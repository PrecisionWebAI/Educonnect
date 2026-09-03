from sqlmodel import Session, select

from .models import ClassDiary, HomeworkAssignment, HomeworkSubmission
from .schemas import (
    ClassDiaryCreate,
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


def get_homework_by_class(
    session: Session, class_id: int, section_id: int | None = None
) -> list[HomeworkAssignment]:
    query = select(HomeworkAssignment).where(
        HomeworkAssignment.grade_class_id == class_id
    )
    if section_id:
        query = query.where(
            (HomeworkAssignment.section_id == section_id)
            | (HomeworkAssignment.section_id == None)
        )
    return list(session.exec(query.order_by(HomeworkAssignment.due_date.desc())).all())


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


def create_diary_note(session: Session, diary_in: ClassDiaryCreate) -> ClassDiary:
    db_diary = ClassDiary.model_validate(diary_in)
    session.add(db_diary)
    session.commit()
    session.refresh(db_diary)
    return db_diary


def get_diary_by_student(session: Session, student_id: int) -> list[ClassDiary]:
    statement = (
        select(ClassDiary)
        .where(ClassDiary.student_id == student_id)
        .order_by(ClassDiary.date.desc())
    )
    return list(session.exec(statement).all())
