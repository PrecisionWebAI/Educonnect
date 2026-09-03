from sqlmodel import Session, select

from .models import StudentProfile
from .schemas import StudentCreate


def get_student_by_id(session: Session, student_id: int) -> StudentProfile | None:
    return session.get(StudentProfile, student_id)


def get_student_by_user_id(session: Session, user_id: int) -> StudentProfile | None:
    statement = select(StudentProfile).where(StudentProfile.user_id == user_id)
    return session.exec(statement).first()


def get_students(
    session: Session, skip: int = 0, limit: int = 100
) -> list[StudentProfile]:
    return list(session.exec(select(StudentProfile).offset(skip).limit(limit)).all())


def create_student(session: Session, student_in: StudentCreate) -> StudentProfile:
    db_student = StudentProfile.model_validate(student_in)
    session.add(db_student)
    session.commit()
    session.refresh(db_student)
    return db_student
