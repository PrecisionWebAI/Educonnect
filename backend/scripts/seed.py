import os

# Need to make sure app is in path
import sys
from datetime import date

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.academics.models import GradeClass, Section, Subject
from app.domains.auth.roles import set_user_roles
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import TeacherProfile
from app.domains.users.models import User


def seed_data():
    with Session(engine) as session:
        # Check if users already exist
        if session.exec(select(User)).first():
            print("Data already seeded. Skipping...")
            return

        print("Seeding Users...")
        # (email, full_name, password, roles). The last field is a **list**: a
        # person holds one or more roles (`user_role`), which is why the
        # principal also teaches and one account is both teacher and parent.
        #
        # The first five keep their historical order - the profile seeding below
        # refers to `users[2]` (teacher) and `users[3]` (student).
        demo_users = [
            ("admin@educonnect.com", "System Admin", "admin123", ["system_admin"]),
            (
                "principal@educonnect.com",
                "Seymour Skinner",
                "password",
                ["principal", "teacher"],
            ),
            (
                "teacher@educonnect.com",
                "Edna Krabappel",
                "password",
                ["class_teacher", "teacher"],
            ),
            ("student@educonnect.com", "Bart Simpson", "password", ["student"]),
            ("parent@educonnect.com", "Homer Simpson", "password", ["guardian"]),
            ("owner@educonnect.com", "Montgomery Burns", "password", ["owner"]),
            (
                "viceprincipal@educonnect.com",
                "Alicia Reyes",
                "password",
                ["vice_principal"],
            ),
            ("hod@educonnect.com", "Dr. Hibbert", "password", ["hod", "teacher"]),
            ("librarian@educonnect.com", "Mrs. Hoover", "password", ["librarian"]),
            (
                "accountant@educonnect.com",
                "Waylon Smithers",
                "password",
                ["accountant"],
            ),
            ("transport@educonnect.com", "Otto Mann", "password", ["transport"]),
            ("office@educonnect.com", "Selma Bouvier", "password", ["staff"]),
            (
                "teacherparent@educonnect.com",
                "Ned Flanders",
                "password",
                ["teacher", "guardian"],
            ),
        ]

        # Hash each distinct password once, not once per account.
        users: list[User] = []
        hashes: dict[str, str] = {}
        for email, full_name, password, role_names in demo_users:
            existing = session.exec(select(User).where(User.email == email)).first()
            if existing:
                users.append(existing)
                continue
            if password not in hashes:
                hashes[password] = get_password_hash(password)
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=hashes[password],
                is_active=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            set_user_roles(session, user, role_names)
            users.append(user)
        print(f"[seed] {len(users)} demo users ready")

        print("Seeding Academics...")
        # 2. Create Academics Data
        grade = GradeClass(name="Grade 10", level=10)
        session.add(grade)
        session.commit()
        session.refresh(grade)

        section = Section(name="A", grade_class_id=grade.id)
        session.add(section)

        maths = Subject(
            name="Mathematics", code="MTH101", description="Advanced Algebra"
        )
        session.add(maths)
        session.commit()
        session.refresh(section)

        print("Seeding Teacher & Student Profiles...")
        # 3. Create Teacher & Student Profiles
        teacher_profile = TeacherProfile(
            user_id=users[2].id,
            department="Mathematics",
            qualification="M.Sc. Mathematics",
            joining_date=date(2015, 9, 1),
        )
        session.add(teacher_profile)

        student_profile = StudentProfile(
            user_id=users[3].id,
            admission_number="ADM-1001",
            date_of_birth=date(2012, 4, 1),
            guardian_name="Homer Simpson",
            grade_class_id=grade.id,
            section_id=section.id,
        )
        session.add(student_profile)
        session.commit()
        session.refresh(teacher_profile)
        session.refresh(student_profile)

        import datetime

        from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
        from app.domains.finance.models import (
            FeeFrequency,
            FeeStructure,
            FeeTransaction,
            PaymentMode,
        )
        from app.domains.homework.models import (
            HomeworkAssignment,
            HomeworkSubmission,
            SubmissionStatus,
        )
        from app.domains.timetable.models import DayOfWeek, TimetablePeriod

        print("Seeding Extended Domains...")

        # Attendance
        attendance = AttendanceRecord(
            student_id=student_profile.id,
            grade_class_id=grade.id,
            section_id=section.id,
            date=date.today(),
            status=AttendanceStatus.present,
        )
        session.add(attendance)

        # Finance
        fee_structure = FeeStructure(
            name="Tuition Fee",
            amount=500.0,
            grade_class_id=grade.id,
            frequency=FeeFrequency.monthly,
        )
        session.add(fee_structure)
        session.commit()
        session.refresh(fee_structure)

        fee_transaction = FeeTransaction(
            student_id=student_profile.id,
            fee_structure_id=fee_structure.id,
            amount_paid=500.0,
            date=date.today(),
            payment_mode=PaymentMode.card,
            receipt_number="RCPT-1001",
        )
        session.add(fee_transaction)

        # Timetable
        period = TimetablePeriod(
            grade_class_id=grade.id,
            section_id=section.id,
            subject_id=maths.id,
            teacher_id=teacher_profile.id,
            day_of_week=DayOfWeek.monday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(9, 45),
            room="Room 101",
        )
        session.add(period)

        # Homework
        hw = HomeworkAssignment(
            title="Algebra Basics",
            description="Solve exercises 1-10 on page 42.",
            grade_class_id=grade.id,
            section_id=section.id,
            subject_id=maths.id,
            teacher_id=teacher_profile.id,
            due_date=date.today() + datetime.timedelta(days=2),
        )
        session.add(hw)
        session.commit()
        session.refresh(hw)

        hw_sub = HomeworkSubmission(
            homework_id=hw.id,
            student_id=student_profile.id,
            status=SubmissionStatus.submitted,
        )
        session.add(hw_sub)

        from app.domains.chat.service import ensure_default_threads

        for u in users:
            ensure_default_threads(session, u.id)

        print("✅ Extended Database successfully seeded!")


if __name__ == "__main__":
    seed_data()
