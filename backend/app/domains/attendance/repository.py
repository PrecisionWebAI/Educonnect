from datetime import date

from sqlmodel import Session, select

from .models import AttendanceRecord
from .schemas import AttendanceRecordCreate


def get_attendance_by_class_and_date(
    session: Session, class_id: int, section_id: int, target_date: date
) -> list[AttendanceRecord]:
    statement = select(AttendanceRecord).where(
        AttendanceRecord.grade_class_id == class_id,
        AttendanceRecord.section_id == section_id,
        AttendanceRecord.date == target_date,
    )
    return list(session.exec(statement).all())


def get_attendance_by_student(
    session: Session, student_id: int
) -> list[AttendanceRecord]:
    statement = (
        select(AttendanceRecord)
        .where(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceRecord.date.desc())
    )
    return list(session.exec(statement).all())


def get_all_attendance(
    session: Session, skip: int = 0, limit: int = 100
) -> list[AttendanceRecord]:
    statement = (
        select(AttendanceRecord)
        .offset(skip)
        .limit(limit)
        .order_by(AttendanceRecord.date.desc())
    )
    return list(session.exec(statement).all())


def create_or_update_attendance(
    session: Session, record_in: AttendanceRecordCreate
) -> AttendanceRecord:
    # Check if record already exists for this student on this date and subject
    statement = select(AttendanceRecord).where(
        AttendanceRecord.student_id == record_in.student_id,
        AttendanceRecord.date == record_in.date,
        AttendanceRecord.subject_id == record_in.subject_id,
    )
    existing_record = session.exec(statement).first()

    if existing_record:
        if (
            existing_record.status != record_in.status
            or existing_record.remarks != record_in.remarks
        ):
            if record_in.overridden_by_id:
                from .models import AttendanceAuditLog

                audit_log = AttendanceAuditLog(
                    attendance_record_id=existing_record.id,
                    changed_by_id=record_in.overridden_by_id,
                    previous_status=existing_record.status,
                    new_status=record_in.status,
                    previous_remarks=existing_record.remarks,
                    new_remarks=record_in.remarks,
                )
                session.add(audit_log)

            existing_record.status = record_in.status
            existing_record.remarks = record_in.remarks
            existing_record.overridden_by_id = record_in.overridden_by_id
            session.add(existing_record)
            session.commit()
            session.refresh(existing_record)
        return existing_record

    new_record = AttendanceRecord.model_validate(record_in)
    session.add(new_record)
    session.commit()
    session.refresh(new_record)
    return new_record
