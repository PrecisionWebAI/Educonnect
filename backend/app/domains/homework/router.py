from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ClassDiaryCreate,
    ClassDiaryRead,
    DiaryEntryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionCreate,
    HomeworkSubmissionRead,
    SubmissionItemRead,
)

router = APIRouter()

# Removed StaffRoles


@router.post(
    "", response_model=HomeworkAssignmentRead, status_code=status.HTTP_201_CREATED
)
def create_homework(
    homework_in: HomeworkAssignmentCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.create")),
):
    """
    Teacher assigns homework.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    # Verify Teacher is assigned to the subject/class
    if not AuthorizationService.can(
        current_user,
        "homework.create",
        session=session,
        class_id=homework_in.classroom_id,
        subject_id=homework_in.subject_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create homework for this class/subject.",
        )

    return service.create_homework(session=session, homework_in=homework_in)


@router.get("/class/{class_id}", response_model=list[HomeworkAssignmentRead])
def read_homework_by_class(
    class_id: int,
    section_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
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
    current_user=Depends(RequirePermission("homework.submit")),
):
    """
    Student submits homework or marks it as done.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    if not AuthorizationService.can(
        current_user,
        "homework.submit",
        session=session,
        student_id=submission_in.student_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to submit homework for this student.",
        )

    return service.submit_homework(session=session, submission_in=submission_in)


@router.post(
    "/diary", response_model=ClassDiaryRead, status_code=status.HTTP_201_CREATED
)
def create_diary_note(
    diary_in: ClassDiaryCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.create")),
):
    """
    Add a diary note for a class.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    if not AuthorizationService.can(
        current_user,
        "diary.create",
        session=session,
        class_id=diary_in.classroom_id,
        subject_id=diary_in.subject_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create diary entry for this class/subject.",
        )

    return service.create_diary_note(session=session, diary_in=diary_in)


@router.get("/diary/student/{student_id}", response_model=list[ClassDiaryRead])
def read_diary_notes(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    """
    Fetch diary notes for a student.
    """
    return service.get_diary_by_student(session=session, student_id=student_id)


@router.get("", response_model=list[HomeworkAssignmentRead])
def read_all_homework(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return service.list_homework(session=session)


@router.get("/submissions", response_model=list[SubmissionItemRead])
def read_submissions(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return service.list_submissions(session=session)


@router.get("/diary", response_model=list[DiaryEntryRead])
def read_diary(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    return service.list_diary(session=session)
