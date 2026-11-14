"""Reads behind the Teachers & Staff screen.

The list is filtered **in SQL** (search, department, status, visibility) rather
than in Python: the screen now asks the server for what it shows, so the filter
that decides a page has to be the same filter the caller asked for - otherwise
"page 2 of Search = Rao" quietly holds rows that do not match.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.services.leave import labels as leave_labels
from app.domains.services.leave.models import LeaveRequest

from . import labels
from .schemas import TeacherCreate

#: Roles that teach. `class_teacher` / `subject_teacher` are gone - they are
#: assignments (`classroom.class_teacher_id`, `subjectteacher`), not roles. The
#: list itself lives in `labels`, so the directory and the Hired tab cannot drift.
TEACHING_ROLES = labels.TEACHING_ROLES

#: The two sides of the Teachers/Staff split (0.9). A `Literal` so a typo is a
#: `422` at the edge instead of "the staff list is empty" in production.
RollKind = Literal["teacher", "staff"]

#: The two sides of the Teachers/Staff split (0.9). A `Literal` so a typo is a
#: `422` at the edge instead of "the staff list is empty" in production.
RollKind = Literal["teacher", "staff"]


def _next_employee_code(session: Session) -> str:
    """Next EMP-#### across the employee table (mirrors the staff service)."""
    codes = session.exec(select(Employee.employee_code)).all()
    numbers = [
        int(code.rsplit("-", 1)[-1])
        for code in codes
        if code and code.rsplit("-", 1)[-1].isdigit()
    ]
    return f"EMP-{max(numbers, default=36) + 1:04d}"


def get_teacher_by_id(session: Session, teacher_id: UUID) -> Employee | None:
    return session.get(Employee, teacher_id)


def get_teacher_by_user_id(session: Session, user_id: UUID) -> Employee | None:
    statement = select(Employee).where(Employee.user_id == user_id)
    return session.exec(statement).first()


def _roll_subquery():
    """The user ids that hold a teaching role - the split's one source of truth.

    A subquery, **not** a join: an employee may hold two teaching roles (a teacher
    who is also an HOD), which a join turns into two rows and pushes the caller to
    `DISTINCT`. On PostgreSQL `SELECT DISTINCT … ORDER BY "app_user".full_name` is
    then rejected outright ("for SELECT DISTINCT, ORDER BY expressions must appear
    in select list") - the list answered 500 while the SQLite tests stayed green.
    """
    return (
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(TEACHING_ROLES))
    )


def _apply_roll(statement, kind: RollKind):
    """Narrow a statement to one side of the Teachers/Staff split (0.9).

    * `teacher` - the employee holds **any** teaching role;
    * `staff` - they hold **none** (school_admin, accountant, librarian, driver…).

    Every employee lands on exactly one side, because the test is the same role
    list read two ways. That is what keeps one person out of both lists without a
    second column that could disagree with the roles.
    """
    teaching = _roll_subquery()
    if kind == "staff":
        return statement.where(Employee.user_id.not_in(teaching))
    return statement.where(Employee.user_id.in_(teaching))


def roll_employees(session: Session, kind: RollKind = "teacher") -> list[Employee]:
    """Every employee on one side of the split right now, by name.

    One query. The summary tiles and the directory read the same list, so a tile
    cannot disagree with the table under it.
    """
    statement = _apply_roll(
        select(Employee).join(User, User.id == Employee.user_id), kind
    )
    return list(session.exec(statement.order_by(User.full_name)).all())


def teaching_employees(session: Session) -> list[Employee]:
    """The teaching half of `roll_employees` - kept for the callers that mean it."""
    return roll_employees(session, "teacher")


