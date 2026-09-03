from fastapi import HTTPException
from sqlmodel import Session

from app.domains.students import repository as student_repository

from . import repository
from .models import ClassDiary, HomeworkAssignment, HomeworkSubmission
from .schemas import (
    ClassDiaryCreate,
    HomeworkAssignmentCreate,
    HomeworkSubmissionCreate,
)


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> HomeworkAssignment:
    return repository.create_homework(session, homework_in)


def get_homework_by_class(
    session: Session, class_id: int, section_id: int | None = None
) -> list[HomeworkAssignment]:
    return repository.get_homework_by_class(session, class_id, section_id)


def submit_homework(
    session: Session, submission_in: HomeworkSubmissionCreate
) -> HomeworkSubmission:
    # Ensure student exists
    student = student_repository.get_student_by_id(session, submission_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return repository.create_or_update_submission(session, submission_in)


def create_diary_note(session: Session, diary_in: ClassDiaryCreate) -> ClassDiary:
    student = student_repository.get_student_by_id(session, diary_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return repository.create_diary_note(session, diary_in)


def get_diary_by_student(session: Session, student_id: int) -> list[ClassDiary]:
    return repository.get_diary_by_student(session, student_id)
