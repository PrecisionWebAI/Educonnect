"""The leave workflow: apply, approve, reject, cancel, and the school's policy.

Everything that changes a leave row is here, and every function answers the same
three questions before touching one:

* **may this caller do this, to this person?** - the route guard says whether they
  reach the endpoint at all; `scope.py` says whose request is theirs to decide
  (nobody approves their own), and `people/teachers/scope.py` says whose record
  they may see (out of scope is `404`, never `403` - the API must not confirm that
  a colleague's request exists);
* **is the row still open to that decision?** - each verb has one state it moves
  from; a second identical decision is a **no-op** (`200`, no audit line, no moved
  timestamp), and a contradictory one is a `409` that names the current state, so
  the screen can say "it was cancelled this morning" instead of "failed";
* **does the balance still allow it?** - checked on apply **and** again on approve,
  because the days between filing and deciding belong to somebody else's request
  too. A type with no policy is untracked and never refuses (`labels.over_limit`).

Audit: a staff leave writes to `staffauditlog` (`section="leave"`), so the profile's
activity feed shows the decision beside the qualification and register entries. A
student leave writes none - `staffauditlog.employee_id` is NOT NULL and a student is
not an employee.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User
from app.domains.auth.models import utcnow
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as staff_labels
from app.domains.people.teachers.profile.service import record_audit

from . import labels, repository, scope, service
from .models import LeavePolicy, LeaveRequest
from .schemas import (
    LeaveApplyIn,
    LeaveBalanceRow,
    LeaveBalanceWrite,
    LeavePoliciesWrite,
    LeavePolicyRead,
    LeaveRequestRead,
)

#: The decision each verb moves a request to.
TARGETS = {
    "approve": labels.APPROVED,
    "reject": labels.REJECTED,
    "cancel": labels.CANCELLED,
}


# --- shared checks ----------------------------------------------------------


def _employee_visible(session: Session, employee: Employee | None, user: User | None):
    """Refuse a person this caller may not see (`404`), like the whole domain."""
    if employee is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    from app.domains.people.teachers import scope as people_scope

    visible = people_scope.visible_employee_ids(session, user)
    if visible is not None and employee.id not in visible:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return employee


def _require_open(employee: Employee) -> None:
    """Refuse leave for somebody off the staff roll (`409`)."""
    if staff_labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This person is off the staff roll, so no new leave can be filed. "
                "Reactivate them first."
            ),
        )


def _staff_type(session: Session, leave_type: str) -> str:
    """The school's own spelling for a leave type (`422` when it grants none).

    Resolved against the policy list so "casual", "Casual " and "CASUAL" cannot
    become three balances for one teacher, and so a type the school does not grant
    is refused with the list it does grant rather than silently accepted.
    """
    effective = repository.effective_policies(session)
    key = labels.type_key(leave_type)
    if key not in effective:
        granted = ", ".join(spelling for spelling, _days in sorted(effective.values()))
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown leave type '{leave_type.strip()}'. "
                f"This school grants: {granted}."
            ),
        )
    return effective[key][0]


def _student_type(leave_type: str) -> str:
    """The screen's own word for a student leave type (`422` when unknown)."""
    wanted = labels.type_key(leave_type)
    for name in labels.STUDENT_LEAVE_TYPES:
        if labels.type_key(name) == wanted:
            return name
    raise HTTPException(
        status_code=422,
        detail=(
            f"Unknown leave type '{leave_type.strip()}'. "
            f"Expected one of: {', '.join(labels.STUDENT_LEAVE_TYPES)}"
        ),
    )


# --- apply ------------------------------------------------------------------


def apply_leave(
    session: Session, payload: LeaveApplyIn, user: User | None
) -> LeaveRequestRead:
    """File a leave for a staff member (or, from the student screen, a student)."""
    if payload.student_id is not None:
        return _apply_student(session, payload, user)
    return _apply_staff(session, payload, user)


