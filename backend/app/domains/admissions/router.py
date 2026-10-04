from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionApplicationUpdate,
    AdmissionStatusUpdate,
    SeparationRecordWrite,
)

router = APIRouter()

# Front-desk staff take applications, so `admissions.manage` (not
# `students.create`) guards the write endpoints.
_can_read = RequirePermission("admissions.read")
_can_manage = RequirePermission("admissions.manage")


# ---------------------------------------------------------------------------
# Operations > Admission screen (full application rows)
# ---------------------------------------------------------------------------


@router.get("/applications", response_model=list[AdmissionApplicationRead])
def read_applications(
    status: str | None = None,
    skip: int = 0,
    limit: int = 500,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every application, newest first (`?status=Draft|Registered` to narrow)."""
    return service.get_applications(
        session=session, status=status, skip=skip, limit=limit
    )


@router.post("/applications", response_model=AdmissionApplicationRead, status_code=201)
def create_application(
    application_in: AdmissionApplicationCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Saves a draft or registers a student; the server assigns the form number."""
    return service.create_application(session=session, application_in=application_in)


@router.put("/applications/{application_id}", response_model=AdmissionApplicationRead)
def update_application(
    application_id: int,
    application_in: AdmissionApplicationUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Writes the whole form back (edit a registered student, finish a draft)."""
    return service.update_application(
        session=session, application_id=application_id, application_in=application_in
    )


@router.put(
    "/applications/{application_id}/separation",
    response_model=AdmissionApplicationRead,
)
def record_separation(
    application_id: int,
    separation_in: SeparationRecordWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Records why/when a student left; the row then reports as Inactive."""
    return service.record_separation(
        session=session, application_id=application_id, separation_in=separation_in
    )


# ---------------------------------------------------------------------------
# Public form + legacy funnel endpoints (kept working)
# ---------------------------------------------------------------------------


@router.post("/apply", response_model=AdmissionApplicationRead, status_code=201)
def apply_for_admission(
    application_in: AdmissionApplicationCreate,
    session: Session = Depends(get_session),
):
    """Public endpoint for parents to submit an application (no login)."""
    return service.create_application(session=session, application_in=application_in)


@router.get("", response_model=list[AdmissionApplicationRead])
def read_application_queue(
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Admin view of the application queue (same rows as `/applications`)."""
    return service.get_applications(
        session=session, status=status, skip=skip, limit=limit
    )


@router.put("/{application_id}/status", response_model=AdmissionApplicationRead)
def update_application_status(
    application_id: int,
    status_update: AdmissionStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Move an application between Draft and Registered."""
    return service.update_application_status(
        session=session, application_id=application_id, status_update=status_update
    )
