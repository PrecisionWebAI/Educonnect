from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ClassLogCreate,
    ClassLogRead,
    DiaryEntryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionCreate,
    HomeworkSubmissionRead,
    SubmissionItemRead,
)

router = APIRouter()


def _class_id_for_section(session: Session, section_id: UUID) -> UUID | None:
    """The class a class-section belongs to - what the scope check needs.

    Homework and the class log name only the section now; the scope rules still
    reason about the class, so the class is resolved here rather than stored.
    """
    from app.domains.academic.classroom.academics.models import Section

    section = session.get(Section, section_id)
    return section.class_id if section else None


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
        class_id=_class_id_for_section(session, homework_in.section_id),
        subject_id=homework_in.subject_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create homework for this class/subject.",
        )

    return service.create_homework(session=session, homework_in=homework_in)


@router.get("/section/{section_id}", response_model=list[HomeworkAssignmentRead])
def read_homework_by_section(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    """Homework set for one class-section."""
    return service.get_homework_by_section(session=session, section_id=section_id)


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
    "/diary", response_model=ClassLogRead, status_code=status.HTTP_201_CREATED
)
def create_class_log(
    log_in: ClassLogCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.create")),
):
    """Write the day's log for a class-section (one entry per section per day)."""
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    if not AuthorizationService.can(
        current_user,
        "diary.create",
        session=session,
        class_id=_class_id_for_section(session, log_in.section_id),
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to write the log for this class-section.",
        )

    return service.create_class_log(session=session, log_in=log_in)


@router.get("/diary/section/{section_id}", response_model=list[ClassLogRead])
def read_class_log(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    """The class log for one class-section, newest first."""
    return service.get_class_log_by_section(session=session, section_id=section_id)


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
