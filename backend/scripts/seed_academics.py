"""Seed the school's structure: classes and sections.

Why this file exists:
  `GET /academics/class-matrix` and `GET /academics/class-info` aggregate from the
  database, which only shows something useful once the school has classes and
  sections. This script inserts exactly that: **the whole school, Nursery to
  Class 12, ten sections (A-J) per class**.

  It does **not** create students, teachers or staff. Students exist because an
  admission form was registered and staff because the hiring flow registered
  them, so those belong to the product, not to a demo bootstrap.

Idempotent: every block looks for what it is about to insert, so this is safe to
run on each container start (bootstrap.py calls it) and by hand:

    docker exec eduverse-backend python scripts/seed_academics.py
"""

import os
import re
import sys

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
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


# ---------------------------------------------------------------------------
# 1. Classrooms - rename the legacy rows, then make sure the catalog exists
# ---------------------------------------------------------------------------


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
        print(
            f"[seed_academics] renamed {renamed} legacy class row(s) "
            "to the class wording"
        )

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
        print(f"[seed_academics] {created} class(es) created")

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
        print(f"[seed_academics] {created} section(s) created")
    return grouped


# ---------------------------------------------------------------------------
# 2. The school structure - classes and their sections
# ---------------------------------------------------------------------------


def seed_academics() -> None:
    """Insert the school's structure; every block skips what is already there.

    No students, teachers or staff are seeded here: they exist because a real
    admission form / hire was registered, which is what makes them show up in the
    directory.
    """
    with Session(engine) as session:
        classrooms = _sync_classrooms(session)
        grouped = _sync_sections(session, classrooms)
        print(
            "[seed_academics] School structure ready: "
            f"{len(classrooms)} classes, "
            f"{sum(len(sections) for sections in grouped.values())} sections"
        )


if __name__ == "__main__":
    seed_academics()
