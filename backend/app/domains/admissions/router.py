from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionStatusUpdate,
)

router = APIRouter()

AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)


@router.post(
    "/apply",
    response_model=AdmissionApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_for_admission(
    application_in: AdmissionApplicationCreate, session: Session = Depends(get_session)
):
    """
    Public endpoint for parents to submit applications.
    """
    return service.create_application(session=session, application_in=application_in)


@router.get("", response_model=list[AdmissionApplicationRead])
def read_applications(
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Admin endpoint to view the application queue.
    """
    return service.get_applications(
        session=session, status=status, skip=skip, limit=limit
    )


@router.put("/{application_id}/status", response_model=AdmissionApplicationRead)
def update_application_status(
    application_id: int,
    status_update: AdmissionStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Admin endpoint to approve/reject. If approved, the service layer will automatically provision a User account and StudentProfile.
    """
    return service.update_application_status(
        session=session, application_id=application_id, status_update=status_update
    )
