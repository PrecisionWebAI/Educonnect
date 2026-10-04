"""Seed a realistic academics demo school (classrooms, sections, students, attendance).

Why this file exists:
  `GET /academics/class-matrix` and `GET /academics/class-info` used to return
  hardcoded numbers. They now aggregate from the database, which only shows
  something useful once the school actually has classes, sections, students and
  attendance rows. This script inserts exactly that data.

Scope: the whole school - Nursery to Class 12, ten sections (A-J) per class - so
  every screen that offers a class or a section offers something real. The
  deliberately awkward cases are seeded too (a section nobody sits in, a student
  with no section, a student with no recorded gender, a student with no
  attendance at all): a demo that only shows the happy path hides the bugs.

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
from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.auth.roles import set_user_roles
from app.domains.students.models import StudentProfile
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

#: Classes that get students in two sections (the rest of the sections stay
#: empty on purpose, so "empty section" is a state the screens really show).
POPULATED_SECTIONS = ("A", "B")

#: Per section, per class - small numbers, but spread over the whole school.
STUDENTS_PER_SECTION = 3

#: Weekdays of attendance history each new student gets.
ATTENDANCE_DAYS = 10

#: The two roles the students and the teachers log in with.
DEMO_PASSWORD = "student123"

#: ("Grade 6" -> "Class 6") - rows created before the vocabulary moved.
LEGACY_NAME = re.compile(r"^Grade\s+(\d+)$")

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

MALE_NAMES: tuple[str, ...] = (
    "Aarav", "Vihaan", "Kabir", "Rohan", "Ishaan", "Aditya",
    "Arjun", "Dev", "Yash", "Neel", "Rudra", "Om",
)
FEMALE_NAMES: tuple[str, ...] = (
    "Ananya", "Ishita", "Diya", "Saanvi", "Aadhya", "Meera",
    "Riya", "Nisha", "Tara", "Ira", "Mahi", "Kiara",
)
SURNAMES: tuple[str, ...] = (
    "Mehta", "Rao", "Singh", "Das", "Gupta", "Nair",
    "Sharma", "Verma", "Patel", "Joshi", "Kulkarni", "Reddy",
)
GUARDIANS: tuple[str, ...] = (
    "Rakesh", "Sunita", "Vijay", "Anita", "Manoj", "Priya",
    "Deepak", "Shalini", "Ravi", "Neha", "Ashok", "Kiran",
)


def _recent_weekdays(count: int) -> list[date]:
    """The last `count` weekdays, so attendance looks like a real register."""
    days: list[date] = []
    cursor = date.today()
    while len(days) < count:
        if cursor.weekday() < 5:  # Monday to Friday
            days.append(cursor)
        cursor -= timedelta(days=1)
    return days


def _status_for(seed: int) -> AttendanceStatus:
    """Deterministic attendance pattern, with every status represented.

    Deterministic (not random) so repeated runs and screenshots stay stable.
    """
    bucket = seed % 100
    if bucket < 6:
        return AttendanceStatus.absent
    if bucket < 10:
        return AttendanceStatus.late
    if bucket < 12:
        return AttendanceStatus.half_day
    if bucket < 14:
        return AttendanceStatus.leave
    return AttendanceStatus.present


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
        clash = session.exec(
            select(Classroom).where(Classroom.name == target)
        ).first()
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
# 2. Teaching staff - profiles plus one class-teacher per class
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


# ---------------------------------------------------------------------------
# 3. Students - the roll, plus the cases the screens must survive
# ---------------------------------------------------------------------------


def _ensure_student(
    session: Session,
    hashed: str,
    *,
    serial: int,
    classroom: Classroom | None,
    section: Section | None,
    admission_number: str,
    email: str,
    gender: str | None,
    last_name: str,
) -> StudentProfile | None:
    """One student with a login and (optionally) a placement. None if present."""
    if session.exec(
        select(StudentProfile).where(
            StudentProfile.admission_number == admission_number
        )
    ).first():
        return None

    is_male = gender == "Male"
    pool = MALE_NAMES if is_male else FEMALE_NAMES
    first_name = pool[serial % len(pool)]
    name = f"{first_name} {last_name}"
    user = _ensure_user(session, email, name, hashed, ["student"])
    level = classroom.level if classroom else 0
    student = StudentProfile(
        user_id=user.id,
        admission_number=admission_number,
        date_of_birth=date(2026 - (level + 4), (serial % 12) + 1, (serial % 27) + 1),
        guardian_name=f"{GUARDIANS[serial % len(GUARDIANS)]} {last_name}",
        gender=gender,
        classroom_id=classroom.id if classroom else None,
        section_id=section.id if section else None,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def _add_attendance(
    session: Session, student: StudentProfile, serial: int, days: list[date]
) -> int:
    """A register for one student over `days`; unplaced students get none."""
    if not (student.classroom_id and student.section_id):
        return 0
    for day_index, day in enumerate(days):
        session.add(
            AttendanceRecord(
                student_id=student.id,
                classroom_id=student.classroom_id,
                section_id=student.section_id,
                date=day,
                status=_status_for(serial * 37 + day_index * 17),
            )
        )
    return len(days)



def _sync_students(
    session: Session,
    classrooms: list[Classroom],
    grouped: dict[str, list[Section]],
    days: list[date],
) -> None:
    """The roll (two populated sections per class) plus the awkward rows."""
    hashed = get_password_hash(DEMO_PASSWORD)
    serial = 0
    students = 0
    registers = 0

    for class_index, classroom in enumerate(classrooms, start=1):
        for section in grouped.get(classroom.name) or []:
            if section.name not in POPULATED_SECTIONS:
                continue
            for slot in range(STUDENTS_PER_SECTION):
                serial += 1
                student = _ensure_student(
                    session,
                    hashed,
                    serial=serial,
                    classroom=classroom,
                    section=section,
                    admission_number=(
                        f"ADM-{class_index:02d}{section.name}-{slot + 1:03d}"
                    ),
                    email=(
                        f"student{class_index:02d}{section.name.lower()}"
                        f"{slot + 1:02d}@educonnect.com"
                    ),
                    gender="Male" if serial % 2 == 0 else "Female",
                    last_name=SURNAMES[(serial + class_index) % len(SURNAMES)],
                )
                if student is None:
                    continue
                students += 1
                registers += _add_attendance(session, student, serial, days)

    # --- the states the screens must survive, one student each --------------
    # (a) Gender never recorded: counts towards strength, not boys/girls.
    first_class = classrooms[0]
    first_sections = grouped.get(first_class.name) or []
    for offset in range(2):
        serial += 1
        student = _ensure_student(
            session,
            hashed,
            serial=serial,
            classroom=first_class,
            section=first_sections[0] if first_sections else None,
            admission_number=f"ADM-ODD-{offset + 1:03d}",
            email=f"student.unknown{offset + 1}@educonnect.com",
            gender=None,
            last_name=SURNAMES[offset],
        )
        if student is not None:
            students += 1
            registers += _add_attendance(session, student, serial, days)

    # (b) Admission still in progress: no class, no section. The class cards
    #     have to keep listing them instead of dropping the row.
    for offset in range(3):
        serial += 1
        student = _ensure_student(
            session,
            hashed,
            serial=serial,
            classroom=None,
            section=None,
            admission_number=f"ADM-NEW-{offset + 1:03d}",
            email=f"student.unplaced{offset + 1}@educonnect.com",
            gender="Male" if offset % 2 else "Female",
            last_name=SURNAMES[(offset + 3) % len(SURNAMES)],
        )
        if student is not None:
            students += 1

    # (c) A student with no attendance rows at all: that section's average has
    #     to read 0%, not blow up.
    last_class = classrooms[-1]
    last_sections = grouped.get(last_class.name) or []
    serial += 1
    if _ensure_student(
        session,
        hashed,
        serial=serial,
        classroom=last_class,
        section=last_sections[-1] if last_sections else None,
        admission_number="ADM-NONREG-001",
        email="student.noattendance@educonnect.com",
        gender="Female",
        last_name="Patel",
    ):
        students += 1

    session.commit()
    if students:
        print(
            f"[seed_academics] {students} students and {registers} "
            "attendance records inserted"
        )


def seed_academics() -> None:
    """Insert the demo school; every block skips what is already there."""
    with Session(engine) as session:
        classrooms = _sync_classrooms(session)
        grouped = _sync_sections(session, classrooms)
        teachers = _sync_teachers(session)
        _sync_class_teachers(session, classrooms, grouped, teachers)
        _sync_students(session, classrooms, grouped, _recent_weekdays(ATTENDANCE_DAYS))
        print(
            "[seed_academics] Academics demo data ready: "
            f"{len(classrooms)} classes, "
            f"{sum(len(sections) for sections in grouped.values())} sections, "
            f"{len(teachers)} teachers"
        )


if __name__ == "__main__":
    seed_academics()

