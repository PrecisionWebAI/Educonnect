from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.admin.settings import calendar as school_calendar
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    BellScheduleWrite,
    BellSlotRead,
    WeekOffRead,
    TimetablePeriodCreate,
    TimetablePeriodRead,
    TimetableSlotRead,
)

router = APIRouter()

# Removed RoleCheckers


@router.get("/bell-schedule", response_model=list[BellSlotRead])
def read_bell_schedule(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """The school's day: periods and breaks, seeded on the first read.

    The grid draws these rows instead of a hardcoded six-period array, so a school with
    eight periods or a long lunch break is described by its own data.
    """
    return service.bell_schedule(session)


@router.put("/bell-schedule", response_model=list[BellSlotRead])
def write_bell_schedule(
    payload: BellScheduleWrite,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.create")),
):
    """Set the day's shape: how many periods, and which breaks fall after which."""
    return service.set_bell_schedule(session, payload)


@router.get("/week-off", response_model=WeekOffRead)
def read_week_off(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """The school's weekly offs, so the grid can block those days.

    Read here (not from the attendance screen) because it needs `timetable.read`,
    not `holiday.manage`.
    """
    return WeekOffRead(
        days=sorted(school_calendar.weekly_off_days(session)),
        nth=school_calendar.nth_off_list(session),
    )


@router.post(
    "", response_model=TimetablePeriodRead, status_code=status.HTTP_201_CREATED
)
def create_period(
    period_in: TimetablePeriodCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.create")),
):
    """
    Admin/Principal adds a period to the schedule.
    """
    return service.create_period(session=session, period_in=period_in)


@router.get("/class/{class_id}", response_model=list[TimetablePeriodRead])
def read_timetable_by_class(
    class_id: UUID,
    section_id: UUID | None = None,
    academic_year_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """Fetch the weekly schedule for a class (current year by default)."""
    return service.get_timetable_by_class(
        session=session,
        class_id=class_id,
        section_id=section_id,
        academic_year_id=academic_year_id,
    )


@router.get("/teacher/{teacher_id}", response_model=list[TimetablePeriodRead])
def read_timetable_by_teacher(
    teacher_id: UUID,
    academic_year_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """Fetch the weekly schedule for a teacher (current year by default)."""
    return service.get_timetable_by_teacher(
        session=session, teacher_id=teacher_id, academic_year_id=academic_year_id
    )


@router.patch("/{period_id}", response_model=TimetablePeriodRead)
def update_period(
    period_id: UUID,
    period_in: TimetablePeriodCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.update")),
):
    """Move a period to another slot, subject, teacher or room.

    The class-section grid sends the whole slot, so the body is the same shape as
    the create body.
    """
    return service.update_period(
        session=session, period_id=period_id, period_in=period_in
    )


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    period_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.delete")),
):
    """Clear a slot from the week."""
    service.delete_period(session=session, period_id=period_id)


@router.get("", response_model=list[TimetableSlotRead])
def read_timetable(
    academic_year_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    return service.list_slots(session=session, academic_year_id=academic_year_id)
