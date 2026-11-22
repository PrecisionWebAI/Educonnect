"""Reads and writes for homework, submissions and the diary.

The only place that knows the two names for one thing: the API's `section_id` and the
column's `classroom_id`. Everything above this file speaks `section_id`.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, func, select

from .models import ClassLog, HomeworkAssignment, HomeworkSubmission, SubmissionStatus
from .schemas import (
    ClassLogCreate,
    HomeworkAssignmentCreate,
    SubmissionFeedbackIn,
)


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> HomeworkAssignment:
    """Store the assignment against the class-section it was set for."""
    row = HomeworkAssignment(
        title=homework_in.title,
        description=homework_in.description,
        classroom_id=homework_in.section_id,
        classroom_subject_id=homework_in.classroom_subject_id,
        teacher_id=homework_in.teacher_id,
        due_date=homework_in.due_date,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_homework_by_section(
    session: Session, section_id: UUID
) -> list[HomeworkAssignment]:
    """Homework set for one class-section, newest due date first.

    A section is the unit homework goes to - the class comes from
    `section.class_id`, so there is no class-wide homework to look up.
    """
    statement = (
        select(HomeworkAssignment)
        .where(HomeworkAssignment.classroom_id == section_id)
        .order_by(HomeworkAssignment.due_date.desc())
    )
    return list(session.exec(statement).all())


def get_all_homework(session: Session) -> list[HomeworkAssignment]:
    return list(
        session.exec(
            select(HomeworkAssignment).order_by(HomeworkAssignment.due_date.desc())
        ).all()
    )


def submission_counts(session: Session, homework_ids: list[UUID]) -> dict[UUID, int]:
    """{homework_id: how many children have handed it in} - one query for a board.

    A `pending` row means "not handed in yet", so it is not counted; everything else
    (submitted or graded) is work the teacher has.
    """
    if not homework_ids:
        return {}
    rows = session.exec(
        select(HomeworkSubmission.homework_id, func.count())
        .where(
            HomeworkSubmission.homework_id.in_(homework_ids),
            HomeworkSubmission.status != SubmissionStatus.pending,
        )
        .group_by(HomeworkSubmission.homework_id)
    ).all()
    return {homework_id: int(count) for homework_id, count in rows}


def roll_counts(session: Session, section_ids: list[UUID]) -> dict[UUID, int]:
    """{section_id: how many children are on its roll} - the "out of" of "3/4 in"."""
    from app.domains.academic.classroom.students.models import Student

    rooms = [room for room in dict.fromkeys(section_ids) if room is not None]
    if not rooms:
        return {}
    rows = session.exec(
        select(Student.classroom_id, func.count())
        .where(
            Student.classroom_id.in_(rooms),
            Student.deactivated_at.is_(None),
        )
        .group_by(Student.classroom_id)
    ).all()
    return {room: int(count) for room, count in rows if room is not None}


def get_submission(
    session: Session, homework_id: UUID, student_id: UUID
) -> HomeworkSubmission | None:
    return session.exec(
        select(HomeworkSubmission).where(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student_id,
        )
    ).first()


def get_submission_by_id(
    session: Session, submission_id: UUID
) -> HomeworkSubmission | None:
    return session.get(HomeworkSubmission, submission_id)


def save_submission(
    session: Session,
    *,
    existing: HomeworkSubmission | None,
    homework_id: UUID,
    student_id: UUID,
    content_url: str | None,
    submitted_at: datetime | None,
    is_late: bool,
) -> HomeworkSubmission:
    """Upsert one child's row for one assignment.

    Handing work in is the student's act, so it moves the row to `submitted` - except
    that a **graded** row stays graded: re-uploading a file does not un-grade work the
    teacher has already looked at. The unique key on `(homework_id, student_id)` is the
    backstop if two requests race here.
    """
    if existing is None:
        row = HomeworkSubmission(
            homework_id=homework_id,
            student_id=student_id,
            content_url=content_url,
            status=SubmissionStatus.submitted,
            submitted_at=submitted_at,
            is_late=is_late,
        )
        session.add(row)
    else:
        row = existing
        if content_url:
            row.content_url = content_url
        if submitted_at is not None:
            row.submitted_at = submitted_at
        if row.status != SubmissionStatus.graded:
            row.status = SubmissionStatus.submitted
        if is_late:
            row.is_late = True
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def save_feedback(
    session: Session,
    submission: HomeworkSubmission,
    feedback_in: SubmissionFeedbackIn,
    *,
    graded_at: datetime,
) -> HomeworkSubmission:
    """Record a score and/or a remark, and move the row to `graded`."""
    if feedback_in.marks_awarded is not None:
        submission.marks_awarded = Decimal(feedback_in.marks_awarded)
    if feedback_in.teacher_feedback is not None:
        submission.teacher_feedback = feedback_in.teacher_feedback.strip() or None
    submission.graded_at = graded_at
    submission.status = SubmissionStatus.graded
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


def get_all_submissions(session: Session) -> list[HomeworkSubmission]:
    return list(
        session.exec(select(HomeworkSubmission).order_by(HomeworkSubmission.id)).all()
    )


def get_submissions_for_section(
    session: Session, section_id: UUID
) -> list[HomeworkSubmission]:
    """Every submission on this class-section's assignments, oldest first."""
    return list(
        session.exec(
            select(HomeworkSubmission)
            .join(
                HomeworkAssignment,
                HomeworkAssignment.id == HomeworkSubmission.homework_id,
            )
            .where(HomeworkAssignment.classroom_id == section_id)
            .order_by(HomeworkSubmission.id)
        ).all()
    )


def create_class_log(session: Session, log_in: ClassLogCreate) -> ClassLog:
    """Add one line to a class-section's day (the keys decide the shape)."""
    row = ClassLog(
        classroom_id=log_in.section_id,
        teacher_id=log_in.teacher_id,
        timetableperiod_id=log_in.timetableperiod_id,
        classroom_subject_id=log_in.classroom_subject_id,
        date=log_in.date,
        note=log_in.note,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_class_log_by_section(session: Session, section_id: UUID) -> list[ClassLog]:
    return list(
        session.exec(
            select(ClassLog)
            .where(ClassLog.classroom_id == section_id)
            .order_by(ClassLog.date.desc())
        ).all()
    )


def get_all_class_logs(session: Session) -> list[ClassLog]:
    return list(session.exec(select(ClassLog).order_by(ClassLog.date.desc())).all())
