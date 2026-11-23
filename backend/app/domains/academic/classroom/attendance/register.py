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
The school's weekly offs (a weekday, or "the 1st and 3rd Saturday"), the dated extra
weekly offs and its `holiday` rows are the days no register exists. Saving one is a
`409` that **names** the day ("Diwali", "1st Saturday"), because "the school is closed"
without saying why reads like a bug.

Leave is derived, never stored twice
------------------------------------
The row keeps what the teacher marked and **links** the approved request
(`leave_request_id`). Every read replaces the status with `leave` while that request is
approved, so a cancelled leave reverts to the real mark with no repair job - and the
leave itself is never copied into a second place that could disagree.
"""

from bisect import bisect_left
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
)
from app.domains.admin.settings import calendar as school_calendar
from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings import year_scope
from app.domains.admin.users.models import User

from . import notify, repository
from .models import AttendanceAuditLog, AttendanceRecord, AttendanceStatus
from .schemas import (
    AttendanceBulkCreate,
    AttentionRowRead,
    ClosedDayRead,
    ClosureDeleteRead,
    ClosureDeleteWrite,
    ClosureImpactDayRead,
    ClosureImpactRead,
    ClosureImpactSectionRead,
    LateStudentRowRead,
    LateStudentsRead,
    RegisterCountsRead,
    RegisterRead,
    RegisterRowRead,
    SectionCalendarDayRead,
    SectionCalendarRead,
    SectionSummaryRead,
    SectionTrendRead,
    StudentAttendanceSummaryRead,
    TrendPointRead,
)

#: How far back the consecutive-absence streak looks for its run.
ATTENTION_DAYS = 30

#: The share of a month's open days at which "late sometimes" becomes "late often".
#: One key, one default - the late card reads it and nothing else repeats the number.
LATE_SHARE_PERCENT = "attendance.late_share_percent"

#: Month names for the late card's heading, spelled out so the label never depends on
#: the server's locale.
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

#: Statuses that count as attendance, and the credit each one earns.
CREDIT: dict[str, float] = {
    AttendanceStatus.present.value: 1.0,
    AttendanceStatus.late.value: 1.0,
    AttendanceStatus.half_day.value: 0.5,
    AttendanceStatus.absent.value: 0.0,
}

#: The trend's short axis words, spelled out so the chart reads the same in every locale.
WEEKDAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTH_SHORT = tuple(name[:3] for name in MONTH_NAMES)


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
    """Why the school is closed that day (`"Sunday"`, `"Diwali"`), else `None`.

    The answer comes from the school's own calendar (`admin/settings/calendar.py`):
    the weekly off days it chose, plus its holiday rows. Nothing here knows about
    Sunday any more - a school that also closes on Saturdays says so once, and
    every screen follows without another copy of the rule.
    """
    return school_calendar.closed_reason(session, on_date)


def closed_days(session: Session, start: date, end: date) -> list[ClosedDayRead]:
    """Every day in the range the register cannot be taken - the calendar's closed days.

    The words and the kind both come from `admin/settings/calendar.py`: a weekday off, a
    "1st Saturday" rule, a dated weekly off and a holiday each answer with their own
    reason and their own colour, so the date control, the month calendar and the toolbar
    can never describe the same day differently.
    """
    #: A year is the widest calendar the screen ever asks for; more is a mistake, not a
    #: feature, and would be a long loop returning rows nobody draws.
    if (end - start).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Ask for a range of a year or less.",
        )

    return [
        ClosedDayRead(date=day, reason=found.reason, kind=found.kind)
        for day, found in sorted(school_calendar.closures(session, start, end).items())
    ]


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


def _writable_year(session: Session, day: date):
    """The academic year `day` may be saved in, or a `409` that says why not.

    Attendance is a record of what happened, so it is written only in **the year today
    falls in**, on a day that has already arrived, and only while that same year is the
    one on screen - a previous or next year is read-only even when it is selected.
    """
    today = date.today()
    real = year_scope.todays_year(session, today)
    if real is None:
        raise HTTPException(
            status_code=409,
            detail="No academic year covers today, so attendance cannot be saved yet.",
        )
    selected = year_scope.current_academic_year(session)
    if selected is not None and selected.id != real.id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{selected.name} is on screen but today belongs to {real.name}. "
                f"Attendance can only be saved in {real.name}; "
                f"{selected.name} is read-only."
            ),
        )
    if not (real.start_date <= day <= real.end_date):
        raise HTTPException(
            status_code=409,
            detail=(
                f"{day.isoformat()} is outside {real.name}. Attendance can only be saved "
                f"for dates inside the current session year ({real.name})."
            ),
        )
    if day > today:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{day.isoformat()} has not arrived yet. Attendance can be saved for "
                "today and earlier days only."
            ),
        )
    return real


def save_register(
    session: Session, payload: AttendanceBulkCreate, user: User | None = None
) -> list[AttendanceRecord]:
    """Upsert a whole class-section's register for one day (and subject).

    Returns the rows as they now stand. Every status/remarks change writes an audit
    row naming the user who made it, so "who marked this child absent" is answerable.
    """
    room = _room_or_404(session, payload.section_id)
    if payload.classroom_subject_id is not None:
        from app.domains.academic.classroom.course.subjects import (
            require_section_subject,
        )

        require_section_subject(session, room.id, payload.classroom_subject_id)

    # The school's own closed days answer first (holiday logic is unchanged); then the
    # session-year rules decide whether the day may be written at all.
    reason = closed_reason(session, payload.date)
    if reason is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{payload.date.isoformat()} is closed - {reason}. "
                "A register cannot be saved on a closed day."
            ),
        )
    year = _writable_year(session, payload.date)

    roll = {
        student.id: student for student in repository.active_students(session, room.id)
    }
    enrollments = repository.enrollments_in_year(session, list(roll), year.id)
    missing = [
        _name_of(student)
        for student_id, student in roll.items()
        if student_id not in enrollments
    ]
    if missing:
        shown = ", ".join(missing[:3]) + (
            f" and {len(missing) - 3} more" if len(missing) > 3 else ""
        )
        raise HTTPException(
            status_code=409,
            detail=(
                f"{shown} {'has' if len(missing) == 1 else 'have'} no enrollment in "
                f"{year.name}, so attendance cannot be saved. "
                "Enrol the student in this year first."
            ),
        )
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
            session, row.student_id, payload.date, payload.classroom_subject_id
        )

        if existing is None:
            record = AttendanceRecord(
                student_id=row.student_id,
                classroom_id=room.id,
                classroom_subject_id=payload.classroom_subject_id,
                date=payload.date,
                status=row.status,
                remarks=row.remarks,
                leave_request_id=leave.id if leave is not None else None,
                enrollment_id=enrollments[row.student_id],
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
        existing.enrollment_id = enrollments[row.student_id]
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


def year_percentages(
    session: Session, student_ids: list[UUID], start: date, end: date
) -> dict[UUID, float | None]:
    """{student_id: attendance %} over one academic year's window - a single query.

    The same rule the register's rows use: only days the school was open count, a day
    on approved leave is out of the denominator, and half a day earns half the credit.
    `None` for a child with nothing marked in the window (no data is not 0%).
    """
    if not student_ids:
        return {}
    closed = set(school_calendar.closures(session, start, end))
    credit: dict[UUID, float] = {}
    marked: dict[UUID, int] = {}
    for student_id, day, status in session.exec(
        select(
            AttendanceRecord.student_id, AttendanceRecord.date, AttendanceRecord.status
        ).where(
            AttendanceRecord.student_id.in_(student_ids),
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= end,
        )
    ).all():
        value = getattr(status, "value", status)
        if day in closed or value == AttendanceStatus.leave.value:
            continue
        marked[student_id] = marked.get(student_id, 0) + 1
        credit[student_id] = credit.get(student_id, 0.0) + CREDIT.get(value, 0.0)
    return {
        student_id: _percent(credit.get(student_id, 0.0), marked.get(student_id, 0))
        for student_id in student_ids
    }


def _share(part: int, total: int) -> float | None:
    """A percentage over the **open days**, or `None` when there were none.

    One formula for every screen: a child's attendance is what they attended over the
    days the school was open. Dividing by "the days somebody remembered to mark" made
    a half-taken month read as 100%.
    """
    if total <= 0:
        return None
    return round(part * 100.0 / total, 1)


def _working_days(session: Session, start: date, end: date) -> int:
    """Days in the range the school is open - weekly offs and holidays removed."""
    return school_calendar.count_open_days(session, start, end)


def attendance_window(
    session: Session, classroom_id: UUID, today: date | None = None
) -> tuple[date, date] | None:
    """The days this section's attendance tab measures over.

    It starts on the first day **anybody** on the roll was marked - a class whose
    register began mid-month is not judged against days that predate it - and ends on the
    **last day the register holds**. A day nobody has marked yet is not a day anybody was
    absent from, so it must not sit in the denominator and drag every percentage down;
    opening the tab tomorrow morning cannot change yesterday's numbers.

    `today` only caps the end: a register cannot hold a future day, but the clock is never
    allowed to extend the window past the data. `None` when the register has never been
    saved: no data is an honest answer, and a zero denominator is not.
    """
    span = session.exec(
        year_scope.by_date_window(
            session,
            select(
                func.min(AttendanceRecord.date), func.max(AttendanceRecord.date)
            ).where(AttendanceRecord.classroom_id == classroom_id),
            AttendanceRecord.date,
        )
    ).first()
    if span is None or span[0] is None:
        return None
    first, last = span
    if today is not None and last > today:
        last = today
    return (first if first <= last else last, last)


def _month_first(day: date) -> date:
    """The first day of `day`'s month."""
    return day.replace(day=1)


