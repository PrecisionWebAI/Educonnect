"""The class catalog - an app-level seeder, like the role catalog.

Same shape as the other catalog seeders (`permissions_repository.seed_roles`,
`seed_permissions`): it takes a `Session`, does its inserts, prints what it did and
returns. `app/core/bootstrap.py` is what opens the session.

`classroom` (15 rows) and `section` (150 rows) are **shared** across schools - one
set for the whole platform, exactly like `role` and `permission` - so this seeds
once and never grows with the number of schools. A school's boundary lives on the
*data* rows (students, attendance, timetable), which carry their own `school_id`.

Idempotent: every step looks for what it is about to insert, so it is safe on
every container start.
"""

import re

from sqlmodel import Session, select

from app.domains.academics.models import Classroom, Section

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

#: ("Grade 6" -> "Class 6") - rows created before the vocabulary moved.
LEGACY_NAME = re.compile(r"^Grade\s+(\d+)$")


def _sync_classrooms(session: Session) -> list[Classroom]:
    """The whole catalogue, in order. Legacy "Grade N" rows are renamed first."""
    renamed = 0
    for classroom in session.exec(select(Classroom)).all():
        match = LEGACY_NAME.match(classroom.name or "")
        if not match:
            continue
        target = f"Class {int(match.group(1))}"
        clash = session.exec(select(Classroom).where(Classroom.name == target)).first()
        if clash is not None:
            continue
        classroom.name = target
        session.add(classroom)
        renamed += 1
    if renamed:
        session.commit()
        print(f"[academics] renamed {renamed} legacy class row(s)")

    created = 0
    for name, level, stage in CLASS_CATALOG:
        classroom = session.exec(
            select(Classroom).where(Classroom.name == name)
        ).first()
        if classroom is None:
            session.add(Classroom(name=name, level=level, stage=stage))
            created += 1
            continue
        # Keep level/stage truthful even on rows written before they existed.
        if classroom.level != level or classroom.stage != stage:
            classroom.level = level
            classroom.stage = stage
            session.add(classroom)
    session.commit()
    if created:
        print(f"[academics] {created} class(es) created")

    present = {c.name: c for c in session.exec(select(Classroom)).all()}
    return [present[name] for name, _, _ in CLASS_CATALOG if name in present]


def _sync_sections(
    session: Session, classrooms: list[Classroom]
) -> dict[str, list[Section]]:
    """Every class gets A-J; the rows come back grouped by class name."""
    created = 0
    grouped: dict[str, list[Section]] = {}
    for classroom in classrooms:
        by_name = {
            section.name: section
            for section in session.exec(
                select(Section).where(Section.classroom_id == classroom.id)
            ).all()
        }
        for section_name in SECTION_NAMES:
            if section_name in by_name:
                continue
            section = Section(name=section_name, classroom_id=classroom.id)
            session.add(section)
            by_name[section_name] = section
            created += 1
        session.commit()
        grouped[classroom.name] = [
            by_name[name] for name in SECTION_NAMES if name in by_name
        ]
    if created:
        print(f"[academics] {created} section(s) created")
    return grouped


def seed_academics(session: Session) -> tuple[int, int]:
    """Create the one global class catalog. Returns (classes, sections).

    Seeded **once**, not per school: `classroom` and `section` are shared catalog
    rows (like `role`), so there are always 15 classes and 150 sections regardless
    of how many schools register.
    """
    classrooms = _sync_classrooms(session)
    grouped = _sync_sections(session, classrooms)
    sections = sum(len(rows) for rows in grouped.values())
    print(
        f"[academics] class catalog ready: {len(classrooms)} classes, "
        f"{sections} sections"
    )
    return (len(classrooms), sections)
