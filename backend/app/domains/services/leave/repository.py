"""Statements for leave: policies, overrides, and the days a year has spent.

Every read here is batched. The staff leave screen shows a term's worth of requests
and the balance behind each of them, and looking those facts up per row is how a
full tab takes seconds on a real school; here the rows, the days and the names are
each **one** statement.

`student_id IS NULL` is what makes a row a staff leave - the same table answers the
student screen, so every staff query here says which half it means. The tenant
listener in `app/core/db.py` binds all of it to the session's school.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.tenancy import tenant_of
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from . import labels
from .models import LeaveBalance, LeavePolicy, LeaveRequest

# --- policies ---------------------------------------------------------------


def policies(session: Session) -> list[LeavePolicy]:
    """The school's own policy rows, alphabetically by type."""
    return list(
        session.exec(select(LeavePolicy).order_by(LeavePolicy.leave_type)).all()  # type: ignore[arg-type]
    )


def policy_for(session: Session) -> dict[str, LeavePolicy]:
    """``{type_key: policy}`` - keyed the way a caller's spelling is compared."""
    return {labels.type_key(row.leave_type): row for row in policies(session)}


def effective_policies(session: Session) -> dict[str, tuple[str, int]]:
    """``{type_key: (spelling, annual_days)}`` for every type this school grants.

    Stored rows win **wholesale**: a school that has written its own list does not
    silently get the defaults back for the types it left out (that would make a
    retired type impossible to retire). The defaults exist so a school that has
    never opened the policy screen still has a working apply form - the same
    reasoning that gives the workload matrix a timetable fallback.
    """
    stored = policies(session)
    if stored:
        return {
            labels.type_key(row.leave_type): (row.leave_type, row.annual_days)
            for row in stored
        }
    return {
        labels.type_key(name): (name, days)
        for name, days in labels.DEFAULT_POLICIES.items()
    }


def policy_row(session: Session, *, leave_type: str) -> LeavePolicy | None:
    """The stored policy for one type, compared case-insensitively."""
    wanted = labels.type_key(leave_type)
    return session.exec(
        select(LeavePolicy).where(func.lower(LeavePolicy.leave_type) == wanted)
    ).first()


# --- overrides --------------------------------------------------------------


def overrides(
    session: Session, *, year: int, employee_ids: list[UUID]
) -> dict[tuple[UUID, str], LeaveBalance]:
    """``{(employee_id, type_key): override}`` for one year."""
    if not employee_ids:
        return {}
    rows = session.exec(
        select(LeaveBalance).where(
            LeaveBalance.year == year,
            LeaveBalance.employee_id.in_(employee_ids),
        )
    ).all()
    return {(row.employee_id, labels.type_key(row.leave_type)): row for row in rows}


def override(
    session: Session, *, employee_id: UUID, leave_type: str, year: int
) -> LeaveBalance | None:
    """One person's override for one type and year."""
    wanted = labels.type_key(leave_type)
    rows = session.exec(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == year,
        )
    ).all()
    for row in rows:
        if labels.type_key(row.leave_type) == wanted:
            return row
    return None


# --- days spent -------------------------------------------------------------


def days_by_employee(
    session: Session, *, year: int, user_ids: list[UUID]
) -> dict[tuple[UUID, str], tuple[int, int]]:
    """``{(user_id, type_key): (approved_days, pending_days)}`` for one year.

    One `GROUP BY` for the whole school. A leave belongs to the year of its
    **start** date (`labels.leave_year`), so a range crossing New Year is counted
    once rather than half in each year.

    Cancelled and rejected requests are absent by construction - only `Approved`
    and `Pending` are asked for, which is what makes a cancelled leave give its
    days back without a single update.
    """
    if not user_ids:
        return {}
    start, end = labels.year_bounds(year)
    rows = session.exec(
        select(
            LeaveRequest.requester_user_id,
            LeaveRequest.leave_type,
            LeaveRequest.status,
            func.sum(LeaveRequest.days),
        )
        .where(
            LeaveRequest.student_id.is_(None),  # type: ignore[union-attr]
            LeaveRequest.status.in_((labels.APPROVED, labels.PENDING)),
            LeaveRequest.from_date >= start,
            LeaveRequest.from_date <= end,
            LeaveRequest.requester_user_id.in_(user_ids),
        )
        .group_by(
            LeaveRequest.requester_user_id,
            LeaveRequest.leave_type,
            LeaveRequest.status,
        )
    ).all()

    spent: dict[tuple[UUID, str], tuple[int, int]] = {}
    for user_id, leave_type, status, total in rows:
        if user_id is None:
            continue
        key = (user_id, labels.type_key(leave_type or ""))
        used, pending = spent.get(key, (0, 0))
        if status == labels.APPROVED:
            used += int(total or 0)
        else:
            pending += int(total or 0)
        spent[key] = (used, pending)
    return spent