def _month_last(day: date) -> date:
    """The last day of `day`'s month (leap years included - it is date arithmetic)."""
    return (_month_first(day) + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def _cutoff(session: Session, classroom_id: UUID, clock: date) -> date:
    """The last day the annual figure may judge: today when it is saved, else yesterday.

    One rule, not two: a day the teacher may still be about to mark is not an absence, and
    a day that has passed without a register is. The cutoff is the last day the section's
    own register reaches - never a day in the future, and never the clock by itself.
    """
    if repository.saved_dates(session, classroom_id, clock, clock):
        return clock
    return clock - timedelta(days=1)


def _month_cutoff(
    session: Session,
    classroom_id: UUID,
    month_first: date,
    month_last: date,
    until: date | None,
    clock: date,
) -> date:
    """Where the month's fraction stops.

    A **completed** month divides by all of its open days - that is what makes a forgotten
    register visible instead of flattering. The month we are living in stops on the day on
    screen, and steps back one day when that day has no register yet.
    """
    if month_last < clock:
        return month_last
    base = min(until or clock, clock, month_last)
    if repository.saved_dates(session, classroom_id, base, base):
        return base
    return base - timedelta(days=1)


def last_complete_month(today: date | None = None) -> tuple[date, date, str]:
    """The month before the one `today` falls in: first day, last day, and its name."""
    anchor = today or date.today()
    last = anchor.replace(day=1) - timedelta(days=1)
    first = last.replace(day=1)
    return first, last, f"{MONTH_NAMES[first.month - 1]} {first.year}"


def _name_of(student) -> str:
    """The register prints the profile's own name; never an empty cell."""
    name = (student.full_name or "").strip() if student is not None else ""
    return name or "Student"


def register(
    session: Session,
    section_id: UUID,
    on_date: date,
    classroom_subject_id: UUID | None = None,
) -> RegisterRead:
    """The roll of one class-section plus that day's answer, row by row.

    Everyone on the roll appears - `unmarked` is a state, not a missing row - because
    the screen's whole job is to show the teacher who has not been marked yet. A child who
    has since left still appears, flagged `active=False`: the register is a record of the
    section, and hiding a name makes a hole look like a complete day.
    """
    room = _room_or_404(session, section_id)
    students = repository.roll_students(session, room.id)
    records = {
        record.student_id: record
        for record in repository.records_on(
            session, room.id, on_date, classroom_subject_id
        )
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
                active=student.deactivated_at is None,
                leave_request_id=(
                    leave.id
                    if leave is not None
                    else (record.leave_request_id if record is not None else None)
                ),
            )
        )

    marked = counts.present + counts.absent + counts.late + counts.half_day
    closed = school_calendar.closure(session, on_date)
    return RegisterRead(
        section_id=room.id,
        date=on_date,
        classroom_subject_id=classroom_subject_id,
        closed_reason=closed.reason if closed else None,
        closed_kind=closed.kind if closed else None,
        counts=counts,
        percent=_percent(credit, marked),
        rows=rows,
    )


