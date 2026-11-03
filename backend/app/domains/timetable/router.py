from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import TimetablePeriodCreate, TimetablePeriodRead, TimetableSlotRead

router = APIRouter()

# Removed RoleCheckers


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
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """
    Fetch the weekly schedule for a class.
    """
    return service.get_timetable_by_class(
        session=session, class_id=class_id, section_id=section_id
    )


@router.get("/teacher/{teacher_id}", response_model=list[TimetablePeriodRead])
def read_timetable_by_teacher(
    teacher_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    """
    Fetch the weekly schedule for a teacher.
    """
    return service.get_timetable_by_teacher(session=session, teacher_id=teacher_id)


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
    return service.update_period(session=session, period_id=period_id, period_in=period_in)


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
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    return service.list_slots(session=session)
