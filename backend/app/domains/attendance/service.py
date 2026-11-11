from datetime import date
from uuid import UUID
from sqlmodel import Session

from app.domains.academics.models import ClassName, Classroom, Section, Subject
from app.domains.students.models import Student
from app.domains.users.models import User

from . import repository
from .models import AttendanceRecord
from .schemas import AttendanceBulkCreate, AttendanceRecordCreate, AttendanceRecordRead


def _build_attendance_read(
    session: Session, rec: AttendanceRecord
) -> AttendanceRecordRead:
    student = session.get(Student, rec.student_id) if rec.student_id else None
    user = session.get(User, student.user_id) if (student and student.user_id) else None
    room = session.get(Classroom, rec.classroom_id) if rec.classroom_id else None
    # The class and the letter are read from the class-section; the register no
    # longer stores a copy of either.
    classroom = session.get(ClassName, room.class_id) if room else None
    letter = session.get(Section, room.section_id) if room else None
    subj = (
        session.get(Subject, rec.subject_id)
        if getattr(rec, "subject_id", None)
        else None
    )

    class_str = (
        f"{classroom.classname}-{letter.section_name}"
        if (classroom and letter)
        else (classroom.classname if classroom else "Class 10-A")
    )

    return AttendanceRecordRead(
        id=rec.id,
        student_id=rec.student_id,
        # The register's class-section, under the name the model now uses.
        classroom_id=rec.classroom_id,
        subject_id=rec.subject_id,
        date=rec.date,
        status=rec.status,
        remarks=rec.remarks,
        studentName=(student.full_name if student else None)
        or (user.full_name if user else "Student"),
        className=class_str,
        subjectName=subj.name if subj else None,
        overridden_by_id=rec.overridden_by_id,
    )


def get_all_attendance(
    session: Session, skip: int = 0, limit: int = 100
) -> list[AttendanceRecordRead]:
    records = repository.get_all_attendance(session, skip=skip, limit=limit)
    return [_build_attendance_read(session, r) for r in records]


def get_attendance_by_section_and_date(
    session: Session, section_id: UUID, target_date: date
) -> list[AttendanceRecordRead]:
    records = repository.get_attendance_by_section_and_date(
        session, section_id, target_date
    )
    return [_build_attendance_read(session, r) for r in records]


def get_attendance_by_student(
    session: Session, student_id: UUID
) -> list[AttendanceRecordRead]:
    records = repository.get_attendance_by_student(session, student_id)
    return [_build_attendance_read(session, r) for r in records]


def bulk_create_attendance(
    session: Session, bulk_data: AttendanceBulkCreate, current_user: User = None
) -> list[AttendanceRecord]:
    from sqlmodel import select

    results = []
    for rec in bulk_data.records:
        existing_record = session.exec(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id == rec["student_id"])
            .where(AttendanceRecord.date == bulk_data.date)
            .where(AttendanceRecord.subject_id == bulk_data.subject_id)
        ).first()

        # It's an override if it already exists, and the status/remarks change, and the user isn't the same.
        # For simplicity, if it exists, mark it as overridden by current user.
        overridden_by_id = None
        if existing_record and current_user:
            overridden_by_id = current_user.id

        record_in = AttendanceRecordCreate(
            student_id=rec["student_id"],
            # The register names the class-section; the model calls it a classroom.
            classroom_id=bulk_data.section_id,
            subject_id=bulk_data.subject_id,
            date=bulk_data.date,
            status=rec["status"],
            remarks=rec.get("remarks"),
            overridden_by_id=overridden_by_id,
        )
        saved = repository.create_or_update_attendance(session, record_in)
        results.append(saved)
    return results


def list_irregular(session: Session) -> list["IrregularStudentRead"]:
    """Students with absences, derived from real `attendancerecord` rows."""
    from .schemas import IrregularStudentRead

    result: list[IrregularStudentRead] = []
    for student_id, absences in repository.get_absent_counts(session):
        student = session.get(Student, student_id)
        if not student:
            continue
        user = session.get(User, student.user_id) if student.user_id else None
        section = session.get(Classroom, student.classroom_id) if student.classroom_id else None
        classroom = session.get(ClassName, section.class_id) if section else None
        letter = session.get(Section, section.section_id) if section else None
        class_name = classroom.classname if classroom else ""
        if letter:
            class_name = f"{class_name}-{letter.section_name}"
        risk = "High" if absences >= 10 else ("Medium" if absences >= 6 else "Low")
        result.append(
            IrregularStudentRead(
                # The student's own id: the row is *about* them, so it is the key
                # the screen can act on (and it is a UUID, which is what the
                # schema promises - a running number here answered 500).
                id=student_id,
                # The profile's own name first: a student without a login still has
                # a name to show (the login is not the identity).
                name=(student.full_name or (user.full_name if user else ""))
                or f"Student {student_id}",
                className=class_name,
                absences=absences,
                pattern="Frequent" if absences >= 10 else "Scattered",
                risk=risk,
            )
        )
    return result


def list_leave_sync(session: Session) -> list["LeaveSyncRowRead"]:
    """Student leave requests that sync onto the attendance register."""
    from sqlmodel import select

    from app.domains.operations.models import LeaveRequest

    from .schemas import LeaveSyncRowRead

    statement = (
        select(LeaveRequest)
        .where(LeaveRequest.student_id != None)  # noqa: E711
        .order_by(LeaveRequest.from_date.desc())
    )
    result: list[LeaveSyncRowRead] = []
    for request in session.exec(statement).all():
        student = session.get(Student, request.student_id)
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        section = session.get(Classroom, student.classroom_id) if (student and student.classroom_id) else None
        classroom = session.get(ClassName, section.class_id) if section else None
        letter = session.get(Section, section.section_id) if section else None
        class_name = classroom.classname if classroom else ""
        if letter:
            class_name = f"{class_name}-{letter.section_name}"
        synced = request.status == "Approved"
        result.append(
            LeaveSyncRowRead(
                # The request's own id (a UUID, as the schema says) - a running
                # number here made the whole tab answer 500 once there was a row.
                id=request.id,
                student=(student.full_name if student else None)
                or (user.full_name if user else f"Student {request.student_id}"),
                className=class_name,
                from_date=request.from_date.strftime("%b %d"),
                days=request.days,
                autoMarked="Approved leave" if synced else "Awaiting approval",
                status="Synced" if synced else "Pending",
            )
        )
    return result