def section_calendar(
    session: Session, section_id: UUID, start: date, end: date
) -> SectionCalendarRead:
    """The month the register's date control draws: closed days and saved days.

    One row per day of the window, oldest first. The server says **why** each day is
    closed and whether a register exists, so the calendar never derives a colour from a
    weekday number on the client - the screen paints what it is given, and the same
    closed day can never look different on two machines.
    """
    if (end - start).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Ask for a range of a year or less.",
        )
    room = _room_or_404(session, section_id)
    closed = school_calendar.closures(session, start, end)
    saved = repository.saved_dates(session, room.id, start, end)

    days: list[SectionCalendarDayRead] = []
    current = start
    while current <= end:
        found = closed.get(current)
        days.append(
            SectionCalendarDayRead(
                date=current,
                closed_kind=found.kind if found else None,
                closed_reason=found.reason if found else None,
                saved=current in saved,
            )
        )
        current += timedelta(days=1)
    return SectionCalendarRead(
        section_id=room.id, from_date=start, to_date=end, days=days
    )


def _leave_days(
    requests, start: date, end: date, open_set: set[date]
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
            if current in open_set:
                dates.add(current)
            current += timedelta(days=1)
    return days


def _section_names(
    session: Session, room_ids: set[UUID]
) -> dict[UUID, tuple[str, str]]:
    """{classroom id: (class name, section name)} - one read per table, never per row."""
    if not room_ids:
        return {}
    rooms = session.exec(select(Classroom).where(Classroom.id.in_(room_ids))).all()
    classes = session.exec(
        select(ClassName).where(
            ClassName.class_id.in_({room.class_id for room in rooms})
        )
    ).all()
    sections = session.exec(
        select(Section).where(
            Section.section_id.in_({room.section_id for room in rooms})
        )
    ).all()
    class_names = {row.class_id: row.classname for row in classes}
    section_names = {row.section_id: row.section_name for row in sections}
    return {
        room.id: (
            class_names.get(room.class_id, ""),
            section_names.get(room.section_id, ""),
        )
        for room in rooms
    }


def _register_days(
    session: Session, start: date, end: date, only: set[date] | None = None
) -> dict[date, dict[UUID, tuple[set[UUID], int]]]:
    """{day: {classroom id: (students, records)}} for the days that already have a register.

    One query for the window: `only` narrows it to the days a proposed closure would hit,
    without asking the database once per day.
    """
    on_date = AttendanceRecord.date
    rows = session.exec(
        select(
            on_date, AttendanceRecord.classroom_id, AttendanceRecord.student_id
        ).where(on_date >= start, on_date <= end)
    ).all()
    per_day: dict[date, dict[UUID, tuple[set[UUID], int]]] = {}
    for day, classroom_id, student_id in rows:
        if only is not None and day not in only:
            continue
        students, records = per_day.setdefault(day, {}).setdefault(
            classroom_id, (set(), 0)
        )
        students.add(student_id)
        per_day[day][classroom_id] = (students, records + 1)
    return per_day


def _impact_read(
    session: Session,
    start: date,
    end: date,
    per_day: dict[date, dict[UUID, tuple[set[UUID], int]]],
    reasons: dict[date, tuple[str, str]],
) -> ClosureImpactRead:
    """Turn the raw per-day counts into the words the warning prints."""
    names = _section_names(
        session, {room for rooms in per_day.values() for room in rooms}
    )
    days: list[ClosureImpactDayRead] = []
    total = 0
    for day in sorted(per_day):
        kind, reason = reasons.get(day, ("", ""))
        sections = [
            ClosureImpactSectionRead(
                section_id=room,
                class_name=names.get(room, ("", ""))[0],
                section_name=names.get(room, ("", ""))[1],
                students=len(students),
                records=records,
            )
            for room, (students, records) in sorted(per_day[day].items())
        ]
        day_total = sum(section.records for section in sections)
        total += day_total
        days.append(
            ClosureImpactDayRead(
                date=day,
                reason=reason,
                kind=kind,
                total_records=day_total,
                sections=sections,
            )
        )
    return ClosureImpactRead(
        from_date=start, to_date=end, total_records=total, days=days
    )


def closure_impact(session: Session, start: date, end: date) -> ClosureImpactRead:
    """Which class-sections already hold a register in the window.

    This is the **warning** a closure must show before it is saved: the names and the counts
    of the registers a confirm would delete. Reading it never changes anything.
    """
    per_day = _register_days(session, start, end)
    closed = school_calendar.closures(session, start, end)
    reasons = {day: (found.kind, found.reason) for day, found in closed.items()}
    return _impact_read(session, start, end, per_day, reasons)


def weekly_off_impact(
    session: Session, start: date, end: date, days: list[int], nth: list[str]
) -> ClosureImpactRead:
    """What a **proposed** weekly-off setting would delete: nothing.

    A rule never takes back a day that already has a register - `admin/settings/calendar`
    skips exactly those days when it decides whether a date is closed - so a weekly-off save
    cannot remove a mark, and the honest preview is empty. The window is still checked and the
    shape is unchanged, so an older caller that asks gets a truthful answer rather than a
    scare; the Calendar page does not need to ask at all.
    """
    if end < start:
        raise HTTPException(
            status_code=422, detail="The end of the window cannot be before its start."
        )
    return ClosureImpactRead(from_date=start, to_date=end, total_records=0, days=[])


def delete_closure_records(
    session: Session, payload: ClosureDeleteWrite
) -> ClosureDeleteRead:
    """Delete the register rows of the days being closed - **only** on an explicit confirm.

    A calendar change used to leave every saved register in place; the school asked for the
    opposite, with two guards: the caller must send the window (this is never a side effect of
    saving a holiday), and the impact is shown first, by name and by count.

    Audit rows go first (their foreign key points at the register row), then the rows
    themselves, in one transaction: a half-deleted day is worse than either answer.
    """
    if not payload.dates and (payload.from_date is None or payload.to_date is None):
        raise HTTPException(
            status_code=422,
            detail="Name the days: either `dates`, or both ends of the range.",
        )
    if (
        payload.dates
        and payload.from_date is not None
        and payload.to_date is not None
        and payload.to_date < payload.from_date
    ):
        raise HTTPException(
            status_code=422, detail="The end of the window cannot be before its start."
        )

    on_date = AttendanceRecord.date
    statement = select(AttendanceRecord.id, on_date)
    if payload.dates:
        # Exactly these days - what the warning listed, no open day in between.
        statement = statement.where(on_date.in_(sorted(set(payload.dates))))
    else:
        statement = statement.where(
            on_date >= payload.from_date, on_date <= payload.to_date
        )
    if payload.section_ids:
        statement = statement.where(
            AttendanceRecord.classroom_id.in_(payload.section_ids)
        )
    rows = session.exec(statement).all()
    if not rows:
        return ClosureDeleteRead()

    record_ids = [row[0] for row in rows]
    days = sorted({row[1] for row in rows})
    audit_rows = 0
    # Chunked, so a big window cannot blow a driver's bound-parameter limit.
    for start in range(0, len(record_ids), 500):
        chunk = record_ids[start : start + 500]
        audit_rows += int(
            session.exec(
                select(func.count(AttendanceAuditLog.id)).where(
                    AttendanceAuditLog.attendance_record_id.in_(chunk)
                )
            ).one()
            or 0
        )
        session.exec(
            delete(AttendanceAuditLog).where(
                AttendanceAuditLog.attendance_record_id.in_(chunk)
            )
        )
        session.exec(delete(AttendanceRecord).where(AttendanceRecord.id.in_(chunk)))
    session.commit()
    return ClosureDeleteRead(
        deleted_records=len(record_ids), deleted_audit_rows=audit_rows, days=days
    )


def section_summary(
    session: Session,
    section_id: UUID,
    start: date | None = None,
    end: date | None = None,
    classroom_subject_id: UUID | None = None,
    until: date | None = None,
    month: date | None = None,
    today: date | None = None,
) -> SectionSummaryRead:
    """Per-student totals, with the school's own threshold applied.

    Two figures come out of one read, because the screen prints two:

    * the **annual** percentage - present + late over the open days since the child's
      first mark, up to the **cutoff**;
    * the **month** fraction - `Monthly attendance 5/12`, present + late over the month's
      open days up to the same kind of cutoff.

    The cutoff is what keeps an unsaved day honest. For the year it is `today` when this
    section has a register today, and yesterday otherwise: a day somebody may still be
    about to mark is not an absence, and a day that has passed without a register is. A
    **completed** month divides by all of its open days; the month we are living in
    divides by the open days up to the day on screen (or the day before it, when that day
    has no register yet). Marking the 19th reads `5/12`; a month whose 19th was never
    marked reads `5/11` - the day is neither counted present nor quietly dropped.

    An explicit `start`/`end` is taken **literally** - the reports ask for a range and get
    exactly that range. Only the screen's own call, which names no end, is cut at the
    clock. `month` picks the month the row figures describe (any day inside it).

    One read per source - records, leaves, holidays - for the whole section, so a
    500-child summary is a handful of queries instead of one per child.
    """
    room = _room_or_404(session, section_id)
    students = repository.active_students(session, room.id)
    threshold = setting_values.get_int(session, "attendance.absence_threshold", 75)
    clock = today or date.today()
    anchor = until or month or clock

    first = start
    if first is None:
        window = attendance_window(session, room.id, today=clock)
        if window is None:
            # Nothing has ever been saved here: no rows, no percentages, no error.
            return SectionSummaryRead(
                section_id=room.id,
                from_date=anchor,
                to_date=anchor,
                working_days=0,
                threshold=threshold,
                month_from_date=_month_first(anchor),
                month_to_date=_month_first(anchor) - timedelta(days=1),
                rows=[],
            )
        first = window[0]

    # Where the annual figure stops. A named range is measured exactly; the screen's own
    # window stops at the cutoff, so a day after it cannot pull every child down.
    last = end if end is not None else _cutoff(session, room.id, clock)
    if last < first:
        # The reader is standing before this class's first register: nothing to judge.
        last = first - timedelta(days=1)

    # The month: all of its open days once it is over, up to the day on screen while it is
    # still being lived in.
    month_first = _month_first(month or last)
    month_last = _month_last(month_first)
    month_cut = _month_cutoff(session, room.id, month_first, month_last, until, clock)
    if end is not None:
        month_cut = min(month_cut, end)
    if month_cut < month_first:
        # The month has not started yet - a dash, never `0/0`.
        month_cut = month_first - timedelta(days=1)

    # The one calendar: weekly offs + holidays. Everything below counts from these.
    open_year = school_calendar.open_days(session, first, last) if last >= first else []
    open_month = (
        school_calendar.open_days(session, month_first, month_cut)
        if month_cut >= month_first
        else []
    )
    open_set = set(open_year) | set(open_month)
    month_open_set = set(open_month)

    # The row's tooltip: registers actually taken inside the counting month. Not the
    # denominator any more - an open day nobody marked is still an open day.
    month_saved = len(
        {
            day
            for day in repository.saved_dates(session, room.id, month_first, month_last)
            if day <= month_cut
        }
        & month_open_set
    )

    window_end = max(last, month_cut)
    records = repository.records_between(
        session, room.id, first, window_end, classroom_subject_id
    )
    marks: dict[UUID, dict[date, str]] = {}
    for record in records:
        marks.setdefault(record.student_id, {})[record.date] = str(record.status)

    leaves = repository.approved_leaves_between(
        session, [student.id for student in students], first, window_end
    )
    leave_days = _leave_days(leaves, first, window_end, open_set)

    rows: list[StudentAttendanceSummaryRead] = []
    for student in students:
        per_day = marks.get(student.id, {})
        on_leave = leave_days.get(student.id, set())
        counts = {"present": 0, "absent": 0, "late": 0, "half_day": 0, "leave": 0}
        month_counts = {"present": 0, "absent": 0, "late": 0}
        marked = 0

        for day in set(per_day) | on_leave:
            if day not in open_set:
                # A closed day is not attendance, even when a register was saved on
                # it before the holiday existed. The rows are kept; nothing counts
                # them, and removing the holiday brings the day straight back.
                continue
            if day in on_leave:
                # Leave is shown, never counted as a mark: an approved leave is not
                # something the child has to make up.
                counts["leave"] += 1
                continue
            status = per_day.get(day)
            if status not in counts:
                continue
            counts[status] += 1
            if day in month_open_set and status in month_counts:
                month_counts[status] += 1
            marked += 1

        # A child who joined after the class's register began is not judged against the
        # days before they arrived: their own denominator starts on their first mark. A
        # stored `leave` is not a mark - the child was not in school that day - so it
        # never starts the clock.
        first_mark = min(
            (
                day
                for day, status in per_day.items()
                if status != AttendanceStatus.leave.value and day in open_set
            ),
            default=None,
        )
        year_from = first if first_mark is None else max(first, first_mark)
        year_open = len(open_year) - bisect_left(open_year, year_from)
        month_from = month_first if first_mark is None else max(month_first, first_mark)
        month_open = len(open_month) - bisect_left(open_month, month_from)

        # Present + late over the open days; no data (nobody marked) is `None`, not 0%.
        percent = (
            None
            if marked == 0
            else _share(counts["present"] + counts["late"], year_open)
        )
        rows.append(
            StudentAttendanceSummaryRead(
                student_id=student.id,
                name=_name_of(student),
                admissionNo=student.admission_number,
                present=counts["present"],
                # Late counts as present: the child was in school, just after the bell.
                present_total=counts["present"] + counts["late"],
                absent=counts["absent"],
                late=counts["late"],
                half_day=counts["half_day"],
                leave=counts["leave"],
                marked=marked,
                # The row's "Monthly attendance 5/12": present-and-late over the month's
                # open days up to its cutoff - never the count of registers taken.
                month_present_total=month_counts["present"] + month_counts["late"],
                month_absent=month_counts["absent"],
                month_open_days=month_open,
                month_saved=month_saved,
                # The days this child's percentage divides by (their own start when they
                # joined later than the class's register).
                open_days=year_open,
                percent=percent,
                threshold=threshold,
                below_threshold=percent is not None and percent < threshold,
            )
        )

    return SectionSummaryRead(
        section_id=room.id,
        from_date=first,
        to_date=last,
        working_days=len(open_year),
        threshold=threshold,
        month_from_date=month_first,
        month_to_date=month_cut,
        rows=rows,
    )


def section_month(
    session: Session, section_id: UUID, today: date | None = None
) -> tuple[float | None, int]:
    """The section's month figure for the page header, and the days it divides by.

    Same formula as the rows: `(present + late) / (open days * strength)` over the
    month the register's last saved day falls in. With no marks in that month the
    answer is `None` - a `0%` here would read as "nobody came to school", which is
    not what "the register was never taken" means. Open days come from the calendar,
    so a Sunday or a holiday never sits in the denominator.
    """
    room = _room_or_404(session, section_id)
    window = attendance_window(session, room.id, today=today)
    if window is None:
        return None, 0
    start, end = window
    month_start = max(start, end.replace(day=1))
    open_days = school_calendar.open_days(session, month_start, end)
    students = repository.active_students(session, room.id)
    if not open_days or not students:
        return None, len(open_days)

    open_set = set(open_days)
    marked = credit = 0
    for record in repository.records_between(session, room.id, month_start, end):
        if record.date not in open_set:
            continue
        status = str(record.status)
        if status == AttendanceStatus.leave.value:
            # An approved leave is neither a mark nor an absence - it was never school.
            continue
        marked += 1
        if status in {AttendanceStatus.present.value, AttendanceStatus.late.value}:
            credit += 1
    if marked == 0:
        return None, len(open_days)
    return _share(credit, len(open_days) * len(students)), len(open_days)


def _span_totals(
    per_day: dict[date, list[str]], open_set: set[date], first: date, last: date
) -> tuple[int, int, float | None]:
    """One bar's numbers: present, marked and credit over the span's open days.

    An approved leave is not a mark (it was never school), so it is dropped before the
    divide - the same rule the rows use, applied to a span instead of a child.
    """
    statuses: list[str] = []
    current = first
    while current <= last:
        if current in open_set:
            statuses.extend(
                status
                for status in per_day.get(current, [])
                if status != AttendanceStatus.leave.value
            )
        current += timedelta(days=1)
    credit = sum(CREDIT.get(status, 0.0) for status in statuses)
    present = sum(
        1
        for status in statuses
        if status in {AttendanceStatus.present.value, AttendanceStatus.late.value}
    )
    return present, len(statuses), _percent(credit, len(statuses))


def _week_spans(anchor: date, count: int) -> list[tuple[date, date]]:
    """The month's weeks - 1-7, 8-14, 15-21, 22-28, 29-end - newest first, then reversed.

    A week here is a slice of its **month**, not of the ISO calendar: "the 3rd week of
    November" is what a school means. The slice holding `anchor` stops on `anchor`, so the
    chart never draws a day that has not happened.
    """
    wanted = max(1, count)
    spans: list[tuple[date, date]] = []
    cursor = anchor
    while len(spans) < wanted:
        month_first = _month_first(cursor)
        month_last = _month_last(month_first)
        starts = [month_first + timedelta(days=offset) for offset in (0, 7, 14, 21, 28)]
        for index in range(4, -1, -1):
            start = starts[index]
            stop = month_last if index == 4 else starts[index + 1] - timedelta(days=1)
            stop = min(stop, cursor)
            if stop < start:
                continue
            spans.append((start, stop))
            if len(spans) == wanted:
                break
        cursor = month_first - timedelta(days=1)
    spans.reverse()
    return spans


def _month_spans(anchor: date, count: int) -> list[tuple[date, date]]:
    """The last `count` calendar months, oldest first; the running one stops on `anchor`."""
    spans: list[tuple[date, date]] = []
    month_first = _month_first(anchor)
    for _ in range(max(1, count)):
        if month_first <= anchor:
            spans.append((month_first, min(_month_last(month_first), anchor)))
        month_first = _month_first(month_first - timedelta(days=1))
    spans.reverse()
    return spans


def _span_label(start: date, stop: date, scale: str) -> str:
    """The axis word for a span: `"Nov"`, or `"3rd wk Nov"` for the month's third week."""
    month = MONTH_SHORT[start.month - 1]
    if scale != "week":
        return month
    ordinal = ("1st", "2nd", "3rd", "4th", "5th")[min(4, (start.day - 1) // 7)]
    return f"{ordinal} wk {month}"


def section_trend(
    session: Session,
    section_id: UUID,
    days: int = 7,
    end: date | None = None,
    bucket: str = "day",
    limit: int | None = None,
    today: date | None = None,
) -> SectionTrendRead:
    """The section's present percentage on the scale the card is showing.

    * `day` - one point per **open** day (weekly offs and holidays skipped, never drawn as
      0%): the last `days` of the register, ending on the day on screen.
    * `week` - the month cut into 1-7 / 8-14 / 15-21 / 22-28 / 29-end, so the bars answer
      "how did this month go" without a month of unreadable weekdays.
    * `month` - one point per calendar month.

    With no `end` the chart ends on the **last day the register holds**, so it never trails
    off into a stretch of days nobody marked. A span nobody marked still comes back with
    `percent=None` - "no data" is an answer, and `0%` is a different one.
    """
    room = _room_or_404(session, section_id)
    clock = today or date.today()
    if end is not None:
        # A caller who names the last day gets that day - a report may look at a window
        # that ends before today, and it is measured as asked.
        anchor = end
    else:
        # Otherwise the chart ends on the last day the register holds, so its last bar
        # always describes a day the school actually marked.
        window = attendance_window(session, room.id, today=clock)
        anchor = window[1] if window else clock

    scale = bucket if bucket in {"day", "week", "month"} else "day"
    if scale == "week":
        spans = _week_spans(anchor, limit or 5)
    elif scale == "month":
        spans = _month_spans(anchor, limit or 6)
    else:
        spans = [(anchor - timedelta(days=max(1, limit or days) - 1), anchor)]

    if not spans:
        return SectionTrendRead(section_id=room.id, range=scale, days=days, points=[])

    span_first = min(start for start, _ in spans)
    span_last = max(stop for _, stop in spans)
    # One read for every bar: a month of weeks is still one query, not five.
    per_day: dict[date, list[str]] = {}
    for record in repository.records_between(session, room.id, span_first, span_last):
        per_day.setdefault(record.date, []).append(str(record.status))
    open_set = set(school_calendar.open_days(session, span_first, span_last))

    points: list[TrendPointRead] = []
    if scale == "day":
        current = span_first
        while current <= span_last:
            if current in open_set:
                present, marked, percent = _span_totals(
                    per_day, open_set, current, current
                )
                points.append(
                    TrendPointRead(
                        date=current,
                        label=WEEKDAY_SHORT[current.weekday()],
                        present=present,
                        marked=marked,
                        percent=percent,
                    )
                )
            current += timedelta(days=1)
    else:
        for start, stop in spans:
            present, marked, percent = _span_totals(per_day, open_set, start, stop)
            points.append(
                TrendPointRead(
                    date=start,
                    label=_span_label(start, stop, scale),
                    present=present,
                    marked=marked,
                    percent=percent,
                    end_date=stop,
                )
            )

    return SectionTrendRead(section_id=room.id, range=scale, days=days, points=points)


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
    open_day_set = set(school_calendar.open_days(session, first, end))
    streaks: dict[UUID, int] = {}

    for student in students:
        run = 0
        current = end
        while current >= first:
            if current in open_day_set:
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
    # The same window the roster prints (first saved day -> last saved day), so a child's
    # percentage here is the percentage beside their name in that table.
    window = attendance_window(session, room.id, today=end)
    if window is None:
        return []
    first, last = window

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


def late_students_last_month(
    session: Session, section_id: UUID, today: date | None = None
) -> LateStudentsRead:
    """The children late more often than the school tolerates, over the last month.

    The month is the last **complete** one (in December it is November), because a
    share of a half-finished month swings wildly: one early late day would read as a
    huge percentage. Open days are the calendar's own (weekly offs and holidays
    removed), and the threshold is `attendance.late_share_percent` - one key, read
    here and nowhere else.

    A month with no register at all comes back with `marked_days == 0` and no rows,
    so the screen can say "no data yet" instead of "nobody was late".
    """
    room = _room_or_404(session, section_id)
    first, last, label = last_complete_month(today)
    share = setting_values.get_int(session, LATE_SHARE_PERCENT, 5)
    open_days = school_calendar.open_days(session, first, last)
    open_total = len(open_days)
    open_set = set(open_days)

    records = repository.records_between(session, room.id, first, last)
    marked_days = {record.date for record in records if record.date in open_set}
    late: dict[UUID, int] = {}
    for record in records:
        if str(record.status) != AttendanceStatus.late.value:
            continue
        if record.date not in open_set:
            continue
        late[record.student_id] = late.get(record.student_id, 0) + 1

    rows: list[LateStudentRowRead] = []
    if open_total > 0:
        for student in repository.active_students(session, room.id):
            count = late.get(student.id, 0)
            if count == 0:
                continue
            # "More than the share" compared in whole days, so rounding to one decimal
            # can never pull a child in or out at the boundary.
            if count * 100 <= share * open_total:
                continue
            rows.append(
                LateStudentRowRead(
                    student_id=student.id,
                    name=_name_of(student),
                    late=count,
                    percent=_share(count, open_total) or 0.0,
                )
            )

    rows.sort(key=lambda row: (row.percent, row.late), reverse=True)
    return LateStudentsRead(
        from_date=first,
        to_date=last,
        month_label=label,
        open_days=open_total,
        marked_days=len(marked_days),
        threshold=share,
        rows=rows,
    )
