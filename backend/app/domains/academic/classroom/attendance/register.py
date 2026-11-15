"""The register: saving it, reading it back, and the numbers it produces.

One writer, one key
-------------------
A mark is identified by **(school, student, date, subject)** - the unique key on
`attendancerecord`. `save_register` reads that row and updates it, so saving the same
register twice changes it instead of doubling it; the database keys are the second
line of defence for two people pressing Save at the same moment, and the loser gets a
`409` telling them to reload rather than a silent second row.

A closed day cannot be saved
----------------------------
Sunday and the school's own `holiday` rows are the days no register exists. Saving one
is a `409` that **names** the day ("Diwali"), because "the school is closed" without
saying why reads like a bug.

Leave is derived, never stored twice
------------------------------------
The row keeps what the teacher marked and **links** the approved request
(`leave_request_id`). Every read replaces the status with `leave` while that request is
approved, so a cancelled leave reverts to the real mark with no repair job - and the
leave itself is never copied into a second place that could disagree.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import Classroom
from app.domains.admin.settings import values as setting_values
from app.domains.admin.users.models import User

from . import notify, repository
from .models import AttendanceAuditLog, AttendanceRecord, AttendanceStatus
from .schemas import (
    AttendanceBulkCreate,
    AttentionRowRead,
    ClosedDayRead,
    RegisterCountsRead,
    RegisterRead,
    RegisterRowRead,
    SectionSummaryRead,
    SectionTrendRead,
    StudentAttendanceSummaryRead,
    TrendPointRead,
)

#: Sunday - the one weekday a school in this system never marks.
CLOSED_WEEKDAY = 6

#: How far back the attention list and its summary look.
ATTENTION_DAYS = 30

#: Statuses that count as attendance, and the credit each one earns.
CREDIT: dict[str, float] = {
    AttendanceStatus.present.value: 1.0,
    AttendanceStatus.late.value: 1.0,
    AttendanceStatus.half_day.value: 0.5,
    AttendanceStatus.absent.value: 0.0,
}


def _room_or_404(session: Session, section_id: UUID) -> Classroom:
    """This school's class-section, or a `404`.

    `session.get` bypasses the tenant filter, so another school's id would otherwise
    come back as that school's room; the school is compared explicitly (the rule
    Phase 1 applied to students).
    """
    room = session.get(Classroom, section_id)
    school = tenant_of(session)
    if room is None or (school is not None and room.school_id != school):
        raise HTTPException(status_code=404, detail="Class-section not found")
    return room


def closed_reason(session: Session, on_date: date) -> str | None:
    """Why the school is closed that day (`"Sunday"`, `"Diwali"`), else `None`."""
    if on_date.weekday() == CLOSED_WEEKDAY:
        return "Sunday"
    holiday = repository.holiday_on(session, on_date)
    return holiday.name if holiday is not None else None


def closed_days(session: Session, start: date, end: date) -> list[ClosedDayRead]:
    """Every day in the range the register cannot be taken - the calendar's greyed days.

    Sundays are computed, holidays are read; both carry the words the screen prints, so
    the date picker and the toolbar explain the same thing with the same string.
    """
    #: A year is the widest calendar the screen ever asks for; more is a mistake, not a
    #: feature, and would be a long loop returning rows nobody draws.
    if (end - start).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Ask for a range of a year or less.",
        )

    holidays = {
        holiday.on_date: holiday.name
        for holiday in repository.holiday_rows_between(session, start, end)
    }
    days: list[ClosedDayRead] = []
    current = start
    while current <= end:
        if current.weekday() == CLOSED_WEEKDAY:
            days.append(ClosedDayRead(date=current, reason="Sunday"))
        elif current in holidays:
            days.append(ClosedDayRead(date=current, reason=holidays[current]))
        current += timedelta(days=1)
    return days


def _commit(session: Session) -> None:
    """Commit, turning a lost race into a `409` instead of a 500."""
    try:
        session.commit()
    except IntegrityError as error:  # pragma: no cover - the keys make this a race only
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Someone else saved this register at the same moment. "
                "Reload the day and save again."
            ),
        ) from error


def save_register(
    session: Session, payload: AttendanceBulkCreate, user: User | None = None
) -> list[AttendanceRecord]:
    """Upsert a whole class-section's register for one day (and subject).

    Returns the rows as they now stand. Every status/remarks change writes an audit
    row naming the user who made it, so "who marked this child absent" is answerable.
    """
    room = _room_or_404(session, payload.section_id)

    reason = closed_reason(session, payload.date)
    if reason is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{payload.date.isoformat()} is closed - {reason}. "
                "A register cannot be saved on a closed day."
            ),
        )

    roll = {
        student.id: student for student in repository.active_students(session, room.id)
    }
    leaves = repository.approved_leave_on(session, list(roll), payload.date)
    school = tenant_of(session)
    saved: list[AttendanceRecord] = []

    for row in payload.records:
        if row.student_id not in roll:
            raise HTTPException(
                status_code=409,
                detail=(
                    "That student is not on this class-section's roll. "
                    "Reload the register before saving."
                ),
            )

        leave = leaves.get(row.student_id)
        existing = repository.find_record(
            session, row.student_id, payload.date, payload.subject_id
        )

        if existing is None:
            record = AttendanceRecord(
                student_id=row.student_id,
                classroom_id=room.id,
                subject_id=payload.subject_id,
                date=payload.date,
                status=row.status,
                remarks=row.remarks,
                leave_request_id=leave.id if leave is not None else None,
                school_id=school,
            )
            session.add(record)
            saved.append(record)
            continue

        changed = existing.status != row.status or (
            (existing.remarks or None) != (row.remarks or None)
        )
        if changed:
            if user is not None:
                session.add(
                    AttendanceAuditLog(
                        attendance_record_id=existing.id,
                        changed_by_id=user.id,
                        previous_status=existing.status,
                        new_status=row.status,
                        previous_remarks=existing.remarks,
                        new_remarks=row.remarks,
                        school_id=school,
                    )
                )
            existing.overridden_by_id = user.id if user is not None else None

        existing.status = row.status
        existing.remarks = row.remarks
        # A child who moved rooms mid-session: the day follows the current room, the
        # row keeps its own date as history.
        existing.classroom_id = room.id
        existing.leave_request_id = leave.id if leave is not None else None
        session.add(existing)
        saved.append(existing)

    _commit(session)
    for record in saved:
        session.refresh(record)

    # The register is saved and committed; from here on a notification can only add.
    _announce_absences(session, room.id, payload.date, saved)
    return saved


def _announce_absences(
    session: Session, classroom_id: UUID, on_date: date, saved: list[AttendanceRecord]
) -> None:
    """Hand the day's absences (and any run behind them) to the notification module.

    Called **after** the commit on purpose: the register is the school's record, the
    message is a courtesy, and the courtesy must never be able to undo the record.
    """
    absent = [
        record.student_id
        for record in saved
        if str(record.status) == AttendanceStatus.absent.value
    ]
    if not absent:
        return
    streaks = _consecutive_absences(session, classroom_id, on_date)
    run_limit = setting_values.get_int(session, "attendance.consecutive_days", 3)
    notify.announce(
        session,
        classroom_id=classroom_id,
        on_date=on_date,
        absent_student_ids=absent,
        streaks=streaks,
        run_limit=run_limit,
    )


def _percent(credit: float, marked: int) -> float | None:
    """Attendance percentage, or `None` when nothing was marked.

    `None` is the honest answer for "no register yet": a `0%` would read as "the child
    was absent every day", which is the opposite of having no data.
    """
    if marked <= 0:
        return None
    return round(credit * 100.0 / marked, 1)


def _working_days(session: Session, start: date, end: date) -> int:
    """Days in the range the school is open - Sundays and holidays removed."""
    holidays = repository.holidays_between(session, start, end)
    days = 0
    current = start
    while current <= end:
        if current.weekday() != CLOSED_WEEKDAY and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return days


def _name_of(student) -> str:
    """The register prints the profile's own name; never an empty cell."""
    name = (student.full_name or "").strip() if student is not None else ""
    return name or "Student"


