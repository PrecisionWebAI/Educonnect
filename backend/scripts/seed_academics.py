"""Seed a realistic academics demo school (classes, sections, students, attendance).

Why this file exists:
  `GET /academics/class-matrix` and `GET /academics/class-info` used to return
  hardcoded numbers. They now aggregate from the database, which only shows
  something useful once the school actually has classes, sections, students and
  attendance rows. This script inserts exactly that data.

Idempotent: it exits immediately if the demo classes are already present, so it
is safe to run on every container start (bootstrap.py calls it) and by hand:

    docker exec eduverse-backend python scripts/seed_academics.py
"""

import os
import sys
from datetime import date, timedelta

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.academics.models import GradeClass, Section
from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.auth.roles import set_user_roles
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile
from app.domains.users.models import User

# --- the demo school ------------------------------------------------------
CLASS_LEVELS = [6, 7, 8, 9, 10]
SECTION_NAMES = ["A", "B"]
STUDENTS_PER_SECTION = 8
ATTENDANCE_DAYS = 10
DEMO_PASSWORD = "student123"

DEMO_TEACHERS = [
    ("Meera Iyer", "Mathematics", "M.Sc. Mathematics"),
    ("Arjun Nair", "Science", "M.Sc. Physics"),
    ("Kavita Sharma", "English", "M.A. English"),
    ("Rahul Verma", "Social Studies", "M.A. History"),
]

MALE_NAMES = ["Aarav", "Vihaan", "Kabir", "Rohan", "Ishaan", "Aditya", "Arjun", "Dev"]
FEMALE_NAMES = [
    "Ananya",
    "Ishita",
    "Diya",
    "Saanvi",
    "Aadhya",
    "Meera",
    "Riya",
    "Nisha",
]
SURNAMES = ["Mehta", "Rao", "Singh", "Das", "Gupta", "Nair", "Sharma", "Verma"]
GUARDIANS = [
    "Rakesh",
    "Sunita",
    "Vijay",
    "Anita",
    "Manoj",
    "Priya",
    "Deepak",
    "Shalini",
]


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
    """Deterministic attendance pattern: ~94% attended, varied per section.

    Deterministic (not random) so repeated runs and screenshots stay stable.
    """
    bucket = seed % 100
    if bucket < 4:
        return AttendanceStatus.absent
    if bucket < 8:
        return AttendanceStatus.late
    if bucket < 10:
        return AttendanceStatus.half_day
    if bucket < 12:
        return AttendanceStatus.leave
    return AttendanceStatus.present


