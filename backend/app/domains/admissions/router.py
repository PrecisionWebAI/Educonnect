from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionApplicationUpdate,
    ContactLookupRead,
    PasswordResetRead,
    SeparationRecordWrite,
)

router = APIRouter()

# Front-desk staff take applications, so `admissions.manage` (not
# `students.create`) guards the write endpoints.
_can_read = RequirePermission("admissions.read")
_can_manage = RequirePermission("admissions.manage")


# ---------------------------------------------------------------------------
# Operations > Admission screen (the student rows)
# ---------------------------------------------------------------------------


@router.get("/applications", response_model=list[AdmissionApplicationRead])
def read_applications(
    skip: int = 0,
    limit: int = 500,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every student, newest first - there is no draft, so nothing is filtered out.

    The default limit covers a whole school: the screen paginates and filters on the
    client, and a limit below the roll silently hides students.
    """
    return service.get_applications(session=session, skip=skip, limit=limit)


@router.post("/applications", response_model=AdmissionApplicationRead, status_code=201)
def create_application(
    application_in: AdmissionApplicationCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Admit a student: the row, their guardian, the link and the logins, at once.

    The form is saved **once** and complete - the server mints the admission number
    and refuses a form that is missing what a student cannot be without (`422`), so
    nothing half-admitted is ever stored. The response carries the logins (with their
    first-time passwords) that the form's own emails made.
    """
    return service.create_application(session=session, application_in=application_in)


@router.put("/applications/{application_id}", response_model=AdmissionApplicationRead)
def update_application(
    application_id: UUID,
    application_in: AdmissionApplicationUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Writes the whole form back (correct a student, or the family's contact)."""
    return service.update_application(
        session=session, application_id=application_id, application_in=application_in
    )


@router.put(
    "/applications/{application_id}/separation",
    response_model=AdmissionApplicationRead,
)
def record_separation(
    application_id: UUID,
    separation_in: SeparationRecordWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Records why/when a student left; the row then reports as Inactive."""
    return service.record_separation(
        session=session, application_id=application_id, separation_in=separation_in
    )


# ---------------------------------------------------------------------------
# The public form + the form's popup
# ---------------------------------------------------------------------------


@router.get("/contact-lookup", response_model=ContactLookupRead)
def contact_lookup(
    phone: str | None = None,
    email: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Who a phone number or an email already belongs to - the form's popup.

    The admission form asks this when the office leaves the guardian's phone or email
    field. A hit means the family is already on file: their details can be filled in
    and the new child linked to them, instead of a second row being made for the same
    parent. A contact that belongs to somebody else is **refused when the form is
    saved** (`409`), which is why the form asks before the office gets that far.
    """
    return service.contact_lookup(session=session, phone=phone, email=email)


@router.post("/apply", response_model=AdmissionApplicationRead, status_code=201)
def apply_for_admission(
    application_in: AdmissionApplicationCreate,
    session: Session = Depends(get_session),
):
    """Public endpoint for parents to submit an application (no login).

    It saves exactly what the office screen saves - a complete form, and therefore a
    student - because there is no draft to hold a half-filled one. The logins are
    created, but their passwords are **not** echoed back here (the caller is
    anonymous), so the office hands them over from the Admission screen.
    """
    read = service.create_application(session=session, application_in=application_in)
    read.credentials = None
    return read


@router.get("", response_model=list[AdmissionApplicationRead])
def read_application_queue(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Admin view of the admission queue (same rows as `/applications`)."""
    return service.get_applications(session=session, skip=skip, limit=limit)


@router.post(
    "/applications/{application_id}/reset-login", response_model=PasswordResetRead
)
def reset_login(
    application_id: UUID,
    target: Literal["student", "guardian"] = "student",
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Give the student or the guardian a new first-time password.

    Returns it once; only the hash is stored, so it can never be read back.
    """
    return service.reset_login_password(
        session=session, application_id=application_id, target=target
    )
