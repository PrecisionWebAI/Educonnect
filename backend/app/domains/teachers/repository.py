from sqlmodel import Session, select

from .models import TeacherProfile
from .schemas import TeacherCreate


def get_teacher_by_id(session: Session, teacher_id: int) -> TeacherProfile | None:
    return session.get(TeacherProfile, teacher_id)


def get_teacher_by_user_id(session: Session, user_id: int) -> TeacherProfile | None:
    statement = select(TeacherProfile).where(TeacherProfile.user_id == user_id)
    return session.exec(statement).first()


def get_teachers(
    session: Session, skip: int = 0, limit: int = 100
) -> list[TeacherProfile]:
    return list(session.exec(select(TeacherProfile).offset(skip).limit(limit)).all())


def create_teacher(session: Session, teacher_in: TeacherCreate) -> TeacherProfile:
    db_teacher = TeacherProfile.model_validate(teacher_in)
    session.add(db_teacher)
    session.commit()
    session.refresh(db_teacher)
    return db_teacher
