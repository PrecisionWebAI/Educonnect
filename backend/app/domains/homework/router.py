from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    ClassDiaryCreate,
    ClassDiaryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionCreate,
    HomeworkSubmissionRead,
)

router = APIRouter()

StaffRoles = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director, RoleEnum.teacher]
)


@router.post(
    "", response_model=HomeworkAssignmentRead, status_code=status.HTTP_201_CREATED
)
def create_homework(
    homework_in: HomeworkAssignmentCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Teacher assigns homework.
    """
    return service.create_homework(session=session, homework_in=homework_in)


@router.get("/class/{class_id}", response_model=list[HomeworkAssignmentRead])
def read_homework_by_class(
    class_id: int,
    section_id: int | None = None,
    session: Session = Depends(get_session),
):
    """
    Fetch homework for a class board.
    """
    return service.get_homework_by_class(
        session=session, class_id=class_id, section_id=section_id
    )


@router.post(
    "/submit",
    response_model=HomeworkSubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_homework(
    submission_in: HomeworkSubmissionCreate,
    session: Session = Depends(get_session),
    # Could protect this so only the student or teacher can modify
):
    """
    Student submits homework or marks it as done.
    """
    return service.submit_homework(session=session, submission_in=submission_in)


@router.post(
    "/diary", response_model=ClassDiaryRead, status_code=status.HTTP_201_CREATED
)
def create_diary_note(
    diary_in: ClassDiaryCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Add a diary note for a student.
    """
    return service.create_diary_note(session=session, diary_in=diary_in)


@router.get("/diary/student/{student_id}", response_model=list[ClassDiaryRead])
def read_diary_notes(student_id: int, session: Session = Depends(get_session)):
    """
    Fetch diary notes for a student.
    """
    return service.get_diary_by_student(session=session, student_id=student_id)