# --- requests ---------------------------------------------------------------


def staff_requests(
    session: Session,
    *,
    user_ids: list[UUID] | None = None,
    status: str | None = None,
    year: int | None = None,
) -> list[LeaveRequest]:
    """Staff leave requests, newest first, optionally narrowed.

    `year` filters on the **start** date - the same key the balance counts by - so
    the table and the balance strip cannot disagree about which year they are in.
    """
    statement = select(LeaveRequest).where(
        LeaveRequest.student_id.is_(None)  # type: ignore[union-attr]
    )
    if user_ids is not None:
        statement = statement.where(LeaveRequest.requester_user_id.in_(user_ids))
    if status is not None:
        statement = statement.where(LeaveRequest.status == status)
    if year is not None:
        start, end = labels.year_bounds(year)
        statement = statement.where(
            LeaveRequest.from_date >= start, LeaveRequest.from_date <= end
        )
    statement = statement.order_by(
        LeaveRequest.created_at.desc()  # type: ignore[attr-defined]
    )
    return list(session.exec(statement).all())


def student_requests(
    session: Session,
    *,
    student_id: UUID | None = None,
    status: str | None = None,
    year: int | None = None,
) -> list[LeaveRequest]:
    """Student leave requests, newest first. `student_id` narrows to one student."""
    statement = select(LeaveRequest).where(
        LeaveRequest.student_id.is_not(None)  # type: ignore[union-attr]
    )
    if student_id is not None:
        statement = statement.where(LeaveRequest.student_id == student_id)
    if status is not None:
        statement = statement.where(LeaveRequest.status == status)
    if year is not None:
        start, end = labels.year_bounds(year)
        statement = statement.where(
            LeaveRequest.from_date >= start, LeaveRequest.from_date <= end
        )
    statement = statement.order_by(
        LeaveRequest.created_at.desc()  # type: ignore[attr-defined]
    )
    return list(session.exec(statement).all())


def request_by_id(session: Session, request_id: UUID) -> LeaveRequest | None:
    """One request by its own id, or None. The caller decides who may see it.

    The school check is **explicit**, not left to the tenant listener:
    `session.get` answers from the identity map or emits a primary-key read that the
    `do_orm_execute` filter does not narrow, so without this line a caller in school A
    could read school B's leave by guessing an id. Phase 7's cross-school test is the
    reason this is here.
    """
    request = session.get(LeaveRequest, request_id)
    if request is None:
        return None
    school = tenant_of(session)
    if school is not None and request.school_id != school:
        return None
    return request


def overlapping(
    session: Session,
    *,
    user_id: UUID,
    from_date: date,
    to_date: date,
    exclude_id: UUID | None = None,
) -> list[LeaveRequest]:
    """This person's live requests that clash with a range.

    `Pending` and `Approved` only: a rejected or cancelled request is history and
    must not stop a fresh application for the same week.
    """
    statement = select(LeaveRequest).where(
        LeaveRequest.student_id.is_(None),  # type: ignore[union-attr]
        LeaveRequest.requester_user_id == user_id,
        LeaveRequest.status.in_((labels.PENDING, labels.APPROVED)),
        LeaveRequest.from_date <= to_date,
        LeaveRequest.to_date >= from_date,
    )
    if exclude_id is not None:
        statement = statement.where(LeaveRequest.id != exclude_id)
    return list(session.exec(statement).all())


# --- names ------------------------------------------------------------------


def employees_by_user(session: Session, user_ids: list[UUID]) -> dict[UUID, Employee]:
    """``{user_id: employee}`` - the row that carries EMP-####, dept and post."""
    wanted = list(dict.fromkeys(user_id for user_id in user_ids if user_id))
    if not wanted:
        return {}
    rows = session.exec(select(Employee).where(Employee.user_id.in_(wanted))).all()
    return {row.user_id: row for row in rows if row.user_id is not None}


def full_names(session: Session, user_ids: list[UUID]) -> dict[UUID, str]:
    """``{user_id: full_name}`` for whoever asked and whoever decided."""
    wanted = list(dict.fromkeys(user_id for user_id in user_ids if user_id))
    if not wanted:
        return {}
    rows = session.exec(
        select(User.id, User.full_name).where(User.id.in_(wanted))
    ).all()
    return {user_id: name for user_id, name in rows if user_id is not None}
