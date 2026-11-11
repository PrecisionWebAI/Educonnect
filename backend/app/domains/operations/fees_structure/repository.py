from uuid import UUID

from sqlmodel import Session, func, select

from app.domains.academic.classroom.academics.models import ClassName, Classroom
from app.domains.academic.classroom.academics.repository import find_classroom
from app.domains.academic.classroom.students.models import Student

from .models import FeeStructure
from .schemas import FeeStructureCreate


def get_fee_structures(
    session: Session, skip: int = 0, limit: int = 100
) -> list[FeeStructure]:
    return list(session.exec(select(FeeStructure).offset(skip).limit(limit)).all())


def get_fee_structures_by_class(session: Session, class_id: UUID) -> list[FeeStructure]:
    statement = select(FeeStructure).where(FeeStructure.class_id == class_id)
    return list(session.exec(statement).all())


def create_fee_structure(
    session: Session, structure_in: FeeStructureCreate
) -> FeeStructure:
    db_structure = FeeStructure.model_validate(structure_in)
    session.add(db_structure)
    session.commit()
    session.refresh(db_structure)
    return db_structure


def get_fee_structure(session: Session, structure_id: UUID) -> FeeStructure | None:
    return session.get(FeeStructure, structure_id)


def save_fee_structure(session: Session, structure: FeeStructure) -> FeeStructure:
    session.add(structure)
    session.commit()
    session.refresh(structure)
    return structure


def get_classroom(session: Session, class_name: str) -> ClassName | None:
    """Resolve a class the UI sent ("Class 6", "Grade 6", "6") to `classname`.

    One implementation, in the academics domain that owns the vocabulary, so the
    fee card and the admission form resolve a class the same way.
    """
    return find_classroom(session, class_name)


def get_classroom_names(session: Session) -> dict[UUID, str]:
    """{class_id: class name} - one query for the whole fee list."""
    return {
        classroom.class_id: classroom.classname
        for classroom in session.exec(select(ClassName)).all()
        if classroom.class_id is not None
    }


def count_students_by_class(session: Session) -> dict[UUID, int]:
    """{class_id: students} - powers the "Students" column.

    The class is read through the student's class-section, so there is no class id
    stored on the student row to drift out of step. `select_from` is spelled out
    because the selected column belongs to the *joined* table - without it
    SQLAlchemy would take `classroom` as the FROM and join it to itself.
    """
    rows = session.exec(
        select(Classroom.class_id, func.count())
        .select_from(Student)
        .join(Classroom, Classroom.id == Student.classroom_id)
        .group_by(Classroom.class_id)
    ).all()
    return {
        classroom_id: int(count) for classroom_id, count in rows if classroom_id is not None
    }
