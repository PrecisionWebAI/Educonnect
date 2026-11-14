"""What the register may record, and what it refuses to.

The writes answer Phase 3's three questions in the same order, because the same
mistakes are possible here:

* **may this caller see this person?** - out of scope is `404`, never `403`: the
  API must not confirm that a colleague's id exists;
* **may this caller write the register at all?** - `staff_attendance.mark` (and
  `scope.may_mark_attendance`) decides it; a department head holds the read right
  only, which is also the right the register's own filter respects;
* **is the record still open?** - a leaver's profile is history, so marking a day
  on it is `409`, with the message naming reactivation as the way back in.

Three rules are specific to attendance:

* **`on_leave` is derived and it wins.** A person with an approved leave covering
  the day reads `On Leave` whether or not somebody marked them, because the leave
  is the decision the school stands behind and a register that kept them Present
  would need a second edit nobody remembers to make. Their row is **kept**, not
  deleted: cancel the leave and the recorded day is exactly where the office left
  it. The same rule refuses a mark for somebody on leave that day (`409`), so a
  contradiction cannot be created in the first place.
* **a day nobody marked is `Not Marked`**, never `Absent` (see `labels`).
* **only what changed is audited.** A bulk call re-sending yesterday's statuses is
  a refresh, not forty events; `staffauditlog` is a trail, not a log file.
"""

from calendar import monthrange
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.admin.users.models import User
from app.domains.auth.models import utcnow
from app.domains.people.staff.models import Employee

from .. import labels, scope
from .. import repository as teachers_repository
from ..profile.repository import employee_names, recorder_names
from ..profile.service import record_audit, require_employee
from . import repository
from .models import StaffAttendanceRecord
from .schemas import (
    AttendanceBulkIn,
    AttendanceDayRead,
    AttendanceRecordPatch,
    RegisterRead,
    RegisterRowRead,
    StaffMonthRead,
)


def require_mark(session: Session, user: User | None) -> None:
    """Refuse a write unless this caller fills the register.

    Checked here as well as on the route (`RequirePermission`), for the reason the
    profile's writes are: the route guard is one line somebody can forget to add,
    and this function is what every write already calls.
    """
    if not scope.may_mark_attendance(session, user):
        raise HTTPException(
            status_code=403, detail="Your role may not mark the staff register."
        )


# --- who the register covers ----------------------------------------------


def _roll(
    session: Session,
    user: User | None,
    department: str | None,
    kind: str | None = None,
) -> list[Employee]:
    """The people this register lists: on the roll, in scope, optionally one dept.

    The roll is **everybody** (`all_employees`) - the 0.9 fix: it used to be only
    the teaching roll, so a school's accountant never had a row in its own staff
    register. `kind` narrows it to one side of the Teachers/Staff split when the
    screen asks; the default is the whole school, because the register is the
    school's book.

    A leaver is left out: the register is today's book, and their own month stays
    readable through `month()`.

    `department` is matched case- and space-insensitively, like every other
    department filter in this domain.
    """
    people = [
        employee
        for employee in teachers_repository.all_employees(session)
        if not labels.serves_read_only(
            deactivated_at=employee.deactivated_at, left_on=employee.left_on
        )
    ]

    if kind is not None:
        wanted = {
            employee.id
            for employee in teachers_repository.roll_employees(session, kind)  # type: ignore[arg-type]
        }
        people = [employee for employee in people if employee.id in wanted]

    visible = scope.visible_employee_ids(session, user)
    if visible is not None:
        people = [employee for employee in people if employee.id in visible]

    if department:
        wanted = department.strip().lower()
        people = [
            employee
            for employee in people
            if (employee.department or "").strip().lower() == wanted
        ]
    return people


def _require_visible(
    session: Session, employee_id: UUID, user: User | None
) -> Employee:
    """The employee, if this caller may see them (`404` otherwise)."""
    return require_employee(session, employee_id, user)


def _require_open(session: Session, employee: Employee, on_date: date) -> None:
    """Refuse a write on a leaver (`409`) and on a day their leave covers (`409`)."""
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This person is off the staff roll, so their register is read-only. "
                "Reactivate them first."
            ),
        )

    leave_type = repository.staff_leave_on(session, on_date=on_date).get(
        employee.user_id
    )
    if leave_type:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This person is on approved {leave_type} leave on {on_date}. "
                "The register reads On Leave from the leave itself - "
                "amend or cancel the leave instead of marking the day."
            ),
        )


