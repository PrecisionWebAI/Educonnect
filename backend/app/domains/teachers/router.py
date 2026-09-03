from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import TeacherCreate, TeacherRead

router = APIRouter()

# Admin, Principal, or Director might manage teachers
AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)


@router.get("", response_model=list[TeacherRead])
def read_teachers(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    """
    List all teachers. Anyone authenticated can typically view the staff directory.
    """
    return service.get_teachers(session=session, skip=skip, limit=limit)


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    teacher_in: TeacherCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Create a teacher profile. Admin/Principal/Director only.
    """
    return service.create_teacher(session=session, teacher_in=teacher_in)


@router.get("/{teacher_id}", response_model=TeacherRead)
def read_teacher(teacher_id: int, session: Session = Depends(get_session)):
    """
    Get a specific teacher profile.
    """
    return service.get_teacher(session=session, teacher_id=teacher_id)
