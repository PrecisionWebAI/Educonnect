from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import StudentCreate, StudentRead

router = APIRouter()

# Admin, Principal, or Teachers might manage students
StaffRoles = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director, RoleEnum.teacher]
)


@router.get("", response_model=list[StudentRead])
def read_students(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    List all students. Staff only.
    """
    return service.get_students(session=session, skip=skip, limit=limit)


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RoleChecker([RoleEnum.admin, RoleEnum.principal])),
):
    """
    Create a student profile. Admin/Principal only.
    """
    return service.create_student(session=session, student_in=student_in)


@router.get("/{student_id}", response_model=StudentRead)
def read_student(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Get a specific student profile.
    """
    return service.get_student(session=session, student_id=student_id)
