from datetime import date

from sqlmodel import Session

from app.domains.academics.models import GradeClass, Section
from app.domains.students.models import StudentProfile
from app.domains.users.models import User

from . import repository
from .models import AttendanceRecord
from .schemas import AttendanceBulkCreate, AttendanceRecordCreate, AttendanceRecordRead


def _build_attendance_read(
    session: Session, rec: AttendanceRecord
) -> AttendanceRecordRead:
    student = session.get(StudentProfile, rec.student_id) if rec.student_id else None
    user = session.get(User, student.user_id) if (student and student.user_id) else None
    grade_class = (
        session.get(GradeClass, rec.grade_class_id) if rec.grade_class_id else None
    )
    sec = session.get(Section, rec.section_id) if rec.section_id else None

    class_str = (
        f"{grade_class.name.replace('Grade ', '')}-{sec.name}"
        if (grade_class and sec)
        else (grade_class.name if grade_class else "10-A")
    )

    return AttendanceRecordRead(
        id=rec.id,
        student_id=rec.student_id,
        grade_class_id=rec.grade_class_id,
        section_id=rec.section_id,
        date=rec.date,
        status=rec.status,
        remarks=rec.remarks,
        studentName=user.full_name if user else "Student",
        className=class_str,
    )


def get_all_attendance(
    session: Session, skip: int = 0, limit: int = 100
) -> list[AttendanceRecordRead]:
    records = repository.get_all_attendance(session, skip=skip, limit=limit)
    return [_build_attendance_read(session, r) for r in records]


def get_attendance_by_class_and_date(
    session: Session, class_id: int, section_id: int, target_date: date
) -> list[AttendanceRecordRead]:
    records = repository.get_attendance_by_class_and_date(
        session, class_id, section_id, target_date
    )
    return [_build_attendance_read(session, r) for r in records]


def get_attendance_by_student(
    session: Session, student_id: int
) -> list[AttendanceRecordRead]:
    records = repository.get_attendance_by_student(session, student_id)
    return [_build_attendance_read(session, r) for r in records]


def bulk_create_attendance(
    session: Session, bulk_data: AttendanceBulkCreate
) -> list[AttendanceRecord]:
    results = []
    for rec in bulk_data.records:
        record_in = AttendanceRecordCreate(
            student_id=rec["student_id"],
            grade_class_id=bulk_data.grade_class_id,
            section_id=bulk_data.section_id,
            date=bulk_data.date,
            status=rec["status"],
            remarks=rec.get("remarks"),
        )
        saved = repository.create_or_update_attendance(session, record_in)
        results.append(saved)
    return results
