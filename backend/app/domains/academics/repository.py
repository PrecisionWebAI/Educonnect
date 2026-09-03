from sqlmodel import Session, select

from .models import GradeClass, Section
from .schemas import GradeClassCreate, SectionCreate


def get_classes(session: Session, skip: int = 0, limit: int = 100) -> list[GradeClass]:
    return list(session.exec(select(GradeClass).offset(skip).limit(limit)).all())


def get_class_by_id(session: Session, class_id: int) -> GradeClass | None:
    return session.get(GradeClass, class_id)


def create_class(session: Session, class_in: GradeClassCreate) -> GradeClass:
    db_class = GradeClass.model_validate(class_in)
    session.add(db_class)
    session.commit()
    session.refresh(db_class)
    return db_class


def get_sections_by_class(session: Session, class_id: int) -> list[Section]:
    statement = select(Section).where(Section.grade_class_id == class_id)
    return list(session.exec(statement).all())


def create_section(session: Session, section_in: SectionCreate) -> Section:
    db_section = Section.model_validate(section_in)
    session.add(db_section)
    session.commit()
    session.refresh(db_section)
    return db_section
