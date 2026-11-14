"""Reads and upserts for the register.

Every statement is narrowed by `employee_id` **and** the tenant listener binds it
to the session's school, so a record id from another school finds nothing (`404`)
rather than being amended.

The day's rows are read in **one** statement for the whole roll, and the leave that
blankets them in one more (`teachers.repository.approved_leave_between`): a register
is forty people at once, and a query per person is how a screen that felt instant in
a demo takes three seconds in a real school.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.domains.auth.models import utcnow
from app.domains.services.leave.models import LeaveRequest

from .models import StaffAttendanceRecord

# --- reads -----------------------------------------------------------------


def records_on(
    session: Session, *, on_date: date, employee_ids: list[UUID]
) -> dict[UUID, StaffAttendanceRecord]:
    """``{employee_id: row}`` for one day - at most one row per person."""
    if not employee_ids:
        return {}
    rows = session.exec(
        select(StaffAttendanceRecord).where(
            StaffAttendanceRecord.date == on_date,
            StaffAttendanceRecord.employee_id.in_(employee_ids),
        )
    ).all()
    return {row.employee_id: row for row in rows}


def records_between(
    session: Session, *, employee_id: UUID, start: date, end: date
) -> list[StaffAttendanceRecord]:
    """One person's rows in a window, oldest first (the grid's reading order)."""
    return list(
        session.exec(
            select(StaffAttendanceRecord)
            .where(
                StaffAttendanceRecord.employee_id == employee_id,
                StaffAttendanceRecord.date >= start,
                StaffAttendanceRecord.date <= end,
            )
            .order_by(StaffAttendanceRecord.date)  # type: ignore[arg-type]
        ).all()
    )


def record(session: Session, record_id: UUID) -> StaffAttendanceRecord | None:
    """One row by its own id, or None. The caller checks whose it is."""
    return session.get(StaffAttendanceRecord, record_id)


def on_date(
    session: Session, *, employee_id: UUID, on_date: date
) -> StaffAttendanceRecord | None:
    """The row for this person on this day, if there is one."""
    return session.exec(
        select(StaffAttendanceRecord).where(
            StaffAttendanceRecord.employee_id == employee_id,
            StaffAttendanceRecord.date == on_date,
        )
    ).first()


def staff_leave_on(session: Session, *, on_date: date) -> dict[UUID, str]:
    """``{requester_user_id: leave_type}`` for approved staff leave on one day.

    Keyed by **user** id because that is what `leaverequest` holds; the register
    maps it through `employee.user_id`. A person with two overlapping leaves is
    listed once, by the first one found - the register prints one word and does not
    need to choose between a medical leave and its extension.
    """
    rows = session.exec(
        select(LeaveRequest.requester_user_id, LeaveRequest.leave_type).where(
            LeaveRequest.student_id.is_(None),  # type: ignore[union-attr]
            LeaveRequest.status == "Approved",
            LeaveRequest.from_date <= on_date,
            LeaveRequest.to_date >= on_date,
        )
    ).all()
    leaves: dict[UUID, str] = {}
    for user_id, leave_type in rows:
        if user_id is not None:
            leaves.setdefault(user_id, leave_type or "Leave")
    return leaves


# --- writes ----------------------------------------------------------------


def upsert(
    session: Session,
    *,
    employee_id: UUID,
    day: date,
    status: str,
    remarks: str | None,
    user_id: UUID | None,
) -> tuple[StaffAttendanceRecord, bool, str | None, str | None]:
    """Mark one person's day. ``(row, created, previous_status, previous_remarks)``.

    The previous values are returned rather than re-read so the caller can word its
    audit line ("Present -> Absent") without a second lookup, and `created` lets it
    say whether this was the first mark of the day or a correction.

    Updates the row it finds instead of inserting a second one: `UNIQUE(school,
    employee, date)` is the backstop, but a caught `IntegrityError` would have
    already poisoned the transaction.

    The parameter is `day`, not `on_date`, because `on_date` is this module's
    lookup function - a parameter of that name would shadow it inside the body.
    """
    row = on_date(session, employee_id=employee_id, on_date=day)
    created = row is None
    previous_status = None if row is None else row.status
    previous_remarks = None if row is None else row.remarks
    if row is None:
        row = StaffAttendanceRecord(
            employee_id=employee_id,
            date=day,
            status=status,
            remarks=remarks,
            marked_by_user_id=user_id,
        )
    else:
        row.status = status
        row.remarks = remarks
        row.marked_by_user_id = user_id
        row.updated_at = utcnow()
    session.add(row)
    return row, created, previous_status, previous_remarks