def _leave_window(start: date, end: date) -> tuple:
    """The conditions that make one `leaverequest` row a staff absence in a window.

    `student_id IS NULL` is what makes a row a staff leave - the same table also
    answers the student screen. A leave **overlaps** the window when it starts on
    or before the window's last day and ends on or after its first.

    One builder, three readers (the directory's `On Leave` badge, the summary tile,
    the daily register and the month grid): a second copy is how the badge and the
    register start disagreeing about the same Tuesday.
    """
    return (
        LeaveRequest.student_id.is_(None),  # type: ignore[union-attr]
        LeaveRequest.status == leave_labels.APPROVED,
        LeaveRequest.from_date <= end,
        LeaveRequest.to_date >= start,
    )


def _leave_today_subquery():
    """The staff on approved leave today, as a subquery of **user** ids."""
    today = date.today()
    return select(LeaveRequest.requester_user_id).where(*_leave_window(today, today))


def approved_leave_between(
    session: Session,
    start: date,
    end: date,
    *,
    requester_user_id: UUID | None = None,
) -> dict[UUID, list[tuple[date, date, str]]]:
    """``{user_id: [(from_date, to_date, leave_type)]}`` for staff leave in a window.

    A person may hold more than one approved leave covering the same period (a
    medical leave extended by a second application), so the answer is a list and
    the reader decides what to print. The dates are the leave's own, not the
    window's: the month grid needs to know that Tuesday is day four of a leave,
    not that it was asked about.

    ``requester_user_id`` narrows the read to **one person**. The register (a whole
    day, everybody on the roll) wants the school; one person's month sheet wants
    one person, and asking the database for the school and then throwing all but
    one person's rows away is how a single click became a scan of every leave the
    school ever approved - especially against a database reached over the network.
    """
    statement = select(
        LeaveRequest.requester_user_id,
        LeaveRequest.from_date,
        LeaveRequest.to_date,
        LeaveRequest.leave_type,
    ).where(*_leave_window(start, end))
    if requester_user_id is not None:
        statement = statement.where(LeaveRequest.requester_user_id == requester_user_id)

    rows = session.exec(statement).all()
    leaves: dict[UUID, list[tuple[date, date, str]]] = {}
    for user_id, from_date, to_date, leave_type in rows:
        if user_id is None:
            continue
        leaves.setdefault(user_id, []).append(
            (from_date, to_date, leave_type or "Leave")
        )
    return leaves


def approved_leave_today(session: Session, today: date) -> set[UUID]:
    """{user_id of every staff member on approved leave covering `today`}."""
    return set(approved_leave_between(session, today, today))


def period_counts(session: Session, teacher_ids: list[UUID]) -> dict[UUID, int]:
    """{employee_id: timetable periods a week} for the teachers asked about."""
    if not teacher_ids:
        return {}
    rows = session.exec(
        select(TimetablePeriod.teacher_id, func.count())
        .where(TimetablePeriod.teacher_id.in_(teacher_ids))
        .group_by(TimetablePeriod.teacher_id)  # type: ignore[arg-type]
    ).all()
    return {teacher_id: int(count) for teacher_id, count in rows}


def week_capacity(session: Session) -> int:
    """The teaching slots one week runs, counted from the timetable itself.

    A slot is a `(day, start time)` pair. Counting them gives the workload matrix
    a real denominator; the old code divided by a hard-coded 22, so every
    percentage on that tab described a timetable nobody had verified.
    """
    slots = session.exec(
        select(TimetablePeriod.day_of_week, TimetablePeriod.start_time).distinct()
    ).all()
    return len(slots)