def _apply_staff(
    session: Session, payload: LeaveApplyIn, user: User | None
) -> LeaveRequestRead:
    """File a staff leave and hold the days against the person's balance.

    **The requester is the staff member**, not whoever filed it: the register
    derives `On Leave` from `leaverequest.requester_user_id`, so an office clerk
    filing on a teacher's behalf must not become the person who is away.
    """
    employee = _staff_target(session, payload, user)
    _require_open(employee)
    if employee.user_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This employee has no login, so no leave can be filed against them. "
                "Attach a user account first."
            ),
        )

    spelling = _staff_type(session, payload.leave_type)
    days = labels.days_between(payload.from_date, payload.to_date)
    year = labels.leave_year(payload.from_date)

    clashing = repository.overlapping(
        session,
        user_id=employee.user_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )
    if clashing:
        first = clashing[0]
        raise HTTPException(
            status_code=409,
            detail=(
                f"{employee.employee_code} already has a {first.status.lower()} "
                f"{first.leave_type} leave from {first.from_date} to {first.to_date}. "
                "Cancel or amend that one instead of filing a second."
            ),
        )

    entitlement = service.entitlement_for(
        session, employee=employee, leave_type=spelling, year=year
    )
    used, pending = service.days_for(
        session, employee=employee, leave_type=spelling, year=year
    )
    if labels.over_limit(entitled=entitlement, used=used, pending=pending, days=days):
        left = labels.balance_left(entitled=entitlement, used=used, pending=pending)
        raise HTTPException(
            status_code=409,
            detail=(
                f"{spelling} leave for {year}: {entitlement} entitled, {used} used, "
                f"{pending} pending - {days} day(s) requested would leave {left}. "
                "Grant an override on the balances screen first."
            ),
        )

    request = LeaveRequest(
        student_id=None,
        employee_id=employee.id,
        requester_user_id=employee.user_id,
        leave_type=spelling,
        from_date=payload.from_date,
        to_date=payload.to_date,
        days=days,
        half_day=bool(getattr(payload, "half_day", False)),
        reason=payload.reason,
        status=labels.PENDING,
    )
    session.add(request)
    session.flush()
    _audit(session, request, employee, action="created", user=user, note=None)
    session.commit()
    session.refresh(request)
    return service.request_read(session, request)


def _staff_target(
    session: Session, payload: LeaveApplyIn, user: User | None
) -> Employee:
    """Whose leave this is, and whether this caller may file it.

    With an `employee_id` the caller is filing for **somebody else**, which is the
    office's job (`leave.approve` roles). Without one, it is the caller's own leave -
    the teacher's form - and their employee record is looked up from their login.
    """
    if payload.employee_id is not None:
        employee = _employee_visible(
            session, session.get(Employee, payload.employee_id), user
        )
        filing_for_someone_else = user is None or employee.user_id != user.id
        if filing_for_someone_else and not scope.may_decide(session, user):
            raise HTTPException(
                status_code=403,
                detail="Only the office may file leave for somebody else.",
            )
        return employee

    own = (
        repository.employees_by_user(session, [user.id]).get(user.id)
        if user is not None
        else None
    )
    if own is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Your login is not attached to a staff record, so there is nobody to "
                "file leave for. Send the employee's id instead."
            ),
        )
    return own


