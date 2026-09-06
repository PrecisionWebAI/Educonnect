from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import TimetablePeriodCreate, TimetablePeriodRead, TimetableSlotRead

router = APIRouter()

AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)


@router.post(
    "", response_model=TimetablePeriodRead, status_code=status.HTTP_201_CREATED
)
def create_period(
    period_in: TimetablePeriodCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Admin/Principal adds a period to the schedule.
    """
    return service.create_period(session=session, period_in=period_in)


@router.get("/class/{class_id}", response_model=list[TimetablePeriodRead])
def read_timetable_by_class(
    class_id: int,
    section_id: int | None = None,
    session: Session = Depends(get_session),
):
    """
    Fetch the weekly schedule for a class.
    """
    return service.get_timetable_by_class(
        session=session, class_id=class_id, section_id=section_id
    )


@router.get("/teacher/{teacher_id}", response_model=list[TimetablePeriodRead])
def read_timetable_by_teacher(
    teacher_id: int,
    session: Session = Depends(get_session),
    # Could protect this if needed
):
    """
    Fetch the weekly schedule for a teacher.
    """
    return service.get_timetable_by_teacher(session=session, teacher_id=teacher_id)


@router.get("", response_model=list[TimetableSlotRead])
def read_timetable(session: Session = Depends(get_session)):
    return [
        TimetableSlotRead(
            day="Mon",
            period="P1",
            className="10-A",
            subject="Mathematics",
            teacher="M. Iyer",
        ),
        TimetableSlotRead(
            day="Mon",
            period="P2",
            className="10-A",
            subject="Physics",
            teacher="P. Menon",
        ),
        TimetableSlotRead(
            day="Tue",
            period="P1",
            className="10-A",
            subject="Chemistry",
            teacher="R. Khanna",
        ),
        TimetableSlotRead(
            day="Wed",
            period="P3",
            className="10-A",
            subject="English",
            teacher="S. Das",
        ),
    ]