def teachers_statement(
    *,
    kind: RollKind = "teacher",
    visible_ids: set[UUID] | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
):
    """The directory's statement, up to (not including) paging.

    Split out so `tests/test_people_contracts.py` can compile it: SQLite accepts
    SQL that PostgreSQL refuses, and that difference already cost a live 500.
    """
    statement = select(Employee).join(User, User.id == Employee.user_id)
    off_the_roll = (
        Employee.deactivated_at.is_(None),  # type: ignore[union-attr]
        Employee.left_on.is_(None),  # type: ignore[union-attr]
    )
    if status == labels.INACTIVE:
        statement = statement.where(
            or_(
                Employee.deactivated_at.is_not(None),  # type: ignore[union-attr]
                Employee.left_on.is_not(None),  # type: ignore[union-attr]
            )
        )
    else:
        # No status filter means "the whole teaching roll", leavers who still hold
        # the role included. Hiding them here is what would make the table
        # disagree with the tiles above it (`active + on leave + inactive`).
        statement = _apply_roll(statement, kind)
        if status == labels.ON_LEAVE:
            statement = statement.where(
                *off_the_roll, Employee.user_id.in_(_leave_today_subquery())
            )
        elif status == labels.ACTIVE:
            statement = statement.where(
                *off_the_roll, Employee.user_id.not_in(_leave_today_subquery())
            )

    if visible_ids is not None:
        statement = statement.where(Employee.id.in_(visible_ids))
    if department:
        statement = statement.where(
            func.lower(Employee.department) == department.strip().lower()
        )
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(User.full_name).like(like),
                func.lower(Employee.employee_code).like(like),
                func.lower(Employee.department).like(like),
                func.lower(Employee.email).like(like),
                func.lower(Employee.phone).like(like),
            )
        )
    return statement.order_by(User.full_name)


def get_teachers(
    session: Session,
    *,
    kind: RollKind = "teacher",
    visible_ids: set[UUID] | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[Employee]:
    """The directory, narrowed by the caller's scope and the screen's filters.

    `kind` picks the side of the Teachers/Staff split (0.9); everything else is the
    same filter the screen sent, so page 2 of a search holds only matching rows.

    `status="Inactive"` deliberately drops the teaching-role test: deactivating
    somebody withdraws their roles, so a leaver looked up *by role* would never
    be found again - and a leaver is exactly who an administrator goes looking
    for.
    """
    if visible_ids is not None and not visible_ids:
        # A caller confined to ids that resolved to nothing sees nothing. The
        # alternative (`IN ()`) is a SQL error dressed as an empty page.
        return []

    statement = teachers_statement(
        kind=kind, visible_ids=visible_ids, q=q, department=department, status=status
    ).offset(skip)
    # `limit=None` is "everything": the screen pages in the browser, and the
    # numbers above the table must describe the school, not the first page.
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def count_teachers(
    session: Session,
    *,
    kind: RollKind = "teacher",
    visible_ids: set[UUID] | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
) -> int:
    """How many rows the same filters match - the number behind `X-Total-Count`.

    Counted by the database, not by `len(page)`: a paged list must be able to say
    "3 of 41" without loading the other 38, and the tiles above the table are
    counted the same way.
    """
    if visible_ids is not None and not visible_ids:
        return 0
    statement = teachers_statement(
        kind=kind, visible_ids=visible_ids, q=q, department=department, status=status
    )
    # `teachers_statement` orders by name for the page; an aggregate must not
    # carry an ORDER BY over a joined column.
    count_statement = select(func.count()).select_from(
        statement.order_by(None).subquery()
    )
    return int(session.exec(count_statement).one())


def all_employees(session: Session) -> list[Employee]:
    """Every employee in the school, teaching or not - the register's roll.

    Phase 3 (0.9) fix: the register used to be built from `teaching_employees`,
    which meant an accountant, a driver or the principal's office had no row in
    the "staff" register at all. The register is everybody's book now; `kind`
    narrows it when the caller asks for one side of the split.
    """
    statement = select(Employee).join(User, User.id == Employee.user_id)
    return list(session.exec(statement.order_by(User.full_name)).all())


def create_teacher(session: Session, teacher_in: TeacherCreate) -> Employee:
    db_teacher = Employee(
        user_id=teacher_in.user_id,
        employee_code=_next_employee_code(session),
        department=teacher_in.department,
        qualification=teacher_in.qualification,
        joining_date=teacher_in.joining_date,
    )
    session.add(db_teacher)
    session.commit()
    session.refresh(db_teacher)

    # The role lives in `user_role`, not on the employee row. `grant_role` adds
    # it without disturbing any role the person already holds.
    user = session.get(User, teacher_in.user_id)
    if user is not None:
        grant_role(session, user, "teacher")
    return db_teacher