def register(
    session: Session,
    section_id: UUID,
    on_date: date,
    subject_id: UUID | None = None,
) -> RegisterRead:
    """The roll of one class-section plus that day's answer, row by row.

    Everyone on the roll appears - `unmarked` is a state, not a missing row - because
    the screen's whole job is to show the teacher who has not been marked yet.
    """
    room = _room_or_404(session, section_id)
    students = repository.active_students(session, room.id)
    records = {
        record.student_id: record
        for record in repository.records_on(session, room.id, on_date, subject_id)
    }
    leaves = repository.approved_leave_on(
        session, [student.id for student in students], on_date
    )

    rows: list[RegisterRowRead] = []
    counts = RegisterCountsRead()
    credit = 0.0

    for student in students:
        record = records.get(student.id)
        leave = leaves.get(student.id)
        if leave is not None:
            status = AttendanceStatus.leave.value
        elif record is not None:
            status = str(record.status)
        else:
            status = "unmarked"

        if status == "unmarked":
            counts.unmarked += 1
        else:
            setattr(counts, status, getattr(counts, status, 0) + 1)
            if status != AttendanceStatus.leave.value:
                credit += CREDIT.get(status, 0.0)

        rows.append(
            RegisterRowRead(
                student_id=student.id,
                record_id=record.id if record is not None else None,
                name=_name_of(student),
                admissionNo=student.admission_number,
                status=status,
                marked=status != "unmarked",
                remarks=record.remarks if record is not None else None,
                leave_request_id=(
                    leave.id
                    if leave is not None
                    else (record.leave_request_id if record is not None else None)
                ),
            )
        )

    marked = counts.present + counts.absent + counts.late + counts.half_day
    return RegisterRead(
        section_id=room.id,
        date=on_date,
        subject_id=subject_id,
        closed_reason=closed_reason(session, on_date),
        counts=counts,
        percent=_percent(credit, marked),
        rows=rows,
    )