def seed_academics() -> None:
    """Insert the demo school. Returns early when it is already there."""
    with Session(engine) as session:
        already = session.exec(
            select(GradeClass).where(GradeClass.level == CLASS_LEVELS[0])
        ).first()
        if already:
            print("[seed_academics] Demo classes already exist. Skipping...")
            return

        # One hash for every demo account: they all share DEMO_PASSWORD, and
        # hashing ~80 times would make startup needlessly slow.
        demo_hash = get_password_hash(DEMO_PASSWORD)

        # 1. Classes and sections (reuse anything the core seed created).
        pairs: list[tuple[GradeClass, Section]] = []
        for level in CLASS_LEVELS:
            grade = session.exec(
                select(GradeClass).where(GradeClass.level == level)
            ).first()
            if grade is None:
                grade = GradeClass(name=f"Grade {level}", level=level)
                session.add(grade)
                session.commit()
                session.refresh(grade)
            for section_name in SECTION_NAMES:
                section = session.exec(
                    select(Section)
                    .where(Section.grade_class_id == grade.id)
                    .where(Section.name == section_name)
                ).first()
                if section is None:
                    section = Section(name=section_name, grade_class_id=grade.id)
                    session.add(section)
                    session.commit()
                    session.refresh(section)
                pairs.append((grade, section))
        print(f"[seed_academics] {len(pairs)} sections ready")

        # 2. Class teachers - one per section (round robin over the demo staff).
        teachers: list[TeacherProfile] = []
        for index, (full_name, department, qualification) in enumerate(DEMO_TEACHERS):
            email = f"cteacher{index + 1}@educonnect.com"
            user = session.exec(select(User).where(User.email == email)).first()
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    hashed_password=demo_hash,
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                # A class teacher also teaches: two roles on one login.
                set_user_roles(session, user, ["class_teacher", "teacher"])
            profile = session.exec(
                select(TeacherProfile).where(TeacherProfile.user_id == user.id)
            ).first()
            if profile is None:
                profile = TeacherProfile(
                    user_id=user.id,
                    department=department,
                    qualification=qualification,
                    joining_date=date(2015 + index, 6, 1),
                )
                session.add(profile)
                session.commit()
                session.refresh(profile)
            teachers.append(profile)

        for index, (grade, section) in enumerate(pairs):
            existing = session.exec(
                select(ClassTeacherAssignment)
                .where(ClassTeacherAssignment.grade_class_id == grade.id)
                .where(ClassTeacherAssignment.section_id == section.id)
            ).first()
            if existing is None:
                session.add(
                    ClassTeacherAssignment(
                        teacher_id=teachers[index % len(teachers)].id,
                        grade_class_id=grade.id,
                        section_id=section.id,
                    )
                )
        session.commit()
        print(f"[seed_academics] {len(teachers)} demo teachers assigned")

        # 3. Students + their logins, and 4. attendance for each of them.
        days = _recent_weekdays(ATTENDANCE_DAYS)
        created = 0
        counter = 0
        for grade, section in pairs:
            for slot in range(STUDENTS_PER_SECTION):
                counter += 1
                is_male = slot % 2 == 0
                pool = MALE_NAMES if is_male else FEMALE_NAMES
                first_name = pool[slot % len(pool)]
                last_name = SURNAMES[(slot + grade.level) % len(SURNAMES)]
                admission_number = f"ADM-{grade.level}{section.name}-{slot + 1:03d}"

                exists = session.exec(
                    select(StudentProfile).where(
                        StudentProfile.admission_number == admission_number
                    )
                ).first()
                if exists:
                    continue

                email = (
                    f"student{grade.level}{section.name.lower()}{slot + 1:02d}"
                    "@educonnect.com"
                )
                user = User(
                    email=email,
                    full_name=f"{first_name} {last_name}",
                    hashed_password=demo_hash,
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                set_user_roles(session, user, ["student"])

                student = StudentProfile(
                    user_id=user.id,
                    admission_number=admission_number,
                    date_of_birth=date(
                        2026 - grade.level - 5, (slot % 12) + 1, (slot % 27) + 1
                    ),
                    guardian_name=f"{GUARDIANS[slot % len(GUARDIANS)]} {last_name}",
                    gender="Male" if is_male else "Female",
                    grade_class_id=grade.id,
                    section_id=section.id,
                )
                session.add(student)
                session.commit()
                session.refresh(student)
                created += 1

                for day_index, day in enumerate(days):
                    seed_value = counter * 37 + day_index * 17 + grade.level * 11
                    session.add(
                        AttendanceRecord(
                            student_id=student.id,
                            grade_class_id=grade.id,
                            section_id=section.id,
                            date=day,
                            status=_status_for(seed_value),
                        )
                    )
        session.commit()
        print(
            f"[seed_academics] {created} students and "
            f"{created * len(days)} attendance records inserted"
        )

        # 5. A pre-existing student without a gender would count towards
        #    strength but not boys/girls. Fill it so the matrix adds up.
        unknown = session.exec(
            select(StudentProfile).where(StudentProfile.gender.is_(None))
        ).all()
        for student in unknown:
            student.gender = "Male"
            session.add(student)
        session.commit()
        if unknown:
            print(
                f"[seed_academics] filled gender for {len(unknown)} existing student(s)"
            )

        print("[seed_academics] Academics demo data ready")


if __name__ == "__main__":
    seed_academics()
