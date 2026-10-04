from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import Classroom, Section
from .schemas import (
    CatalogClassRead,
    CatalogSectionRead,
    ClassCatalogRead,
    ClassInfoRead,
    ClassMatrixRowRead,
    ClassroomCreate,
    SectionCreate,
)

#: School stages in the order a school grows. The stored truth is
#: `classroom.stage`; this only decides the order the chips are drawn in.
STAGE_ORDER = ("pre_primary", "primary", "middle", "secondary", "senior_secondary")


def get_classes(session: Session, skip: int = 0, limit: int = 100) -> list[Classroom]:
    return repository.get_classes(session, skip=skip, limit=limit)


def create_class(session: Session, class_in: ClassroomCreate) -> Classroom:
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
    if section_in.classroom_id != class_id:
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
    for classroom in repository.get_classes(session):
        sections = repository.get_sections_by_class(session, class_id=classroom.id)
        for section in sections:
            strength, boys, girls = students.get(section.id, (0, 0, 0))
            rows.append(
                ClassMatrixRowRead(
                    id=section.id,
                    # "Class 6-A": the stored class name, so the screen never
                    # re-derives a label from the level number.
                    className=f"{classroom.name}-{section.name}",
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
    for classroom in repository.get_classes(session):
        sections = repository.get_sections_by_class(session, class_id=classroom.id)
        if not sections:
            result.append(
                ClassInfoRead(
                    id=classroom.id,
                    name=classroom.name,
                    section="-",
                    classTeacher="Staff",
                    strength=per_class.get(classroom.id, 0),
                )
            )
            continue
        for section in sections:
            result.append(
                ClassInfoRead(
                    id=section.id,
                    name=classroom.name,
                    section=section.name,
                    classTeacher=teachers.get(section.id, "Staff"),
                    strength=per_section.get(section.id, (0, 0, 0))[0],
                )
            )
    return result


def get_catalog(session: Session) -> ClassCatalogRead:
    """The class vocabulary in one payload: classes with their sections.

    Everything a screen needs to render a class list, a section list or a stage
    chip comes from here, so no client keeps its own copy of the school's
    vocabulary and a class added to the database appears everywhere at once.
    """
    classes: list[CatalogClassRead] = []
    section_names: list[str] = []
    stages: list[str] = []

    for classroom in repository.get_classes(session):
        sections = repository.get_sections_by_class(session, class_id=classroom.id)
        classes.append(
            CatalogClassRead(
                id=classroom.id,
                name=classroom.name,
                level=classroom.level,
                stage=classroom.stage,
                sections=[
                    CatalogSectionRead(
                        id=section.id,
                        name=section.name,
                        classroomId=section.classroom_id,
                    )
                    for section in sections
                ],
            )
        )
        for section in sections:
            if section.name not in section_names:
                section_names.append(section.name)
        if classroom.stage not in stages:
            stages.append(classroom.stage)

    # A school grows pre-primary -> senior secondary; unknown stages sort last.
    stages.sort(
        key=lambda stage: (
            STAGE_ORDER.index(stage) if stage in STAGE_ORDER else len(STAGE_ORDER),
            stage,
        )
    )
    section_names.sort()
    return ClassCatalogRead(
        classes=classes, sectionNames=section_names, stages=stages
    )
