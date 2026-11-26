from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import holidays as holiday_service
from . import register as register_service
from . import service
from .models import AttendanceRecord
from .schemas import (
    AttendanceBulkCreate,
    AttendanceRecordRead,
    AttentionRowRead,
    ClosedDayRead,
    ClosureDeleteRead,
    ClosureDeleteWrite,
    ClosureImpactRead,
    HolidayCalendarRead,
    HolidayImpact,
    HolidayWrite,
    IrregularStudentRead,
    LateStudentsRead,
    LeaveSyncRowRead,
    OpenDayRead,
    OpenDayWrite,
    RegisterRead,
    SectionCalendarRead,
    SectionSummaryRead,
    SectionTrendRead,
    WeeklyOffRead,
    WeeklyOffWrite,
)

router = APIRouter()


def _as_read(
    session: Session, records: list[AttendanceRecord]
) -> list[AttendanceRecordRead]:
    """The save answers with the same shape the reads use (one row per child)."""
    return [service.build_record_read(session, record) for record in records]


@router.post(
    "/bulk",
    response_model=list[AttendanceRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def mark_attendance_bulk(
    bulk_data: AttendanceBulkCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.mark")),
):
    """Save a whole class-section's register for one day.

    Saving the same day twice **updates** it (one row per child/day/subject), and every
    status change leaves an audit row naming who made it. A closed day (Sunday, a
    holiday) is refused with `409` naming the day.

    A **future** day is refused with `422`: the register records what happened, and a day
    that has not happened cannot be marked. Past days stay editable - a correction is a
    normal thing to need - so the rule is one comparison against today, not a lock.
    """
    from app.domains.academic.classroom.academics.models import Section
    from app.domains.auth.service import AuthorizationService

    if bulk_data.date > date.today():
        raise HTTPException(
            status_code=422,
            detail=(
                f"The register cannot be taken for {bulk_data.date:%d %b %Y}: "
                "a day that has not happened cannot be marked."
            ),
        )

    # The class comes from the section, so the caller names the section and the
    # scope check resolves the class it belongs to.
    section = session.get(Section, bulk_data.section_id)
    class_id = section.class_id if section else None

    # Normally the class's own teachers. A teacher the office has handed this class-section's
    # attendance to **for this date** may also save it - that one grant, nothing wider.
    from app.domains.people.teachers.substitution.attendance_access import has_access

    if not AuthorizationService.can(
        current_user,
        "attendance.mark",
        session=session,
        class_id=class_id,
        classroom_subject_id=bulk_data.classroom_subject_id,
    ) and not has_access(session, current_user, bulk_data.section_id, bulk_data.date):
        raise HTTPException(
            status_code=403, detail="Not authorized to mark attendance for this scope."
        )

    saved = register_service.save_register(session, bulk_data, user=current_user)
    return _as_read(session, saved)


@router.get(
    "/class/{class_id}/section/{section_id}", response_model=list[AttendanceRecordRead]
)
def read_attendance_by_class(
    class_id: UUID,
    section_id: UUID,
    target_date: date,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    Fetch the attendance records for a specific date (to load the attendance register).

    `class_id` stays in the path for the existing callers, but the lookup is by
    section - the class is `section.class_id`.
    """
    return service.get_attendance_by_section_and_date(
        session=session,
        section_id=section_id,
        target_date=target_date,
    )


@router.get("/student/{student_id}", response_model=list[AttendanceRecordRead])
def read_attendance_by_student(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    Fetch the attendance history for a single student.
    """
    return service.get_attendance_by_student(session=session, student_id=student_id)


@router.get("", response_model=list[AttendanceRecordRead])
def read_all_attendance(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    List all attendance records with pagination.
    """
    return service.get_all_attendance(session=session, skip=skip, limit=limit)


@router.get("/irregular", response_model=list[IrregularStudentRead])
def read_irregular_students(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return service.list_irregular(session=session)


@router.get("/leave-sync", response_model=list[LeaveSyncRowRead])
def read_leave_sync(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return service.list_leave_sync(session=session)


# ---------------------------------------------------------------------------
# The register the Attendance tab actually draws (Phase 2)
#
# `?date=`, `?from=&to=` are the words the UI already uses; the parameters are
# named `on_date`/`from_date` here because `date` is also a type.
# ---------------------------------------------------------------------------


@router.get("/section/{section_id}", response_model=RegisterRead)
def read_section_register(
    section_id: UUID,
    on_date: date = Query(alias="date"),
    classroom_subject_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """The class-section's roll for one day: everyone, marked or not.

    This is the read the screen was missing - it used to draw a roster from the
    student list and then forget to ask what had been saved. `closed_reason` says when
    the day is a Sunday or a holiday, and a child on approved leave comes back as
    `leave` with the request's id.
    """
    return register_service.register(
        session=session,
        section_id=section_id,
        on_date=on_date,
        classroom_subject_id=classroom_subject_id,
    )


@router.get("/section/{section_id}/summary", response_model=SectionSummaryRead)
def read_section_summary(
    section_id: UUID,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    classroom_subject_id: UUID | None = None,
    until: date | None = Query(default=None),
    month: date | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Per-student present/absent/late days and percentage.

    With no `from`/`to` the server measures the register's own year: the first day this
    section was ever marked up to the **cutoff** - today when the section has a register
    today, yesterday otherwise - so a day still waiting to be marked is never counted as an
    absence. Both dates keep working for callers that ask for a specific range, and a named
    range is measured exactly as asked.

    `month` chooses the month the row's `Monthly attendance 5/12` describes, and `until`
    is the day on screen: it stops the **month** on that day (stepping back one day when
    that day has no register yet). A completed month uses all of its open days.
    """
    return register_service.section_summary(
        session=session,
        section_id=section_id,
        start=from_date,
        end=to_date,
        classroom_subject_id=classroom_subject_id,
        until=until,
        month=month,
    )


@router.get("/section/{section_id}/calendar", response_model=SectionCalendarRead)
def read_section_calendar(
    section_id: UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """The month the register's date control draws: which days are closed and why,
    and which days already have a register saved.

    One answer for the whole month, so the calendar's colours and its saved-days dot come
    from the same read - and from the same calendar the register itself obeys.
    """
    return register_service.section_calendar(
        session=session, section_id=section_id, start=from_date, end=to_date
    )


@router.get("/section/{section_id}/trend", response_model=SectionTrendRead)
def read_section_trend(
    section_id: UUID,
    days: int = Query(default=7, ge=1, le=400),
    end: date | None = Query(default=None),
    on_range: Literal["day", "week", "month"] = Query(default="day", alias="range"),
    limit: int | None = Query(default=None, ge=1, le=60),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """The section's present percentage on the scale the card is showing.

    `range=day` is one point per open day (weekly offs and holidays skipped), `week` is the
    month cut into 1-7 / 8-14 / 15-21 / 22-28 / 29-end, and `month` is one point per
    calendar month. `limit` caps the number of bars (7 / 5 / 6 by default).

    With no `end` the chart ends on the last day the register holds, so it never trails off
    into a stretch of days nobody marked.
    """
    return register_service.section_trend(
        session=session,
        section_id=section_id,
        days=days,
        end=end,
        bucket=on_range,
        limit=limit,
    )


@router.get("/section/{section_id}/late-last-month", response_model=LateStudentsRead)
def read_late_last_month(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Children late more than the school's share of last month's open days."""
    return register_service.late_students_last_month(
        session=session, section_id=section_id
    )


@router.get("/section/{section_id}/attention", response_model=list[AttentionRowRead])
def read_section_attention(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Children below the school's threshold, or absent too many open days in a row."""
    return register_service.section_attention(session=session, section_id=section_id)


@router.get("/closed-days", response_model=list[ClosedDayRead])
def read_closed_days(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Sundays and holidays in a range - what the register's date picker greys out.

    The reason is the words the screen prints ("Sunday", "Diwali break"), so the
    calendar and the toolbar cannot explain the same closed day differently.
    """
    return register_service.closed_days(session=session, start=from_date, end=to_date)


@router.get("/closure-impact", response_model=ClosureImpactRead)
def read_closure_impact(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    days: list[int] | None = Query(default=None),
    nth: list[str] | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """What a closure of this window would throw away - by class-section, by name.

    With `days`/`nth` the read answers for a **proposed** weekly-off setting instead of the
    stored calendar. That answer is always empty: a rule never takes back a day that already
    has a register, so a weekly-off save deletes nothing. Reading never deletes anything.
    """
    if days is not None or nth is not None:
        return register_service.weekly_off_impact(
            session=session,
            start=from_date,
            end=to_date,
            days=days or [],
            nth=nth or [],
        )
    return register_service.closure_impact(
        session=session, start=from_date, end=to_date
    )


@router.post("/closure-impact/delete", response_model=ClosureDeleteRead)
def remove_closure_records(
    payload: ClosureDeleteWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Delete the register rows of the days being closed - **explicit confirm only**.

    `holiday.manage` (the office), not `attendance.mark`: a teacher may take a register, but
    only the office may throw one away.
    """
    return register_service.delete_closure_records(session=session, payload=payload)


# ---------------------------------------------------------------------------
# The school's calendar (Phase 3.5)
#
# Reading **and** writing is `holiday.manage` - the principal and every role above,
# never the deputy or a teacher. The calendar is a school-wide decision (it moves every
# class's percentages), so the page is not printed on the register screen either. The
# register keeps its own reads (`/closed-days`, the section calendar), which stay
# `attendance.read`; only this calendar is the office's.
# ---------------------------------------------------------------------------


@router.get("/holidays", response_model=HolidayCalendarRead)
def read_holiday_calendar(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Holidays, the dated weekly offs, the weekly-off rules, the marked days and the dates
    reopened on purpose.

    The holidays come back without the weekly offs: a weekly off closes a day but is not
    a holiday, so the list under the calendar shows only the holidays and the extra
    weekly offs arrive in their own list (`week_offs`) with ids, so a mistaken date can be
    deleted.
    """
    return holiday_service.list_calendar(session=session, start=from_date, end=to_date)


@router.post(
    "/holidays",
    response_model=HolidayImpact,
    status_code=status.HTTP_201_CREATED,
)
def add_holiday(
    payload: HolidayWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Add a holiday or a range; `409` when it overlaps one that already exists."""
    return holiday_service.create_holiday(
        session=session, payload=payload, user=current_user
    )


@router.patch("/holidays/{holiday_id}", response_model=HolidayImpact)
def edit_holiday(
    holiday_id: UUID,
    payload: HolidayWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Edit one holiday (same overlap rule); `404` for an unknown id."""
    return holiday_service.update_holiday(
        session=session, holiday_id=holiday_id, payload=payload
    )


@router.delete("/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_holiday(
    holiday_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Remove the holiday - the day reopens; the register rows were never touched."""
    holiday_service.delete_holiday(session=session, holiday_id=holiday_id)


@router.get("/weekly-off", response_model=WeeklyOffRead)
def read_weekly_off(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """The weekdays the school is regularly closed (`date.weekday()` order), plus the
    `"5#1"` rules for "the 1st, 2nd, 3rd or 4th Saturday"."""
    return WeeklyOffRead(
        days=holiday_service.weekly_off(session=session),
        nth=holiday_service.nth_off(session=session),
    )


@router.put("/weekly-off", response_model=WeeklyOffRead)
def write_weekly_off(
    payload: WeeklyOffWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Set the weekly offs - one setting for every week, never a row per Sunday.

    `days` are whole weekdays; `nth` is the Saturday-style rule (`"5#1"`). A payload that
    leaves `nth` out keeps the rules the school already had.

    Saving never deletes a register: a day that already has one is skipped by the rule
    (`calendar.closures`), so the marks stay and stay counted. Nothing to confirm.
    """
    days = holiday_service.set_weekly_off(
        session=session, days=payload.days, nth=payload.nth
    )
    return WeeklyOffRead(days=days, nth=holiday_service.nth_off(session=session))


@router.post(
    "/open-days",
    response_model=OpenDayRead,
    status_code=status.HTTP_201_CREATED,
)
def add_open_day(
    payload: OpenDayWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Reopen **one** date a weekly off (or a holiday) closes - "just this day".

    The weekly-off setting is untouched: every other Sunday stays closed, and a register can
    be saved on this one date. `409` when the day is already open, or already reopened.
    """
    return holiday_service.mark_open_day(
        session=session, payload=payload, user=current_user
    )


@router.delete("/open-days/{on_date}", status_code=status.HTTP_204_NO_CONTENT)
def remove_open_day(
    on_date: date,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("holiday.manage")),
):
    """Close the date again - the rule (or the holiday) takes over as it did before."""
    holiday_service.clear_open_day(session=session, day=on_date)