def _status_of(row: StaffAttendanceRecord | None, leave_type: str | None) -> str:
    """The word the register shows for one person on one day.

    Leave first (the decision), then the recorded row, then `Not Marked`. See the
    module docstring for why the leave wins and the row is kept.
    """
    if leave_type:
        return labels.ATTENDANCE_ON_LEAVE
    if row is not None and labels.is_markable(row.status):
        return row.status
    return labels.NOT_MARKED


# --- the day's register ----------------------------------------------------


def register(
    session: Session,
    *,
    on_date: date,
    user: User | None,
    department: str | None = None,
    status: str | None = None,
) -> RegisterRead:
    """One day, everybody in scope, and the counts above them.

    Two statements for the people (the roll, the names) plus two for the day (the
    rows, the approved leave) - the counts and the table are built from the same
    list, so a filter cannot make the header disagree with the rows.

    The `status` filter is applied **after** counting: it narrows what the office is
    looking at, and "Absent 3" must not drop to "Absent 3 of 1" because it asked.
    """
    if status is not None and status not in labels.ATTENDANCE_VIEW_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown attendance status '{status}'. "
                f"Expected one of: {', '.join(labels.ATTENDANCE_VIEW_STATUSES)}"
            ),
        )

    people = _roll(session, user, department)
    ids = [employee.id for employee in people]
    names = employee_names(session, ids)
    rows = repository.records_on(session, on_date=on_date, employee_ids=ids)
    leave = repository.staff_leave_on(session, on_date=on_date)
    markers = recorder_names(
        session,
        [row.marked_by_user_id for row in rows.values() if row.marked_by_user_id],
    )

    built: list[RegisterRowRead] = []
    for employee in people:
        row = rows.get(employee.id)
        leave_type = leave.get(employee.user_id)
        word = _status_of(row, leave_type)
        built.append(
            RegisterRowRead(
                employee_id=employee.id,
                employee_code=employee.employee_code,
                name=names.get(employee.id) or employee.employee_code,
                department=employee.department or "",
                designation=employee.designation,
                status=word,
                status_label=labels.attendance_status_label(word),
                is_marked=labels.is_markable(word),
                record_id=row.id if row is not None else None,
                remarks=row.remarks if row is not None else None,
                leave_type=leave_type,
                marked_by=(
                    markers.get(row.marked_by_user_id)
                    if row is not None and row.marked_by_user_id is not None
                    else None
                ),
                marked_at=row.updated_at if row is not None else None,
            )
        )

    counts = dict.fromkeys(labels.ATTENDANCE_VIEW_STATUSES, 0)
    for entry in built:
        counts[entry.status] = counts.get(entry.status, 0) + 1
    marked = sum(counts[word] for word in labels.ATTENDANCE_STATUSES)

    shown = built if status is None else [row for row in built if row.status == status]

    return RegisterRead(
        date=on_date,
        weekday=labels.weekday_label(on_date),
        rows=shown,
        total=len(built),
        present=counts[labels.PRESENT],
        absent=counts[labels.ABSENT],
        half_day=counts[labels.HALF_DAY],
        on_leave=counts[labels.ATTENDANCE_ON_LEAVE],
        not_marked=counts[labels.NOT_MARKED],
        marked=marked,
        percent=labels.attendance_percent(
            present=counts[labels.PRESENT],
            half_day=counts[labels.HALF_DAY],
            marked=marked,
        ),
    )


# --- writes ----------------------------------------------------------------


def _audit_summary(on_date: date, before: str, after: str) -> str:
    """One readable line: `2026-11-12: Present -> Absent`."""
    return (
        f"{on_date}: {labels.attendance_status_label(before)} -> "
        f"{labels.attendance_status_label(after)}"
    )


