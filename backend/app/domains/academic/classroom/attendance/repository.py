"""Reads behind the register, its summary, its trend and its leave links.

Every query narrows in SQL. The two that matter on a real school (500 students x
200 days) are `records_between` and `approved_leaves_between`: the summary and the
trend ask for a **range** once, not one day at a time.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.students.models import Student
from app.domains.services.leave.models import LeaveRequest

from .models import AttendanceAuditLog, AttendanceRecord, AttendanceStatus

#: The word the leave workflow stores for a granted request.
APPROVED = "Approved"


def get_attendance_by_section_and_date(
    session: Session, section_id: UUID, target_date: date
) -> list[AttendanceRecord]:
    """The register for one class-section on one day.

    The class is not part of the lookup any more: it comes from
    `section.class_id`, so naming the section is enough.
    """
    statement = select(AttendanceRecord).where(
        AttendanceRecord.classroom_id == section_id,
        AttendanceRecord.date == target_date,
    )
    return list(session.exec(statement).all())


def get_attendance_by_student(
    session: Session, student_id: UUID
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


def active_students(session: Session, classroom_id: UUID) -> list[Student]:
    """The roll of one class-section: children who have not left it.

    A deactivated student keeps their rows (history is never deleted), but they are
    not on today's register - the same rule the directory's "Active" chip uses.
    """
    statement = (
        select(Student)
        .where(
            Student.classroom_id == classroom_id,
            Student.deactivated_at.is_(None),
        )
        .order_by(Student.admission_number)
    )
    return list(session.exec(statement).all())


def roll_students(session: Session, classroom_id: UUID) -> list[Student]:
    """Every child the class-section holds, alphabetical - the marking sheet's roll.

    `active_students` leaves out a child who has left the school, which is right for a
    percentage (a leaver must not drag it down) but wrong for the register: the teacher is
    marking the section the directory lists, and a row that silently disappears is how a
    child ends up with a hole in their history. The row carries `active` instead, so the
    screen can grey its chips out without hiding the child.
    """
    statement = (
        select(Student)
        .where(Student.classroom_id == classroom_id)
        .order_by(func.coalesce(Student.full_name, Student.admission_number))
    )
    return list(session.exec(statement).all())


def records_on(
    session: Session, classroom_id: UUID, on_date: date, subject_id: UUID | None
) -> list[AttendanceRecord]:
    """Rows for one class-section, day and (optionally) subject."""
    statement = select(AttendanceRecord).where(
        AttendanceRecord.classroom_id == classroom_id,
        AttendanceRecord.date == on_date,
    )
    if subject_id is None:
        statement = statement.where(AttendanceRecord.classroom_subject_id.is_(None))
    else:
        statement = statement.where(AttendanceRecord.classroom_subject_id == subject_id)
    return list(session.exec(statement).all())


def records_between(
    session: Session,
    classroom_id: UUID,
    start: date,
    end: date,
    subject_id: UUID | None = None,
) -> list[AttendanceRecord]:
    """Rows for one class-section over a range - one query for a whole summary."""
    statement = select(AttendanceRecord).where(
        AttendanceRecord.classroom_id == classroom_id,
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    )
    if subject_id is not None:
        statement = statement.where(AttendanceRecord.classroom_subject_id == subject_id)
    statement = statement.order_by(AttendanceRecord.date)
    return list(session.exec(statement).all())


def find_record(
    session: Session, student_id: UUID, on_date: date, subject_id: UUID | None
) -> AttendanceRecord | None:
    """The row this save would update, keyed exactly like the unique constraint.

    `subject_id IS NULL` is a real value here (the day-level mark), so it is compared
    with `is_`, not `==`: `NULL == NULL` would find nothing and the save would try to
    insert a second day-level row.
    """
    statement = select(AttendanceRecord).where(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.date == on_date,
    )
    if subject_id is None:
        statement = statement.where(AttendanceRecord.classroom_subject_id.is_(None))
    else:
        statement = statement.where(AttendanceRecord.classroom_subject_id == subject_id)
    return session.exec(statement).first()


def approved_leave_on(
    session: Session, student_ids: list[UUID], on_date: date
) -> dict[UUID, LeaveRequest]:
    """{student_id: the approved request} for one day - the register's `leave`.

    A range test (`from_date <= day <= to_date`) on approved rows, answered by
    `ix_leaverequest_school_status_window`. Cancelled or rejected requests are not
    "approved", so a cancelled leave stops showing the moment it is decided - the
    register row keeps saying what the teacher marked.
    """
    if not student_ids:
        return {}
    rows = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.student_id.in_(student_ids),
            LeaveRequest.status == APPROVED,
            LeaveRequest.from_date <= on_date,
            LeaveRequest.to_date >= on_date,
        )
    ).all()
    leaves: dict[UUID, LeaveRequest] = {}
    for request in rows:
        if request.student_id is not None and request.student_id not in leaves:
            leaves[request.student_id] = request
    return leaves


def approved_leaves_between(
    session: Session, student_ids: list[UUID], start: date, end: date
) -> list[LeaveRequest]:
    """Approved requests that overlap the range (for the per-student totals)."""
    if not student_ids:
        return []
    return list(
        session.exec(
            select(LeaveRequest).where(
                LeaveRequest.student_id.in_(student_ids),
                LeaveRequest.status == APPROVED,
                LeaveRequest.from_date <= end,
                LeaveRequest.to_date >= start,
            )
        ).all()
    )


def saved_dates(
    session: Session, classroom_id: UUID, start: date, end: date
) -> set[date]:
    """The days this class-section has a register on - the month calendar's dots.

    One distinct read for the whole month. The summary is not built from it (that needs
    every mark), but the calendar only asks "was there a register that day", so a month
    with a 40-child roll costs one small query instead of 1 200 rows.
    """
    day = AttendanceRecord.date
    rows = session.exec(
        select(day)
        .where(
            AttendanceRecord.classroom_id == classroom_id,
            day >= start,
            day <= end,
        )
        .distinct()
    ).all()
    return {value for value in rows if value is not None}


def audit_rows(session: Session, record_id: UUID) -> list[AttendanceAuditLog]:
    """Every change recorded against one register row (oldest first)."""
    return list(
        session.exec(
            select(AttendanceAuditLog)
            .where(AttendanceAuditLog.attendance_record_id == record_id)
            .order_by(AttendanceAuditLog.changed_at)
        ).all()
    )


def get_absent_counts(session: Session) -> list[tuple[int, int]]:
    """{student_id: absence count} for the irregular-attendance screen."""
    rows = session.exec(
        select(AttendanceRecord.student_id, func.count())
        .where(AttendanceRecord.status == AttendanceStatus.absent)
        .group_by(AttendanceRecord.student_id)
    ).all()
    return [(student_id, int(count)) for student_id, count in rows]
