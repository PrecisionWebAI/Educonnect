from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    HiringCandidateCreate,
    HiringCandidateRead,
    HiringStatusUpdate,
    HiringSummary,
    StaffVacancyRead,
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
    """Adds a candidate; the server mints the `CAN-…` number."""
    return service.create_candidate(session=session, candidate_in=candidate_in)


@router.put("/candidates/{candidate_id}/status", response_model=HiringCandidateRead)
def update_candidate_status(
    candidate_id: int,
    status_in: HiringStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Moves a candidate along the pipeline; Hired assigns the employee id."""
    return service.update_status(
        session=session, candidate_id=candidate_id, status_in=status_in
    )


@router.get("/vacancies", response_model=list[StaffVacancyRead])
def read_vacancies(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The posts the school is hiring for."""
    return service.list_vacancies(session=session)


@router.get("/summary", response_model=HiringSummary)
def read_summary(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Counts for the screen's stat tiles (pipeline stages + open vacancies)."""
    return service.summary(session=session)
