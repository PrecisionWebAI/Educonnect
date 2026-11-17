"""The Homework board's HTTP surface.

Paths (Phase 9 added the last three):

* `POST /homework` - assign, and tell the class-section;
* `GET /homework` / `GET /homework/section/{id}` - the board;
* `POST /homework/submit` - the child hands work in (`submitted_at`, `is_late`);
* `GET /homework/submissions?section_id=` - the review board, pending rows included;
* `POST /homework/submissions/{id}/feedback` - grade it (score, remark, `graded_at`);
* `POST /homework/diary` - write the day's line, with its period and subject;
* `GET /homework/diary` / `GET /homework/diary/section/{id}` - the diary.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission
from app.domains.auth.service import AuthorizationService

from . import service
from .schemas import (
    ClassLogCreate,
    ClassLogRead,
    DiaryEntryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionRead,
    SubmissionFeedbackIn,
    SubmissionItemRead,
    SubmissionSubmitIn,
)

router = APIRouter()


def _class_id_for_section(session: Session, section_id: UUID) -> UUID | None:
    """The class a class-section belongs to - what the scope check needs.

    Homework and the class log name only the section; the scope rules still reason
    about the class, so the class is resolved here rather than stored.
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
    """A teacher assigns homework to one class-section."""
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
    """Homework set for one class-section, with the "3/4 in" count."""
    return service.get_homework_by_section(session=session, section_id=section_id)


@router.post(
    "/submit",
    response_model=HomeworkSubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_homework(
    submission_in: SubmissionSubmitIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.submit")),
):
    """A student (or a guardian on their behalf) hands work in."""
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
    "/submissions/{submission_id}/feedback",
    response_model=SubmissionItemRead,
)
def grade_submission(
    submission_id: UUID,
    feedback_in: SubmissionFeedbackIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.review")),
):
    """Record a score and/or a remark on one submission, and tell the family."""
    return service.grade_submission(
        session=session,
        submission_id=submission_id,
        feedback_in=feedback_in,
        user=current_user,
    )


@router.post("/diary", response_model=ClassLogRead, status_code=status.HTTP_201_CREATED)
def create_class_log(
    log_in: ClassLogCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.create")),
):
    """Write one line of a class-section's day (period and subject included)."""
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

    return service.create_class_log(session=session, log_in=log_in, user=current_user)


@router.get("/diary/section/{section_id}", response_model=list[ClassLogRead])
def read_class_log(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    """The raw log lines for one class-section, newest first."""
    return service.get_class_log_by_section(session=session, section_id=section_id)


@router.get("", response_model=list[HomeworkAssignmentRead])
def read_all_homework(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return service.list_homework(session=session)


@router.get("/submissions", response_model=list[SubmissionItemRead])
def read_submissions(
    section_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    """The review board - narrowed to one class-section when one is named."""
    return service.list_submissions(session=session, section_id=section_id)


@router.get("/diary", response_model=list[DiaryEntryRead])
def read_diary(
    section_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    return service.list_diary(session=session, section_id=section_id)