def _apply_student(
    session: Session, payload: LeaveApplyIn, user: User | None
) -> LeaveRequestRead:
    """File a student leave - no balance, and no clash check.

    A child may legitimately be on two overlapping leaves (a medical leave extended
    by an event), and the class teacher reads both; a balance is an employment
    entitlement and a student has no contract. The requester is whoever filed it,
    because that is who the class screen has to answer to.
    """
    student = session.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if user is None:  # pragma: no cover - every route is behind a login
        raise HTTPException(status_code=403, detail="Sign in to file a leave.")

    request = LeaveRequest(
        student_id=student.id,
        employee_id=None,
        requester_user_id=user.id,
        leave_type=_student_type(payload.leave_type),
        from_date=payload.from_date,
        to_date=payload.to_date,
        days=labels.days_between(payload.from_date, payload.to_date),
        half_day=bool(getattr(payload, "half_day", False)),
        reason=payload.reason,
        status=labels.PENDING,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return service.request_read(session, request)


# --- decide / cancel --------------------------------------------------------


def read_request(
    session: Session, request_id: UUID, user: User | None
) -> LeaveRequestRead:
    """One request, if this caller may see whose it is (`404` otherwise).

    A student's request is readable by anyone the route lets through - the class
    screen shows them - while a staff request is confined to the caller's scope,
    the same `404` the directory answers for a colleague out of view.
    """
    request = repository.request_by_id(session, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request.student_id is None:
        employee = repository.employees_by_user(
            session, [request.requester_user_id]
        ).get(request.requester_user_id)
        if employee is not None:
            _employee_visible(session, employee, user)
    return service.request_read(session, request)


def _audit(
    session: Session,
    request: LeaveRequest,
    employee: Employee | None,
    *,
    action: str,
    user: User | None,
    note: str | None = None,
) -> None:
    """One readable line in the person's activity feed (`section="leave"`)."""
    if employee is None:
        return
    summary = (
        f"{request.leave_type} {request.from_date} -> {request.to_date} "
        f"({request.days} day(s)) - {request.status}"
    )
    if note:
        summary = f"{summary}: {note}"
    record_audit(
        session,
        employee_id=employee.id,
        section="leave",
        action=action,
        row_id=request.id,
        summary=summary,
        user=user,
        commit=False,
    )


def decide(
    session: Session,
    request_id: UUID,
    *,
    action: str,
    note: str | None = None,
    user: User | None = None,
) -> LeaveRequestRead:
    """Approve, reject or cancel one request.

    The same verb twice is a **no-op**: the request comes back as it is, with no
    second audit line and no moved timestamp - a double click on Approve must not
    rewrite the record of when the school decided. A *contradictory* verb on a
    closed request is a `409` that names the state it is actually in.
    """
    if action not in TARGETS:  # pragma: no cover - the router passes a literal
        raise ValueError(f"Unknown leave decision {action!r}.")

    request = repository.request_by_id(session, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Leave request not found")

    employee = None
    if request.student_id is None:
        employee = repository.employees_by_user(
            session, [request.requester_user_id]
        ).get(request.requester_user_id)
        if employee is not None:
            _employee_visible(session, employee, user)

    is_requester = user is not None and request.requester_user_id == user.id
    if action in ("approve", "reject") and is_requester:
        raise HTTPException(
            status_code=403,
            detail=(
                "You cannot approve or reject your own leave; "
                "somebody else has to decide it."
            ),
        )
    if action == "cancel" and not is_requester and not scope.may_decide(session, user):
        raise HTTPException(
            status_code=403,
            detail="Only the person who filed it, or the office, may cancel a leave.",
        )

    target = TARGETS[action]
    if request.status == target:
        # Idempotent: the same decision again is the same answer, not an error.
        return service.request_read(session, request)

    if action == "approve" and request.status != labels.PENDING:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This request is already {request.status.lower()}; "
                "only a pending leave can be approved."
            ),
        )
    if action == "reject" and request.status == labels.APPROVED:
        raise HTTPException(
            status_code=409,
            detail=(
                "This leave is already approved - cancel it instead of rejecting it, "
                "so the register and the balance stay explainable."
            ),
        )
    if action == "reject" and request.status == labels.CANCELLED:
        raise HTTPException(
            status_code=409, detail="This leave was cancelled; it cannot be rejected."
        )
    if action == "cancel" and request.status == labels.REJECTED:
        raise HTTPException(
            status_code=409,
            detail="This leave was rejected; there is nothing to cancel.",
        )

    if action == "approve" and employee is not None:
        year = labels.leave_year(request.from_date)
        used, pending = service.days_for(
            session, employee=employee, leave_type=request.leave_type, year=year
        )
        # This request is still counted as pending; it must not block itself.
        others = max(0, pending - request.days)
        entitlement = service.entitlement_for(
            session, employee=employee, leave_type=request.leave_type, year=year
        )
        if labels.over_limit(
            entitled=entitlement, used=used, pending=others, days=request.days
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{request.leave_type} leave for {year} no longer fits: "
                    f"{entitlement} entitled, {used} used, {others} pending. "
                    "Grant an override on the balances screen before approving."
                ),
            )

    request.status = target
    if user is not None:
        request.decided_by_user_id = user.id
    request.decided_at = utcnow()
    request.decision_note = note
    session.add(request)
    _audit(
        session,
        request,
        employee,
        action="updated",
        user=user,
        note=request.decision_note,
    )
    session.commit()
    session.refresh(request)
    return service.request_read(session, request)


