from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.core import contacts
from app.core.db import get_session
from app.core.contacts import ContactLookupRead
from app.domains.auth.dependencies import RequirePermission
from app.domains.users.models import User

from . import service
from .schemas import (
    HiringCandidateCreate,
    HiringCandidateRead,
    HiringStatusUpdate,
    HiringSummary,
    InterviewScheduleUpdate,
)

router = APIRouter()

_can_read = RequirePermission("hiring.read")
_can_manage = RequirePermission("hiring.manage")
@router.get("/candidates", response_model=list[HiringCandidateRead])
def read_candidates(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every candidate in the pipeline, newest first."""
    return service.list_candidates(session=session)


@router.post("/candidates", response_model=HiringCandidateRead, status_code=201)
def create_candidate(
    candidate_in: HiringCandidateCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Registers a person for an interview; the server mints the `CAN-…` number."""
    return service.create_candidate(session=session, candidate_in=candidate_in)


@router.put(
    "/candidates/{candidate_id}/interview", response_model=HiringCandidateRead
)
def schedule_candidate_interview(
    candidate_id: UUID,
    schedule_in: InterviewScheduleUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Set / change a candidate's interview date+time."""
    return service.schedule_interview(
        session=session, candidate_id=candidate_id, schedule_in=schedule_in
    )


@router.put("/candidates/{candidate_id}/status", response_model=HiringCandidateRead)
def update_candidate_status(
    candidate_id: UUID,
    status_in: HiringStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Moves a candidate along the pipeline. `Hired` is rejected here: a hire is
    made by the registration form (`POST /staff/profiles`), which creates the
    employee record and the login, and marks the candidate Hired itself."""
    return service.update_status(
        session=session, candidate_id=candidate_id, status_in=status_in
    )


@router.post("/candidates/{candidate_id}/resume", response_model=HiringCandidateRead)
def upload_candidate_resume(
    candidate_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_can_manage),
    file: UploadFile = File(...),
):
    """Attaches a candidate's resume (PDF / Word / image)."""
    return service.save_resume(
        session=session,
        candidate_id=candidate_id,
        file=file,
        school_id=current_user.school_id,
    )


@router.get("/candidates/{candidate_id}/resume")
def download_candidate_resume(
    candidate_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Serves the resume a candidate uploaded."""
    from pathlib import Path

    candidate = service._get_or_404(session, candidate_id)
    if not candidate.resume_path or not Path(candidate.resume_path).exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(path=candidate.resume_path, media_type="application/octet-stream")


@router.get("/contact-lookup", response_model=ContactLookupRead)
def contact_lookup(
    phone: str | None = None,
    email: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Who a phone number or an email already belongs to - the hire form's popup.

    Same payload as the admission form's lookup (`app/core/contacts.py`): a hit means
    the person is already on file - a parent who is now applying to teach, or somebody
    already in the pipeline - so the form offers their details instead of asking for
    them again. A contact that belongs to **somebody else** is refused when the hire or
    the interview is saved.
    """
    return contacts.contact_read(session=session, phone=phone, email=email)


@router.get("/summary", response_model=HiringSummary)
def read_summary(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Counts for the screen's stat tiles (pipeline stages)."""
    return service.summary(session=session)
