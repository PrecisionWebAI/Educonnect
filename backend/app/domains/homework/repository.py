from uuid import UUID
from sqlmodel import Session, select

from .models import ClassLog, HomeworkAssignment, HomeworkSubmission
from .schemas import (
    ClassLogCreate,
    HomeworkAssignmentCreate,
    HomeworkSubmissionCreate,
)


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> HomeworkAssignment:
    db_homework = HomeworkAssignment.model_validate(homework_in)
    session.add(db_homework)
    session.commit()
    session.refresh(db_homework)
    return db_homework


def get_homework_by_section(
    session: Session, section_id: UUID
) -> list[HomeworkAssignment]:
    """Homework set for one class-section, newest due date first.

    A section is the unit homework goes to now - the class comes from
    `section.classroom_id`, so there is no class-wide homework to look up.
    """
    statement = (
        select(HomeworkAssignment)
        .where(HomeworkAssignment.section_id == section_id)
        .order_by(HomeworkAssignment.due_date.desc())
    )
    return list(session.exec(statement).all())


def create_or_update_submission(
    session: Session, submission_in: HomeworkSubmissionCreate
) -> HomeworkSubmission:
    statement = select(HomeworkSubmission).where(
        HomeworkSubmission.homework_id == submission_in.homework_id,
        HomeworkSubmission.student_id == submission_in.student_id,
    )
    existing = session.exec(statement).first()

    if existing:
        existing.status = submission_in.status
        if submission_in.content_url:
            existing.content_url = submission_in.content_url
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    db_submission = HomeworkSubmission.model_validate(submission_in)
    session.add(db_submission)
    session.commit()
    session.refresh(db_submission)
    return db_submission


def create_class_log(session: Session, log_in: ClassLogCreate) -> ClassLog:
    """Add the day's log for a class-section (one per section per day)."""
    db_log = ClassLog.model_validate(log_in)
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


def get_class_log_by_section(session: Session, section_id: UUID) -> list[ClassLog]:
    statement = (
        select(ClassLog)
        .where(ClassLog.section_id == section_id)
        .order_by(ClassLog.date.desc())
    )
    return list(session.exec(statement).all())


def get_all_homework(session: Session) -> list[HomeworkAssignment]:
    return list(
        session.exec(
            select(HomeworkAssignment).order_by(HomeworkAssignment.due_date.desc())
        ).all()
    )


def get_all_submissions(session: Session) -> list[HomeworkSubmission]:
    return list(session.exec(select(HomeworkSubmission).order_by(HomeworkSubmission.id)).all())


def get_all_class_logs(session: Session) -> list[ClassLog]:
    return list(session.exec(select(ClassLog).order_by(ClassLog.date.desc())).all())
