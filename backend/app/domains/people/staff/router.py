"""Staff (employee) API - the Staff Hiring screen's hire + Hired tab."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import lifecycle, service
from .schemas import (
    LifecycleRequest,
    StaffLifecycleRead,
    StaffPasswordResetRead,
    StaffProfileCreate,
    StaffProfileCreateRead,
    StaffProfileRead,
)

router = APIRouter()

_can_read = RequirePermission("hiring.read")
_can_manage = RequirePermission("hiring.manage")


@router.post("/profiles", response_model=StaffProfileCreateRead, status_code=201)
def create_profile(
    profile_in: StaffProfileCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Fill the hire form -> creates the login + `employee` record in one step.

    The response carries the login once, with its first-time password - that is
    the only time it is ever visible.
    """
    return service.create_profile(session=session, profile_in=profile_in)


@router.put("/profiles/{profile_id}", response_model=StaffProfileRead)
def update_profile(
    profile_id: UUID,
    profile_in: StaffProfileCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Edit an existing employee's record (the Hired tab's Edit action)."""
    return service.update_profile(
        session=session, profile_id=profile_id, profile_in=profile_in
    )


@router.get("/profiles", response_model=list[StaffProfileRead])
def read_profiles(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The staff the school has hired - the Hired tab (one row per employee)."""
    return service.list_profiles(session=session)


@router.post(
    "/profiles/{profile_id}/reset-login", response_model=StaffPasswordResetRead
)
def reset_profile_login(
    profile_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Mint a fresh first-time password for a hired staff member."""
    return service.reset_login_password(session=session, profile_id=profile_id)


@router.post("/profiles/{profile_id}/deactivate", response_model=StaffLifecycleRead)
def deactivate_profile(
    profile_id: UUID,
    payload: LifecycleRequest | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Take the staff side of this person off (the Hired tab's "Deactivate").

    Nothing is deleted: their roles are withdrawn and remembered, the day they left is
    stamped and their staff access is gone at once. Their login is only switched off if
    it opened nothing else - a teacher who is also a parent keeps signing in.
    """
    return lifecycle.deactivate_profile(
        session=session, profile_id=profile_id, payload=payload
    )


@router.post("/profiles/{profile_id}/reactivate", response_model=StaffLifecycleRead)
def reactivate_profile(
    profile_id: UUID,
    payload: LifecycleRequest | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Put them back on the staff roll, with exactly the roles they had."""
    return lifecycle.reactivate_profile(
        session=session, profile_id=profile_id, payload=payload
    )


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(
    profile_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Remove a hired employee (only for a record the school never really had).

    Their own rows go; anything with history behind it refuses with `409`, and the
    answer says to deactivate instead. A login that still opens something else stays.
    """
    lifecycle.delete_profile(session=session, profile_id=profile_id)
