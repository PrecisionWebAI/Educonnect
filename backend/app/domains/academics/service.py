from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import GradeClass, Section
from .schemas import (
    ClassInfoRead,
    ClassMatrixRowRead,
    GradeClassCreate,
    SectionCreate,
)


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


# ---------------------------------------------------------------------------
# Class views - every number below comes from the database
# ---------------------------------------------------------------------------


def get_class_matrix(session: Session) -> list[ClassMatrixRowRead]:
    """One row per (class, section): strength / boys / girls / attendance.

    Replaces the five hardcoded rows this endpoint used to return, so the
    matrix shows what the school actually has.
    """
    students = repository.get_students_per_section(session)
    attendance = repository.get_attendance_per_section(session)

    rows: list[ClassMatrixRowRead] = []
    for grade in repository.get_classes(session):
        sections = repository.get_sections_by_class(session, class_id=grade.id)
        for section in sections:
            strength, boys, girls = students.get(section.id, (0, 0, 0))
            rows.append(
                ClassMatrixRowRead(
                    id=section.id,
                    className=f"{grade.level}{section.name}",
                    strength=strength,
                    boys=boys,
                    girls=girls,
                    avgAttendance=attendance.get(section.id, 0.0),
                )
            )
    return rows


def get_class_info(session: Session) -> list[ClassInfoRead]:
    """Class cards with the real class teacher and the real strength.

    A class that has no sections yet still gets one row (section "-"), so
    students that are not placed anywhere stay visible instead of disappearing.
    """
    teachers = repository.get_class_teachers_by_section(session)
    per_section = repository.get_students_per_section(session)
    per_class = repository.get_students_per_class(session)

    result: list[ClassInfoRead] = []
    for grade in repository.get_classes(session):
        display_name = grade.name.replace("Grade ", "")
        sections = repository.get_sections_by_class(session, class_id=grade.id)
        if not sections:
            result.append(
                ClassInfoRead(
                    id=grade.id,
                    name=display_name,
                    section="-",
                    classTeacher="Staff",
                    strength=per_class.get(grade.id, 0),
                )
            )
            continue
        for section in sections:
            result.append(
                ClassInfoRead(
                    id=section.id,
                    name=display_name,
                    section=section.name,
                    classTeacher=teachers.get(section.id, "Staff"),
                    strength=per_section.get(section.id, (0, 0, 0))[0],
                )
            )
    return result