def _leave_days(
    requests, start: date, end: date, closed: set[date]
) -> dict[UUID, set[date]]:
    """{student_id: the open days of their approved leave inside the range}."""
    days: dict[UUID, set[date]] = {}
    for request in requests:
        if request.student_id is None:
            continue
        dates = days.setdefault(request.student_id, set())
        current = max(request.from_date, start)
        last = min(request.to_date, end)
        while current <= last:
            if current.weekday() != CLOSED_WEEKDAY and current not in closed:
                dates.add(current)
            current += timedelta(days=1)
    return days


def section_summary(
    session: Session,
    section_id: UUID,
    start: date,
    end: date,
    subject_id: UUID | None = None,
) -> SectionSummaryRead:
    """Per-student totals over a range, with the school's own threshold applied.

    One read per source - records, leaves, holidays - for the whole section, so a
    500-child summary is a handful of queries instead of one per child.
    """
    room = _room_or_404(session, section_id)
    students = repository.active_students(session, room.id)
    threshold = setting_values.get_int(session, "attendance.absence_threshold", 75)
    closed = repository.holidays_between(session, start, end)

    records = repository.records_between(session, room.id, start, end, subject_id)
    marks: dict[UUID, dict[date, str]] = {}
    for record in records:
        marks.setdefault(record.student_id, {})[record.date] = str(record.status)

    leaves = repository.approved_leaves_between(
        session, [student.id for student in students], start, end
    )
    leave_days = _leave_days(leaves, start, end, closed)

    rows: list[StudentAttendanceSummaryRead] = []
    for student in students:
        per_day = marks.get(student.id, {})
        on_leave = leave_days.get(student.id, set())
        counts = {"present": 0, "absent": 0, "late": 0, "half_day": 0, "leave": 0}
        credit = 0.0
        marked = 0

        for day in set(per_day) | on_leave:
            if day in on_leave:
                # Leave is shown, never counted as a mark: an approved leave is not
                # something the child has to make up.
                counts["leave"] += 1
                continue
            status = per_day.get(day)
            if status not in counts:
                continue
            counts[status] += 1
            credit += CREDIT.get(status, 0.0)
            marked += 1

        percent = _percent(credit, marked)
        rows.append(
            StudentAttendanceSummaryRead(
                student_id=student.id,
                name=_name_of(student),
                admissionNo=student.admission_number,
                present=counts["present"],
                absent=counts["absent"],
                late=counts["late"],
                half_day=counts["half_day"],
                leave=counts["leave"],
                marked=marked,
                percent=percent,
                threshold=threshold,
                below_threshold=percent is not None and percent < threshold,
            )
        )

    return SectionSummaryRead(
        section_id=room.id,
        from_date=start,
        to_date=end,
        working_days=_working_days(session, start, end),
        threshold=threshold,
        rows=rows,
    )