def mark_bulk(
    session: Session, payload: AttendanceBulkIn, user: User | None
) -> RegisterRead:
    """Mark a whole day, then answer with the day as it now reads.

    Everything is checked **before** the first row is written: a payload that
    names somebody on approved leave is refused whole, so the office is never left
    with half a register and a `409` it has to reconcile by hand.

    Only rows that actually changed are audited - re-sending the same register (a
    double click, a refresh) is not forty events, and a trail nobody can read is a
    trail nobody checks. The whole call is one commit.
    """
    require_mark(session, user)

    on_roll = {employee.id: employee for employee in _roll(session, user, None)}
    everyone = {
        employee.id: employee
        for employee in teachers_repository.teaching_employees(session)
    }
    leaves = repository.staff_leave_on(session, on_date=payload.date)

    for record in payload.records:
        employee = everyone.get(record.employee_id)
        if employee is None:
            raise HTTPException(
                status_code=404,
                detail="One of the employees is not on this school's staff roll.",
            )
        if record.employee_id not in on_roll:
            # A leaver is `409` (the message names reactivation); anybody else
            # missing is out of this caller's scope, which is the same `404` the
            # rest of the domain answers.
            _require_open(session, employee, payload.date)
            raise HTTPException(status_code=404, detail="Teacher not found")

        leave_type = leaves.get(employee.user_id)
        if leave_type:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{employee.employee_code} is on approved {leave_type} leave on "
                    f"{payload.date}. The register reads On Leave from the leave "
                    "itself - amend or cancel the leave instead of marking the day."
                ),
            )

    for record in payload.records:
        employee = on_roll[record.employee_id]
        row, created, previous_status, previous_remarks = repository.upsert(
            session,
            employee_id=employee.id,
            day=payload.date,
            status=record.status,
            remarks=record.remarks,
            user_id=user.id if user is not None else None,
        )
        if created:
            record_audit(
                session,
                employee_id=employee.id,
                section="attendance",
                action="created",
                row_id=row.id,
                summary=_audit_summary(payload.date, labels.NOT_MARKED, record.status),
                user=user,
                commit=False,
            )
        elif previous_status != record.status:
            record_audit(
                session,
                employee_id=employee.id,
                section="attendance",
                action="updated",
                row_id=row.id,
                summary=_audit_summary(
                    payload.date, previous_status or "", record.status
                ),
                user=user,
                commit=False,
            )
        elif labels.differs(previous_remarks, record.remarks):
            record_audit(
                session,
                employee_id=employee.id,
                section="attendance",
                action="updated",
                row_id=row.id,
                summary=(
                    f"{payload.date}: remarks "
                    f"{previous_remarks or '—'} -> {record.remarks or '—'}"
                ),
                user=user,
                commit=False,
            )

    session.commit()
    return register(session, on_date=payload.date, user=user)


def _day_read(row: StaffAttendanceRecord, marker: str | None) -> AttendanceDayRead:
    """One row in the shape the month grid and the amend reply use."""
    return AttendanceDayRead(
        date=row.date,
        day=row.date.day,
        weekday=labels.weekday_label(row.date),
        status=row.status,
        status_label=labels.attendance_status_label(row.status),
        remarks=row.remarks,
        record_id=row.id,
        marked_by=marker,
        marked_at=row.updated_at,
    )