# --- the school's policy ----------------------------------------------------


def save_policies(
    session: Session, payload: LeavePoliciesWrite, user: User | None
) -> list[LeavePolicyRead]:
    """Upsert the leave types in one save, and answer with the whole list.

    Upsert, never replace: a type the payload does not mention keeps its row, so a
    screen that adds "Bereavement" cannot delete "Casual" by omission. Removing a
    type is `delete_policy`, which refuses while requests still use it.
    """
    if not scope.may_manage_policy(session, user):
        raise HTTPException(
            status_code=403,
            detail="Your role may not set the school's leave policy.",
        )

    for item in payload.policies:
        spelling = item.leave_type.strip()
        row = repository.policy_row(session, leave_type=spelling)
        if row is None:
            row = LeavePolicy(
                leave_type=spelling,
                annual_days=item.annual_days,
                updated_by_user_id=user.id if user is not None else None,
            )
        else:
            row.leave_type = spelling
            row.annual_days = item.annual_days
            row.updated_by_user_id = user.id if user is not None else None
            row.updated_at = utcnow()
        session.add(row)

    session.commit()
    return service.policies_read(session)


def delete_policy(session: Session, leave_type: str, user: User | None) -> None:
    """Retire one leave type - refused while any request still uses it.

    Deleting a type that requests name would leave those rows describing an
    entitlement the school no longer has; `annual_days = 0` is the way to stop
    granting days without losing that history.
    """
    if not scope.may_manage_policy(session, user):
        raise HTTPException(
            status_code=403,
            detail="Your role may not set the school's leave policy.",
        )

    row = repository.policy_row(session, leave_type=leave_type)
    if row is None:
        raise HTTPException(status_code=404, detail="Leave type not found")

    in_use = session.exec(
        select(LeaveRequest.id).where(
            func.lower(LeaveRequest.leave_type) == labels.type_key(row.leave_type)
        )
    ).first()
    if in_use is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{row.leave_type}' is already used by leave requests. Set its "
                "annual days to 0 to stop granting it instead of deleting it."
            ),
        )

    session.delete(row)
    session.commit()


# --- one person's override --------------------------------------------------


def save_balance(
    session: Session,
    employee_id: UUID,
    payload: LeaveBalanceWrite,
    user: User | None,
) -> LeaveBalanceRow:
    """Grant (or correct) one person's days for one type and year.

    The type must exist in the school's list: an override for a type nobody can
    apply for would be a number the balance screen cannot even show a column for.
    """
    if not scope.may_manage_policy(session, user):
        raise HTTPException(
            status_code=403,
            detail="Your role may not change a staff member's leave balance.",
        )

    from .models import LeaveBalance

    employee = _employee_visible(session, session.get(Employee, employee_id), user)
    spelling = _staff_type(session, payload.leave_type)

    row = repository.override(
        session, employee_id=employee.id, leave_type=spelling, year=payload.year
    )
    if row is None:
        row = LeaveBalance(
            employee_id=employee.id,
            leave_type=spelling,
            year=payload.year,
            entitled_days=payload.entitled_days,
            note=payload.note,
            updated_by_user_id=user.id if user is not None else None,
        )
    else:
        row.entitled_days = payload.entitled_days
        row.note = payload.note
        row.updated_by_user_id = user.id if user is not None else None
        row.updated_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)

    used, pending = service.days_for(
        session, employee=employee, leave_type=spelling, year=payload.year
    )
    names = repository.full_names(
        session, [employee.user_id] if employee.user_id else []
    )
    return LeaveBalanceRow(
        employee_id=employee.id,
        employee_code=employee.employee_code,
        staff_name=names.get(employee.user_id, ""),
        department=employee.department or "",
        leave_type=spelling,
        year=payload.year,
        entitled=row.entitled_days,
        used=used,
        pending=pending,
        remaining=labels.balance_left(
            entitled=row.entitled_days, used=used, pending=pending
        ),
        source="override",
    )
