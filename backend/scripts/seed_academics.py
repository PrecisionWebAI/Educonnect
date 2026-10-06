"""Seed the school's structure: classes, sections, subjects and teachers.

Why this file exists:
  `GET /academics/class-matrix` and `GET /academics/class-info` aggregate from the
  database, which only shows something useful once the school has classes and
  sections. This script inserts exactly that: **the whole school, Nursery to
  Class 12, ten sections (A-J) per class**, plus the teaching staff and one class
  teacher per section A.

  It does **not** create students. A student exists because an admission form was
  registered (see `seed_admissions.py` and `admissions/service.py`), so the
  student directory and the admission register can never disagree.

Idempotent: every block looks for what it is about to insert, so this is safe to
run on each container start (bootstrap.py calls it) and by hand:

    docker exec eduverse-backend python scripts/seed_academics.py
"""

import os
import re
import sys
from datetime import date, timedelta

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.academics.models import Classroom, Section
from app.domains.auth.roles import set_user_roles
from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile
from app.domains.users.models import User

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

#: The password new staff logins are created with.
DEMO_PASSWORD = "student123"

DEMO_TEACHERS: tuple[tuple[str, str, str], ...] = (
    ("Meera Iyer", "Mathematics", "M.Sc. Mathematics"),
    ("Arjun Nair", "Science", "M.Sc. Physics"),
    ("Kavita Sharma", "English", "M.A. English"),
    ("Rahul Verma", "Social Studies", "M.A. History"),
    ("Sunita Rao", "Languages", "M.A. Hindi"),
    ("Imran Qureshi", "Computer Science", "MCA"),
    ("Leela Menon", "Science", "M.Sc. Biology"),
    ("Sanjay Kapoor", "Science", "M.Sc. Chemistry"),
    ("Farida Sheikh", "Arts", "M.F.A."),
    ("Nisha Gupte", "Sports", "B.P.Ed."),
)


def _ensure_user(
    session: Session, email: str, full_name: str, hashed: str, roles: list[str]
) -> User:
    """A login, created once; the roles are only set on first sight."""
    user = session.exec(select(User).where(User.email == email)).first()
    if user is not None:
        return user
    user = User(
        email=email, full_name=full_name, hashed_password=hashed, is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    set_user_roles(session, user, roles)
    return user


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
# 2. Teaching staff - profiles plus one class teacher per class
# ---------------------------------------------------------------------------


def _sync_teachers(session: Session) -> list[TeacherProfile]:
    """One login + profile per demo teacher; the ones already there are reused."""
    hashed = get_password_hash(DEMO_PASSWORD)
    profiles: list[TeacherProfile] = []
    created = 0
    for name, department, qualification in DEMO_TEACHERS:
        profile = session.exec(
            select(TeacherProfile)
            .join(User, TeacherProfile.user_id == User.id)  # type: ignore[arg-type]
            .where(User.full_name == name)
        ).first()
        if profile is None:
            first, _, last = name.partition(" ")
            email = f"{first.lower()}.{last.lower()}@educonnect.com"
            if session.exec(select(User).where(User.email == email)).first():
                email = f"{first.lower()}.{last.lower()}.t@educonnect.com"
            user = _ensure_user(session, email, name, hashed, ["teacher"])
            profile = TeacherProfile(
                user_id=user.id,
                department=department,
                qualification=qualification,
                joining_date=date(2016, 6, 1) + timedelta(days=created * 41),
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            created += 1
        profiles.append(profile)
    if created:
        print(f"[seed_academics] {created} teacher profile(s) created")
    return profiles


def _sync_class_teachers(
    session: Session,
    classrooms: list[Classroom],
    grouped: dict[str, list[Section]],
    teachers: list[TeacherProfile],
) -> None:
    """Section A of every class gets a class teacher (rotating through staff)."""
    if not teachers:
        return
    created = 0
    for index, classroom in enumerate(classrooms):
        sections = grouped.get(classroom.name) or []
        if not sections:
            continue
        section = sections[0]
        exists = session.exec(
            select(ClassTeacherAssignment).where(
                ClassTeacherAssignment.classroom_id == classroom.id,
                ClassTeacherAssignment.section_id == section.id,
            )
        ).first()
        if exists is not None:
            continue
        session.add(
            ClassTeacherAssignment(
                teacher_id=teachers[index % len(teachers)].id,
                classroom_id=classroom.id,
                section_id=section.id,
            )
        )
        created += 1
    if created:
        session.commit()
        print(f"[seed_academics] {created} class-teacher assignment(s) created")


def seed_academics() -> None:
    """Insert the school's structure; every block skips what is already there.

    Students are not seeded here: they are created by registering an admission
    form (`seed_admissions.py`), which is also what makes them show up in the
    directory.
    """
    with Session(engine) as session:
        classrooms = _sync_classrooms(session)
        grouped = _sync_sections(session, classrooms)
        teachers = _sync_teachers(session)
        _sync_class_teachers(session, classrooms, grouped, teachers)
        print(
            "[seed_academics] School structure ready: "
            f"{len(classrooms)} classes, "
            f"{sum(len(sections) for sections in grouped.values())} sections, "
            f"{len(teachers)} teachers"
        )


if __name__ == "__main__":
    seed_academics()