def amend(
    session: Session, record_id: UUID, payload: AttendanceRecordPatch, user: User | None
) -> AttendanceDayRead:
    """Correct one marked day, and say in the trail what it used to be.

    A no-op change (the same status re-sent, or the same remarks) writes **nothing**
    - not a row, not an audit line - so a form that sends its whole state on every
    save does not turn the activity feed into a list of identical entries.
    """
    require_mark(session, user)

    row = repository.record(session, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    employee = _require_visible(session, row.employee_id, user)
    _require_open(session, employee, row.date)

    status = payload.status or row.status
    remarks = payload.remarks if payload.remarks is not None else row.remarks
    status_changed = status != row.status
    remarks_changed = labels.differs(row.remarks, remarks)

    if not status_changed and not remarks_changed:
        marker = recorder_names(
            session, [row.marked_by_user_id] if row.marked_by_user_id else []
        ).get(row.marked_by_user_id)
        return _day_read(row, marker)

    before = row.status
    row.status = status
    row.remarks = remarks
    row.updated_at = utcnow()
    if user is not None:
        row.marked_by_user_id = user.id
    session.add(row)
    record_audit(
        session,
        employee_id=employee.id,
        section="attendance",
        action="updated",
        row_id=row.id,
        summary=(
            _audit_summary(row.date, before, status)
            if status_changed
            else f"{row.date}: remarks {remarks or '—'}"
        ),
        user=user,
        commit=False,
    )
    session.commit()
    session.refresh(row)

    marker = recorder_names(
        session, [row.marked_by_user_id] if row.marked_by_user_id else []
    ).get(row.marked_by_user_id)
    return _day_read(row, marker)


# --- one person's month ----------------------------------------------------


def month_window(month: str) -> tuple[date, date]:
    """``2026-11`` -> ``(2026-11-01, 2026-11-30)``.

    `422` on anything else, naming the shape it wanted: the screen builds this key
    from a month picker, so a bad one is a bug rather than a user's typo, and
    guessing at it (say, reading "11" as November of this year) would answer a
    question nobody asked.
    """
    parts = (month or "").split("-")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise HTTPException(
            status_code=422, detail="The month must be written YYYY-MM (e.g. 2026-11)."
        )
    year, number = int(parts[0]), int(parts[1])
    if number < 1 or number > 12:
        raise HTTPException(
            status_code=422, detail="The month must be between 01 and 12."
        )
    return date(year, number, 1), date(year, number, monthrange(year, number)[1])


def month(
    session: Session, employee_id: UUID, month: str, user: User | None
) -> StaffMonthRead:
    """One person's month: every day of it, the counts, and the percentage.

    Every calendar day is present, including the ones nobody marked and the ones
    inside an approved leave - a grid with holes in it makes the reader count, and
    the counts are the point of the screen.

    A leaver's month stays readable: their record is history the office may still
    have to explain to payroll, which is the one place `require_employee` is used
    without `_require_open`.
    """
    start, end = month_window(month)
    employee = _require_visible(session, employee_id, user)

    rows = {
        row.date: row
        for row in repository.records_between(
            session, employee_id=employee.id, start=start, end=end
        )
    }
    leaves = teachers_repository.approved_leave_between(
        session, start, end, requester_user_id=employee.user_id
    ).get(employee.user_id, [])
    markers = recorder_names(
        session,
        [row.marked_by_user_id for row in rows.values() if row.marked_by_user_id],
    )

    days: list[AttendanceDayRead] = []
    counts = dict.fromkeys(labels.ATTENDANCE_VIEW_STATUSES, 0)
    cursor = start
    while cursor <= end:
        row = rows.get(cursor)
        leave_type = next(
            (
                leave
                for leave_from, leave_to, leave in leaves
                if leave_from <= cursor <= leave_to
            ),
            None,
        )
        word = _status_of(row, leave_type)
        counts[word] = counts.get(word, 0) + 1
        days.append(
            AttendanceDayRead(
                date=cursor,
                day=cursor.day,
                weekday=labels.weekday_label(cursor),
                status=word,
                status_label=labels.attendance_status_label(word),
                remarks=row.remarks if row is not None else None,
                leave_type=leave_type,
                record_id=row.id if row is not None else None,
                marked_by=(
                    markers.get(row.marked_by_user_id)
                    if row is not None and row.marked_by_user_id is not None
                    else None
                ),
                marked_at=row.updated_at if row is not None else None,
            )
        )
        cursor += timedelta(days=1)

    marked = sum(counts[word] for word in labels.ATTENDANCE_STATUSES)
    names = employee_names(session, [employee.id])

    return StaffMonthRead(
        employee_id=employee.id,
        employee_code=employee.employee_code,
        name=names.get(employee.id) or employee.employee_code,
        department=employee.department or "",
        month=month,
        month_label=labels.month_label(month),
        days=days,
        present=counts[labels.PRESENT],
        absent=counts[labels.ABSENT],
        half_day=counts[labels.HALF_DAY],
        on_leave=counts[labels.ATTENDANCE_ON_LEAVE],
        not_marked=counts[labels.NOT_MARKED],
        marked=marked,
        percent=labels.attendance_percent(
            present=counts[labels.PRESENT],
            half_day=counts[labels.HALF_DAY],
            marked=marked,
        ),
    )