def section_trend(
    session: Session, section_id: UUID, days: int = 7, end: date | None = None
) -> SectionTrendRead:
    """The section's present-percentage day by day.

    Closed days (Sunday, holidays) are **skipped**, not drawn as 0%: a chart that dips
    to zero every Sunday teaches the reader to ignore the chart. A day nobody marked
    comes back with `percent=None` for the same reason.
    """
    room = _room_or_404(session, section_id)
    days = max(1, days)
    last = end or date.today()
    first = last - timedelta(days=days - 1)

    records = repository.records_between(session, room.id, first, last)
    per_day: dict[date, list[str]] = {}
    for record in records:
        per_day.setdefault(record.date, []).append(str(record.status))
    closed = repository.holidays_between(session, first, last)

    points: list[TrendPointRead] = []
    current = first
    while current <= last:
        if current.weekday() != CLOSED_WEEKDAY and current not in closed:
            statuses = [
                status
                for status in per_day.get(current, [])
                if status != AttendanceStatus.leave.value
            ]
            credit = sum(CREDIT.get(status, 0.0) for status in statuses)
            present = sum(
                1
                for status in statuses
                if status
                in {AttendanceStatus.present.value, AttendanceStatus.late.value}
            )
            points.append(
                TrendPointRead(
                    date=current,
                    present=present,
                    marked=len(statuses),
                    percent=_percent(credit, len(statuses)),
                )
            )
        current += timedelta(days=1)

    return SectionTrendRead(section_id=room.id, days=days, points=points)


def _consecutive_absences(
    session: Session, classroom_id: UUID, end: date
) -> dict[UUID, int]:
    """How many open days in a row each child has been absent, from `end` backwards.

    A day with no row stops the run: "not marked" is not "absent", and a school that
    has not taken the register yet must not be told a child has stopped coming.
    """
    first = end - timedelta(days=ATTENTION_DAYS + 30)
    records = repository.records_between(session, classroom_id, first, end)
    per_day: dict[date, dict[UUID, str]] = {}
    for record in records:
        per_day.setdefault(record.date, {})[record.student_id] = str(record.status)

    students = repository.active_students(session, classroom_id)
    closed = repository.holidays_between(session, first, end)
    streaks: dict[UUID, int] = {}

    for student in students:
        run = 0
        current = end
        while current >= first:
            if current.weekday() != CLOSED_WEEKDAY and current not in closed:
                status = per_day.get(current, {}).get(student.id)
                if status != AttendanceStatus.absent.value:
                    break
                run += 1
            current -= timedelta(days=1)
        if run:
            streaks[student.id] = run
    return streaks


def section_attention(
    session: Session, section_id: UUID, end: date | None = None
) -> list[AttentionRowRead]:
    """The children to ring: below the school's threshold, or absent too many in a row.

    Both limits come from `school_setting` (`attendance.absence_threshold`,
    `attendance.consecutive_days`), so a school can change what "a concern" means
    without a deploy. Sorted worst percentage first.
    """
    room = _room_or_404(session, section_id)
    last = end or date.today()
    first = last - timedelta(days=ATTENTION_DAYS - 1)

    threshold = setting_values.get_int(session, "attendance.absence_threshold", 75)
    run_limit = setting_values.get_int(session, "attendance.consecutive_days", 3)
    summary = section_summary(session, room.id, first, last)
    streaks = _consecutive_absences(session, room.id, last)

    rows: list[AttentionRowRead] = []
    for row in summary.rows:
        streak = streaks.get(row.student_id, 0)
        reasons: list[str] = []
        if row.percent is not None and row.percent < threshold:
            reasons.append(f"{row.percent}% attendance, below the {threshold}% mark")
        if streak >= run_limit:
            reasons.append(f"absent {streak} open days in a row")
        if not reasons:
            continue
        rows.append(
            AttentionRowRead(
                student_id=row.student_id,
                name=row.name,
                admissionNo=row.admissionNo,
                percent=row.percent,
                consecutive_absences=streak,
                reason="; ".join(reasons),
            )
        )

    rows.sort(key=lambda item: item.percent if item.percent is not None else 100.0)
    return rows
