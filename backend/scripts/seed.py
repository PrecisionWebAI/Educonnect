import os

# Need to make sure app is in path
import sys
from datetime import date

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.academics.models import GradeClass, Section, Subject
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import TeacherProfile
from app.domains.users.models import RoleEnum, User


def seed_data():
    with Session(engine) as session:
        # Check if users already exist
        if session.exec(select(User)).first():
            print("Data already seeded. Skipping...")
            return

        print("Seeding Users...")
        # 1. Create Core Users
        users = [
            User(
                email="admin@eduverse.com",
                full_name="System Admin",
                role=RoleEnum.admin,
                hashed_password=get_password_hash("admin123"),
                is_active=True,
            ),
            User(
                email="principal@eduverse.com",
                full_name="Seymour Skinner",
                role=RoleEnum.principal,
                hashed_password=get_password_hash("password"),
                is_active=True,
            ),
            User(
                email="teacher@eduverse.com",
                full_name="Edna Krabappel",
                role=RoleEnum.teacher,
                hashed_password=get_password_hash("password"),
                is_active=True,
            ),
            User(
                email="student@eduverse.com",
                full_name="Bart Simpson",
                role=RoleEnum.student,
                hashed_password=get_password_hash("password"),
                is_active=True,
            ),
            User(
                email="parent@eduverse.com",
                full_name="Homer Simpson",
                role=RoleEnum.parent,
                hashed_password=get_password_hash("password"),
                is_active=True,
            ),
        ]
        for u in users:
            session.add(u)
        session.commit()

        for u in users:
            session.refresh(u)

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
        from app.domains.exams.models import (
            ExamPaper,
            ExamPaperStatus,
            ExamTerm,
        )
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

        # Exams
        term = ExamTerm(
            name="Midterms 2026",
            grade_class_id=grade.id,
            start_date=date.today() + datetime.timedelta(days=14),
            end_date=date.today() + datetime.timedelta(days=21),
        )
        session.add(term)
        session.commit()
        session.refresh(term)

        paper = ExamPaper(
            exam_term_id=term.id,
            subject_id=maths.id,
            status=ExamPaperStatus.draft,
            content_json={
                "title": "Algebra Midterm",
                "questions": [{"q": "Solve for x: 2x=4", "a": "2"}],
            },
        )
        session.add(paper)

        session.commit()

        print("✅ Extended Database successfully seeded!")


if __name__ == "__main__":
    seed_data()
