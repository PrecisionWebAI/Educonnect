from datetime import date

from sqlmodel import Session

from . import repository
from .models import AttendanceRecord
from .schemas import AttendanceBulkCreate, AttendanceRecordCreate


def get_attendance_by_class_and_date(
    session: Session, class_id: int, section_id: int, target_date: date
) -> list[AttendanceRecord]:
    return repository.get_attendance_by_class_and_date(
        session, class_id, section_id, target_date
    )


def get_attendance_by_student(
    session: Session, student_id: int
) -> list[AttendanceRecord]:
    return repository.get_attendance_by_student(session, student_id)


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
