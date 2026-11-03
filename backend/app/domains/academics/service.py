from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import Subject
from .schemas import (
    CatalogClassRead,
    CatalogSectionRead,
    ClassCatalogRead,
    ClassInfoRead,
    ClassroomCreate,
    ClassroomRead,
    SectionCreate,
    SectionRead,
)

#: School stages in the order a school grows. The stored truth is
#: `classname.stage`; this only decides the order the chips are drawn in.
STAGE_ORDER = ("pre_primary", "primary", "middle", "secondary", "senior_secondary")


def get_classes(
    session: Session, skip: int = 0, limit: int = 100
) -> list[ClassroomRead]:
    """The platform's class list, in the shape the dropdowns already read.

    The classes are a **platform** catalog now (`classname`), so `id` is the
    catalog's `class_id` and `name` is its wording ("Class 6") - the two fields a
    client has always used, whichever table they come from.
    """
    return [
        ClassroomRead(
            id=row.class_id, name=row.classname, level=row.level, stage=row.stage
        )
        for row in repository.get_classes(session, skip=skip, limit=limit)
    ]


def create_class(session: Session, class_in: ClassroomCreate) -> ClassroomRead:
    # We could add a check if class name already exists
    row = repository.create_class(session, class_in=class_in)
    return ClassroomRead(
        id=row.class_id, name=row.classname, level=row.level, stage=row.stage
    )


def get_sections_by_class(session: Session, class_id: UUID) -> list[SectionRead]:
    """The class-sections this school runs for one class ("Class 6-A" …)."""
    if not repository.get_class_by_id(session, class_id=class_id):
        raise HTTPException(status_code=404, detail="Class not found")
    return [
        SectionRead(id=row.id, section_name=row.section_name)
        for row in repository.get_sections_by_class(session, class_id=class_id)
    ]


def get_subjects(session: Session) -> list[Subject]:
    """The school's subject vocabulary (for dropdowns like interview scheduling)."""
    return repository.get_subjects(session)


def create_section(
    session: Session, class_id: UUID, section_in: SectionCreate
) -> SectionRead:
    """Say that this school runs a class-section: the `classroom` row for the pair.

    The letters themselves are a platform catalog (A-J), so "creating a section"
    is creating the school's class-section row - exactly what a registration does.
    """
    if section_in.classroom_id != class_id:
        raise HTTPException(status_code=400, detail="Class ID mismatch")
    if not repository.get_class_by_id(session, class_id=class_id):
        raise HTTPException(status_code=404, detail="Class not found")
    section = repository.find_section(session, section_in.section_name)
    if section is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{section_in.section_name}' is not one of the platform's sections",
        )
    room = repository.ensure_room(session, class_id, section.section_id)
    return SectionRead(id=room.id, section_name=section.section_name)


# ---------------------------------------------------------------------------
# Class views - every number below comes from the database
# ---------------------------------------------------------------------------


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
        sections = repository.get_sections_by_class(session, class_id=classroom.class_id)
        if not sections:
            result.append(
                ClassInfoRead(
                    id=classroom.class_id,
                    name=classroom.classname,
                    section="-",
                    classTeacher="Staff",
                    strength=per_class.get(classroom.class_id, 0),
                )
            )
            continue
        for section in sections:
            result.append(
                ClassInfoRead(
                    id=section.id,
                    name=classroom.classname,
                    section=section.section_name,
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

    # The sections are a **platform** list now (A … J), so every class offers the
    # same ten letters - a dropdown can show them before the school has ever used
    # that class-section.
    all_sections = repository.get_all_sections(session)

    for classroom in repository.get_classes(session):
        classes.append(
            CatalogClassRead(
                id=classroom.class_id,
                name=classroom.classname,
                level=classroom.level,
                stage=classroom.stage,
                sections=[
                    CatalogSectionRead(
                        id=section.section_id,
                        name=section.section_name,
                        classroomId=classroom.class_id,
                    )
                    for section in all_sections
                ],
            )
        )
        for section in all_sections:
            if section.section_name not in section_names:
                section_names.append(section.section_name)
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
    return ClassCatalogRead(classes=classes, sectionNames=section_names, stages=stages)
