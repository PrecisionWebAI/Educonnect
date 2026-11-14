"""Leave reads: both leave screens, the policy table and the balance register.

The student screen and the staff screen used to answer with invented applications;
the table already holds them and `student_id` says which screen a row belongs to.

Both lists read their supporting facts (names, roles, class-section labels) in a
fixed number of statements. The old code looked each of them up per row, which is
why a school with a term's worth of leave took seconds to open a tab.

The balance is **derived**, never stored: `used` is a `SUM` over the approved
requests, `entitled` is the person's override or the school's policy, and
`remaining` is the difference (`labels.balance_left`). Rejecting or cancelling a
leave therefore gives the days back with no update and no reconciliation, which is
the whole reason `leavebalance` holds an override instead of a counter.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.formatting import day, stamp
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User
from app.domains.auth.roles import primary_role_labels
from app.domains.people.staff.models import Employee

from . import labels, repository
from .models import LeaveRequest
from .schemas import (
    LeaveApplicationItem,
    LeaveBalanceRow,
    LeaveBalancesRead,
    LeavePolicyRead,
    LeaveRequestRead,
    StaffLeaveRow,
)


def _student_rows(
    session: Session, requests: list[LeaveRequest]
) -> list[LeaveApplicationItem]:
    student_ids = [request.student_id for request in requests if request.student_id]
    students = (
        {
            student.id: student
            for student in session.exec(
                select(Student).where(Student.id.in_(student_ids))
            ).all()
        }
        if student_ids
        else {}
    )
    user_ids = [student.user_id for student in students.values() if student.user_id]
    users = (
        {
            user.id: user
            for user in session.exec(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )
    class_labels = labels_by_section(
        session,
        [student.classroom_id for student in students.values() if student.classroom_id],
    )

    items: list[LeaveApplicationItem] = []
    for request in requests:
        student = students.get(request.student_id)
        user = users.get(student.user_id) if (student and student.user_id) else None
        items.append(
            LeaveApplicationItem(
                id=request.id,  # type: ignore[arg-type]
                student=user.full_name if user else "",
                class_name=(
                    class_labels.get(student.classroom_id, "")
                    if student and student.classroom_id
                    else ""
                ),
                type=request.leave_type,
                from_date=day(request.from_date),
                to_date=day(request.to_date),
                reason=request.reason or "",
                days=request.days,
                status=request.status,
                submitted_at=stamp(request.created_at),
            )
        )
    return items


def _staff_rows(session: Session, requests: list[LeaveRequest]) -> list[StaffLeaveRow]:
    """The staff table's rows, and the balance behind each of them.

    Four batched reads whatever the school's size: the requesters' names, their
    employee rows (EMP-####, department), their role labels, and the days each of
    them has spent per type in the years this page shows. The old version looked
    every one of those up per row.
    """
    user_ids = list(dict.fromkeys(request.requester_user_id for request in requests))
    users = repository.full_names(session, user_ids)
    employees = repository.employees_by_user(session, user_ids)
    roles = primary_role_labels(session, user_ids)

    # One `(user, type, year)` spend map per year the rows touch - a term's page
    # usually touches one year, and a page spanning New Year touches two.
    years = sorted({labels.leave_year(request.from_date) for request in requests})
    spent: dict[int, dict[tuple[UUID, str], tuple[int, int]]] = {
        year: repository.days_by_employee(session, year=year, user_ids=user_ids)
        for year in years
    }
    entitled = _entitlements(session, employees.values(), years)

    deciders = repository.full_names(
        session,
        [
            request.decided_by_user_id
            for request in requests
            if request.decided_by_user_id
        ],
    )

    items: list[StaffLeaveRow] = []
    for request in requests:
        employee = employees.get(request.requester_user_id)
        row_year = labels.leave_year(request.from_date)
        key = (request.requester_user_id, labels.type_key(request.leave_type))
        used, pending = spent.get(row_year, {}).get(key, (0, 0))
        entitled_days = entitled.get(
            (
                employee.id if employee else None,
                labels.type_key(request.leave_type),
                row_year,
            )
        )
        items.append(
            StaffLeaveRow(
                id=request.id,  # type: ignore[arg-type]
                employee_id=employee.id if employee else None,
                staff_name=users.get(request.requester_user_id, ""),
                staff_code=employee.employee_code if employee else "",
                role=roles.get(request.requester_user_id, "Staff"),
                department=(employee.department or "") if employee else "",
                leave_type=request.leave_type,
                from_date=day(request.from_date),
                to_date=day(request.to_date),
                days=request.days,
                reason=request.reason or "",
                status=request.status,
                balance=labels.balance_left(
                    entitled=entitled_days, used=used, pending=pending
                ),
                applied_at=stamp(request.created_at),
                decided_by=deciders.get(
                    request.decided_by_user_id or request.requester_user_id
                )
                if request.decided_by_user_id
                else None,
                decided_at=stamp(request.decided_at) if request.decided_at else None,
                decision_note=request.decision_note,
            )
        )
    return items


def _entitlements(
    session: Session, employees, years: list[int]
) -> dict[tuple[UUID, str, int], int | None]:
    """``{(employee_id, type_key, year): entitled_days}`` for a set of employees.

    An override wins over the school's policy; a type with neither comes back as
    ``None`` (untracked), which is what keeps "not tracked" and "0 days left" from
    printing as the same thing. Year-aware because the override is: a row filed in
    December is measured against December's year, not the year the page happens to
    be open in.
    """
    people = [employee for employee in employees if employee is not None]
    if not people:
        return {}
    policies = repository.effective_policies(session)
    ids = [employee.id for employee in people]

    result: dict[tuple[UUID, str, int], int | None] = {}
    for year in years:
        overrides = repository.overrides(session, year=year, employee_ids=ids)
        for employee in people:
            for key, (_spelling, annual_days) in policies.items():
                result[(employee.id, key, year)] = annual_days
        # An override for a type the school has since retired still counts: the
        # number somebody granted outranks the policy list that no longer lists it.
        for (employee_id, key), row in overrides.items():
            result[(employee_id, key, year)] = row.entitled_days
    return result


def list_leave_applications(
    session: Session, student_id: UUID | None = None
) -> list[LeaveApplicationItem]:
    """Student leave requests, newest first. `student_id` narrows it to one student."""
    return _student_rows(
        session, repository.student_requests(session, student_id=student_id)
    )


def list_staff_leave(
    session: Session,
    *,
    status: str | None = None,
    year: int | None = None,
    user_ids: list[UUID] | None = None,
) -> list[StaffLeaveRow]:
    """Staff leave requests, newest first (`student_id` is NULL for these).

    `status` and `year` are the screen's filters; `user_ids` is the caller's scope
    (a teacher-only account sees its own rows, exactly like the directory).
    """
    return _staff_rows(
        session,
        repository.staff_requests(session, user_ids=user_ids, status=status, year=year),
    )


# --- scoping ----------------------------------------------------------------


def visible_user_ids(session: Session, user: User | None) -> list[UUID] | None:
    """The **requester** user ids this caller may read, or ``None`` for all.

    The directory's scope decides which employees a caller sees; a leave row keys on
    the requester's user id, so the two are bridged here. ``None`` (the whole school)
    stays ``None`` rather than becoming every id in the database: the repository
    turns it into no `WHERE` at all.
    """
    # Imported inside the function: `people.teachers` imports this domain's models.
    from app.domains.people.teachers import scope as people_scope

    visible = people_scope.visible_employee_ids(session, user)
    if visible is None:
        return None
    if not visible:
        return []
    rows = session.exec(select(Employee.user_id).where(Employee.id.in_(visible))).all()
    return [user_id for user_id in rows if user_id is not None]


# --- policies ---------------------------------------------------------------


def policies_read(session: Session) -> list[LeavePolicyRead]:
    """The school's leave types and what each grants.

    Answers with the **effective** list - stored rows if the school has written any,
    otherwise the defaults - because the apply form needs a list of types whether or
    not anybody has visited the policy screen. `updated_by` / `updated_at` are set
    only for rows that were actually saved, so the screen can tell the two apart.
    """
    stored = repository.policy_for(session)
    names = repository.full_names(
        session,
        [row.updated_by_user_id for row in stored.values() if row.updated_by_user_id],
    )
    ordered = sorted(repository.effective_policies(session).values())
    rows: list[LeavePolicyRead] = []
    for spelling, annual_days in ordered:
        policy = stored.get(labels.type_key(spelling))
        updated_by = policy.updated_by_user_id if policy is not None else None
        rows.append(
            LeavePolicyRead(
                leave_type=spelling,
                annual_days=annual_days,
                updated_by=names.get(updated_by) if updated_by else None,
                updated_at=stamp(policy.updated_at) if policy is not None else None,
            )
        )
    return rows


# --- balances ---------------------------------------------------------------


def balance_register(
    session: Session,
    *,
    year: int,
    employee_id: UUID | None = None,
    user: User | None = None,
) -> LeaveBalancesRead:
    """Every person in scope x every leave type, for one year.

    The people are the **teaching roll** - the same list the directory and the
    register count - narrowed by `scope.visible_employee_ids`, so a teacher-only
    account reads its own balances rather than the school's.

    A fixed number of statements whatever the school's size: the roll, the
    overrides, the days spent, and the names. Nothing is looked up per person per
    type, which is what made the old per-row reads slow.
    """
    # Imported inside the function: `people.teachers` imports this domain's models,
    # and a module-level import would tie the two packages together for good.
    from app.domains.people.teachers import scope
    from app.domains.people.teachers.repository import teaching_employees

    visible = scope.visible_employee_ids(session, user)
    if employee_id is not None:
        target = session.get(Employee, employee_id)
        if target is None or (visible is not None and target.id not in visible):
            raise HTTPException(status_code=404, detail="Teacher not found")
        people = [target]
    else:
        people = [
            employee
            for employee in teaching_employees(session)
            if visible is None or employee.id in visible
        ]

    policies = repository.effective_policies(session)
    types = [spelling for spelling, _days in sorted(policies.values())]
    user_ids = [employee.user_id for employee in people if employee.user_id]
    names = repository.full_names(session, user_ids)
    spent = repository.days_by_employee(session, year=year, user_ids=user_ids)
    overrides = repository.overrides(
        session, year=year, employee_ids=[employee.id for employee in people]
    )

    rows: list[LeaveBalanceRow] = []
    for employee in people:
        for spelling in types:
            key = labels.type_key(spelling)
            override = overrides.get((employee.id, key))
            if override is not None:
                entitled: int | None = override.entitled_days
                source = "override"
            elif key in policies:
                entitled = policies[key][1]
                source = "policy"
            else:  # pragma: no cover - `types` is built from `policies`
                entitled = None
                source = "untracked"
            used, pending = spent.get((employee.user_id, key), (0, 0))
            rows.append(
                LeaveBalanceRow(
                    employee_id=employee.id,
                    employee_code=employee.employee_code,
                    staff_name=names.get(employee.user_id, ""),
                    department=employee.department or "",
                    leave_type=spelling,
                    year=year,
                    entitled=entitled,
                    used=used,
                    pending=pending,
                    remaining=labels.balance_left(
                        entitled=entitled, used=used, pending=pending
                    ),
                    source=source,
                )
            )
    return LeaveBalancesRead(year=year, types=types, rows=rows)


def entitlement_for(
    session: Session, *, employee: Employee, leave_type: str, year: int
) -> int | None:
    """What this person is entitled to for one type and year (`None` = untracked).

    An override wins, then the school's policy. `None` means the school has said
    nothing about this type - and nothing is what the workflow must therefore
    refuse to invent a limit from.
    """
    override = repository.override(
        session, employee_id=employee.id, leave_type=leave_type, year=year
    )
    if override is not None:
        return override.entitled_days
    effective = repository.effective_policies(session)
    key = labels.type_key(leave_type)
    if key in effective:
        return effective[key][1]
    return None


def days_for(
    session: Session, *, employee: Employee, leave_type: str, year: int
) -> tuple[int, int]:
    """``(approved_days, pending_days)`` for one person, type and year."""
    if employee.user_id is None:
        return 0, 0
    spent = repository.days_by_employee(session, year=year, user_ids=[employee.user_id])
    return spent.get((employee.user_id, labels.type_key(leave_type)), (0, 0))


def request_read(session: Session, request: LeaveRequest) -> LeaveRequestRead:
    """One request in the shape every workflow verb answers with."""
    employee = (
        repository.employees_by_user(session, [request.requester_user_id]).get(
            request.requester_user_id
        )
        if request.student_id is None
        else None
    )
    names = repository.full_names(
        session,
        [request.requester_user_id, request.decided_by_user_id],
    )

    person = names.get(request.requester_user_id, "")
    person_code = employee.employee_code if employee is not None else ""
    if request.student_id is not None:
        student = session.get(Student, request.student_id)
        if student is not None and student.user_id:
            person = (
                repository.full_names(session, [student.user_id]).get(student.user_id)
                or person
            )

    remaining: int | None = None
    if employee is not None:
        year = labels.leave_year(request.from_date)
        used, pending = days_for(
            session, employee=employee, leave_type=request.leave_type, year=year
        )
        remaining = labels.balance_left(
            entitled=entitlement_for(
                session, employee=employee, leave_type=request.leave_type, year=year
            ),
            used=used,
            pending=pending,
        )

    return LeaveRequestRead(
        id=request.id,  # type: ignore[arg-type]
        scope="staff" if request.student_id is None else "student",
        person=person,
        person_code=person_code,
        leave_type=request.leave_type,
        from_date=day(request.from_date),
        to_date=day(request.to_date),
        days=request.days,
        reason=request.reason or "",
        status=request.status,
        balance_remaining=remaining,
        decided_by=(
            names.get(request.decided_by_user_id)
            if request.decided_by_user_id
            else None
        ),
        decided_at=stamp(request.decided_at) if request.decided_at else None,
        decision_note=request.decision_note,
        applied_at=stamp(request.created_at),
    )
