from fastapi import HTTPException
from sqlmodel import Session

from app.domains.users import repository as user_repository

from . import repository
from .models import TeacherProfile
from .schemas import TeacherCreate


def get_teacher(session: Session, teacher_id: int) -> TeacherProfile:
    teacher = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


def get_teachers(
    session: Session, skip: int = 0, limit: int = 100
) -> list[TeacherProfile]:
    return repository.get_teachers(session, skip=skip, limit=limit)


def create_teacher(session: Session, teacher_in: TeacherCreate) -> TeacherProfile:
    # Validate user exists
    user = user_repository.get_user_by_id(session, user_id=teacher_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if teacher profile already exists for this user
    existing_teacher = repository.get_teacher_by_user_id(
        session, user_id=teacher_in.user_id
    )
    if existing_teacher:
        raise HTTPException(
            status_code=400, detail="Teacher profile already exists for this user"
        )

    return repository.create_teacher(session, teacher_in=teacher_in)
