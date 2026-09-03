from fastapi import HTTPException
from sqlmodel import Session

from app.domains.users import repository as user_repository

from . import repository
from .models import StudentProfile
from .schemas import StudentCreate


def get_student(session: Session, student_id: int) -> StudentProfile:
    student = repository.get_student_by_id(session, student_id=student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def get_students(
    session: Session, skip: int = 0, limit: int = 100
) -> list[StudentProfile]:
    return repository.get_students(session, skip=skip, limit=limit)


def create_student(session: Session, student_in: StudentCreate) -> StudentProfile:
    # Validate user exists
    user = user_repository.get_user_by_id(session, user_id=student_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if student already exists for this user
    existing_student = repository.get_student_by_user_id(
        session, user_id=student_in.user_id
    )
    if existing_student:
        raise HTTPException(
            status_code=400, detail="Student profile already exists for this user"
        )

    return repository.create_student(session, student_in=student_in)
