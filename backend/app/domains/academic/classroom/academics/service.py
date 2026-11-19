import re
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
    SubjectCreate,
    SubjectUpdate,
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


#: A subject's name/code are short identifiers the office types, not prose.
SUBJECT_NAME_MAX = 120
SUBJECT_CODE_MAX = 20
SUBJECT_NAME_MIN = 1


def get_subjects(session: Session, include_inactive: bool = False) -> list[Subject]:
    """The school's subject vocabulary (dropdowns, and the Course master list)."""
    return repository.get_subjects(session, include_inactive=include_inactive)


def _clean_subject_name(value: str) -> str:
    """The stored name: single-spaced, lower-case (the same rule as every stored name)."""
    name = " ".join((value or "").split()).lower()
    if len(name) < SUBJECT_NAME_MIN:
        raise HTTPException(status_code=422, detail="A subject needs a name.")
    if len(name) > SUBJECT_NAME_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"A subject name cannot be longer than {SUBJECT_NAME_MAX} characters.",
        )
    return name


def _clean_subject_code(value: str) -> str:
    code = (value or "").strip().upper()
    if not code:
        raise HTTPException(status_code=422, detail="A subject code cannot be blank.")
    if len(code) > SUBJECT_CODE_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"A subject code cannot be longer than {SUBJECT_CODE_MAX} characters.",
        )
    return code


def _initials(name: str) -> str:
    """`english 1` -> `E1`, `social science` -> `SS` - the start of a generated code."""
    words = [word for word in re.split(r"[^A-Za-z0-9]+", name) if word]
    letters = "".join(word[0] for word in words[:4]).upper()
    return letters or "SUB"


def _next_subject_code(session: Session, name: str) -> str:
    """A code this school does not use yet (`ENG`, `ENG2`, …), never a duplicate."""
    base = _initials(name)
    used = repository.subject_codes(session)
    candidate = base
    number = 2
    while candidate in used:
        suffix = str(number)
        candidate = f"{base[: max(1, SUBJECT_CODE_MAX - len(suffix))]}{suffix}"
        number += 1
    return candidate


def create_subject(session: Session, subject_in: SubjectCreate) -> Subject:
    """Add a subject to the school's list. The name is the key people type; the code is
    an identifier, generated when the office does not care to choose one."""
    name = _clean_subject_name(subject_in.name)
    existing = repository.find_subject_by_name(session, name)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"This school already lists a subject named '{existing.name}'.",
        )

    code = (
        _clean_subject_code(subject_in.code)
        if subject_in.code
        else _next_subject_code(session, name)
    )
    if code in repository.subject_codes(session):
        raise HTTPException(
            status_code=409, detail=f"Subject code '{code}' is already in use."
        )

    subject = Subject(name=name, code=code)
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def update_subject(
    session: Session, subject_id: UUID, subject_in: SubjectUpdate
) -> Subject:
    """Rename or retire a subject. Retiring never deletes the rows that point at it."""
    subject = repository.get_subject(session, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    if subject_in.name is None and subject_in.is_active is None:
        raise HTTPException(
            status_code=422, detail="Send a new name or a new active state."
        )

    if subject_in.name is not None:
        name = _clean_subject_name(subject_in.name)
        duplicate = repository.find_subject_by_name(session, name)
        if duplicate is not None and duplicate.id != subject.id:
            raise HTTPException(
                status_code=409,
                detail=f"This school already lists a subject named '{duplicate.name}'.",
            )
        subject.name = name

    if subject_in.is_active is not None:
        subject.is_active = subject_in.is_active

    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


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
        sections = repository.get_sections_by_class(
            session, class_id=classroom.class_id
        )
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
