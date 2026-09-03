from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import GradeClass, Section
from .schemas import GradeClassCreate, SectionCreate


def get_classes(session: Session, skip: int = 0, limit: int = 100) -> list[GradeClass]:
    return repository.get_classes(session, skip=skip, limit=limit)


def create_class(session: Session, class_in: GradeClassCreate) -> GradeClass:
    # We could add a check if class name already exists
    return repository.create_class(session, class_in=class_in)


def get_sections_by_class(session: Session, class_id: int) -> list[Section]:
    # Check if class exists
    db_class = repository.get_class_by_id(session, class_id=class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    return repository.get_sections_by_class(session, class_id=class_id)


def create_section(
    session: Session, class_id: int, section_in: SectionCreate
) -> Section:
    if section_in.grade_class_id != class_id:
        raise HTTPException(status_code=400, detail="Class ID mismatch")
    db_class = repository.get_class_by_id(session, class_id=class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    return repository.create_section(session, section_in=section_in)
