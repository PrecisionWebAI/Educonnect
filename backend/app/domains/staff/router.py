"""Staff registration API - the Staff Hiring screen's Registration tab."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    StaffPasswordResetRead,
    StaffProfileRead,
    StaffRegistrationCreate,
    StaffRegistrationRead,
)

router = APIRouter()

_can_read = RequirePermission("hiring.read")
_can_manage = RequirePermission("hiring.manage")


@router.get("/registrations", response_model=list[StaffRegistrationRead])
def read_registrations(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every hire-registration, newest first."""
    return service.list_registrations(session=session)


@router.post("/registrations", response_model=StaffRegistrationRead, status_code=201)
def create_registration(
    registration_in: StaffRegistrationCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Register a hire: creates the login + staff record in one step.

    The response carries the login once, with its first-time password - that is
    the only time it is ever visible.
    """
    return service.create_registration(session=session, registration_in=registration_in)


@router.get("/profiles", response_model=list[StaffProfileRead])
def read_profiles(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The staff the school has hired - the Hired tab."""
    return service.list_profiles(session=session)


@router.post(
    "/profiles/{profile_id}/reset-login", response_model=StaffPasswordResetRead
)
def reset_profile_login(
    profile_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Mint a fresh first-time password for a hired staff member."""
    return service.reset_login_password(session=session, profile_id=profile_id)
