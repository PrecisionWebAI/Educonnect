"""The class catalog - an app-level seeder, like the role catalog.

Same shape as the other catalog seeders (`permissions_repository.seed_roles`,
`seed_permissions`): it takes a `Session`, does its inserts, prints what it did and
returns. `app/core/bootstrap.py` is what opens the session.

`classroom` and `section` carry a `school_id`, so the catalog is seeded **per
active school**: every school gets its own 15 classes and 150 sections, and
`app/core/db.py` keeps one school's classes out of another's queries. `role` and
`permission` are the opposite - platform catalogs, seeded once.

The seeder runs on an unbound session (no school), so the tenant listener neither
filters the reads nor stamps the inserts; every `school_id` here is set explicitly.

Idempotent: every step looks for what it is about to insert, so it is safe on
every container start.
"""

import re

from sqlmodel import Session, select

from app.domains.academics.models import Classroom, Section, Subject
from app.domains.schools.models import School

#: (name, level, stage). `level` is the position inside the school (0 = Nursery),
#: not the class number: the pre-primary years have no number and a school may
#: call a year "Std VI". The name is the truth; the level only sorts.
CLASS_CATALOG: tuple[tuple[str, int, str], ...] = (
    ("Nursery", 0, "pre_primary"),
    ("LKG", 1, "pre_primary"),
    ("UKG", 2, "pre_primary"),
    ("Class 1", 3, "primary"),
    ("Class 2", 4, "primary"),
    ("Class 3", 5, "primary"),
    ("Class 4", 6, "primary"),
    ("Class 5", 7, "primary"),
    ("Class 6", 8, "middle"),
    ("Class 7", 9, "middle"),
    ("Class 8", 10, "middle"),
    ("Class 9", 11, "secondary"),
    ("Class 10", 12, "secondary"),
    ("Class 11", 13, "senior_secondary"),
    ("Class 12", 14, "senior_secondary"),
)

#: Every class runs the same ten sections.
SECTION_NAMES: tuple[str, ...] = tuple("ABCDEFGHIJ")

#: Default subjects seeded per active school (tenant-scoped, like `classroom` is
#: shared - but subjects carry a `school_id` so each school can rename/add them).
SUBJECT_CATALOG: tuple[tuple[str, str], ...] = (
    ("Mathematics", "MATH"),
    ("English", "ENG"),
    ("Hindi", "HIN"),
    ("Physics", "PHY"),
    ("Chemistry", "CHEM"),
    ("Biology", "BIO"),
    ("Computer Science", "CS"),
    ("Social Science", "SST"),
    ("History", "HIS"),
    ("Geography", "GEO"),
    ("Physical Education", "PE"),
    ("Art", "ART"),
    ("Music", "MUS"),
)

#: ("Grade 6" -> "Class 6") - rows created before the vocabulary moved.
LEGACY_NAME = re.compile(r"^Grade\s+(\d+)$")


def _sync_classrooms(session: Session, school: School) -> list[Classroom]:
    """One school's copy of the catalogue, in order.

    Legacy "Grade N" rows are renamed first. Every lookup is scoped to the school,
    because each school owns its own "Class 6" - a platform-wide lookup would match
    another school's row and silently leave this one without a class.
    """
    renamed = 0
    for classroom in session.exec(
        select(Classroom).where(Classroom.school_id == school.id)
    ).all():
        match = LEGACY_NAME.match(classroom.name or "")
        if not match:
            continue
        target = f"Class {int(match.group(1))}"
        clash = session.exec(
            select(Classroom).where(
                Classroom.school_id == school.id, Classroom.name == target
            )
        ).first()
        if clash is not None:
            continue
        classroom.name = target
        session.add(classroom)
        renamed += 1
    if renamed:
        session.commit()
        print(f"[academics] {school.name}: renamed {renamed} legacy class row(s)")

    created = 0
    for name, level, stage in CLASS_CATALOG:
        classroom = session.exec(
            select(Classroom).where(
                Classroom.school_id == school.id, Classroom.name == name
            )
        ).first()
        if classroom is None:
            session.add(
                Classroom(name=name, level=level, stage=stage, school_id=school.id)
            )
            created += 1
            continue
        # Keep level/stage truthful even on rows written before they existed.
        if classroom.level != level or classroom.stage != stage:
            classroom.level = level
            classroom.stage = stage
            session.add(classroom)
    session.commit()
    if created:
        print(f"[academics] {school.name}: {created} class(es) created")

    present = {
        classroom.name: classroom
        for classroom in session.exec(
            select(Classroom).where(Classroom.school_id == school.id)
        ).all()
    }
    return [present[name] for name, _, _ in CLASS_CATALOG if name in present]


def _sync_sections(
    session: Session, school: School, classrooms: list[Classroom]
) -> dict[str, list[Section]]:
    """Every class gets A-J; the rows come back grouped by class name."""
    created = 0
    grouped: dict[str, list[Section]] = {}
    for classroom in classrooms:
        by_name = {
            section.name: section
            for section in session.exec(
                select(Section).where(
                    Section.school_id == school.id,
                    Section.classroom_id == classroom.id,
                )
            ).all()
        }
        for section_name in SECTION_NAMES:
            if section_name in by_name:
                continue
            section = Section(
                name=section_name, classroom_id=classroom.id, school_id=school.id
            )
            session.add(section)
            by_name[section_name] = section
            created += 1
        session.commit()
        grouped[classroom.name] = [
            by_name[name] for name in SECTION_NAMES if name in by_name
        ]
    if created:
        print(f"[academics] {school.name}: {created} section(s) created")
    return grouped


def _sync_subjects(session: Session) -> int:
    """Give every active school the default subject list (idempotent)."""
    schools = session.exec(select(School).where(School.is_active == True)).all()
    created = 0
    for school in schools:
        present = {
            subject.name: subject
            for subject in session.exec(
                select(Subject).where(Subject.school_id == school.id)
            ).all()
        }
        for name, code in SUBJECT_CATALOG:
            if name in present:
                continue
            session.add(Subject(name=name, code=code, school_id=school.id))
            created += 1
    session.commit()
    if created:
        print(f"[academics] {created} subject(s) created")
    return created


def seed_academics(session: Session) -> tuple[int, int]:
    """Give every active school its own class catalog. Returns (classes, sections).

    Per school, not once: `classroom` and `section` carry a `school_id`, so two
    schools both have a "Class 6" and neither can see the other's. `subject` works
    the same way and is seeded in the same loop.
    """
    schools = session.exec(select(School).where(School.is_active == True)).all()  # noqa: E712
    total_classes = 0
    total_sections = 0
    for school in schools:
        classrooms = _sync_classrooms(session, school)
        grouped = _sync_sections(session, school, classrooms)
        total_classes += len(classrooms)
        total_sections += sum(len(rows) for rows in grouped.values())
    subjects = _sync_subjects(session)
    print(
        f"[academics] class catalog ready: {total_classes} classes, "
        f"{total_sections} sections, {subjects} subjects "
        f"across {len(schools)} school(s)"
    )
    return (total_classes, total_sections)
