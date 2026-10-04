"""Admission service - the Operations > Admission workflow.

Reads and writes `admissionapplication`. Three things here are more than plain
CRUD:

* `application_no` is minted server-side (`ADM-2026-0141`) so two open forms in
  two browsers can never claim the same number.
* A row is either a **draft** (half-filled, still editable) or **registered**
  (the student is on the rolls).
* A **separation** records why and when a registered student left. The row is
  then reported as Inactive - derived from the separation block itself rather
  than stored as a second flag that could disagree with it.

Registering does **not** create the student's login: an application is a
request, and turning it into `user` + `studentprofile` records is a separate
step (`POST /users`, `POST /students`). That is what keeps the public
`POST /admissions/apply` form incapable of creating accounts.
"""

from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import STATUS_REGISTERED, AdmissionApplication
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionApplicationUpdate,
    AdmissionStatusUpdate,
    SeparationRecordWrite,
)

# Fields the server owns: a full-row update must never blank them out (neither
# with `null` nor with an empty string).
_SERVER_MANAGED = ("application_no", "created_on")


def _read(application: AdmissionApplication) -> AdmissionApplicationRead:
    """ORM row -> response model, folding the four separation columns together."""
    return AdmissionApplicationRead.model_validate(
        {**application.model_dump(), "separation": application.separation}
    )


def _get_or_404(session: Session, application_id: int) -> AdmissionApplication:
    application = repository.get_application_by_id(session, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def get_applications(
    session: Session, status: str | None = None, skip: int = 0, limit: int = 500
) -> list[AdmissionApplicationRead]:
    return [
        _read(row) for row in repository.get_applications(session, status, skip, limit)
    ]


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplicationRead:
    if not application_in.application_no:
        application_in.application_no = repository.next_application_no(session)
    return _read(repository.create_application(session, application_in))


def update_application(
    session: Session,
    application_id: int,
    application_in: AdmissionApplicationUpdate,
) -> AdmissionApplicationRead:
    application = _get_or_404(session, application_id)
    for field, value in application_in.model_dump(exclude_unset=True).items():
        if field in _SERVER_MANAGED and not value:
            continue
        setattr(application, field, value)
    return _read(repository.save_application(session, application))


def record_separation(
    session: Session,
    application_id: int,
    separation_in: SeparationRecordWrite,
) -> AdmissionApplicationRead:
    application = _get_or_404(session, application_id)
    application.separation_reason = separation_in.reason
    application.separation_session = separation_in.session
    application.separation_date = separation_in.date
    if separation_in.dropped_class:
        application.separation_dropped_class = separation_in.dropped_class
    return _read(repository.save_application(session, application))


def update_application_status(
    session: Session,
    application_id: int,
    status_update: AdmissionStatusUpdate,
) -> AdmissionApplicationRead:
    """Move a row between Draft and Registered (legacy funnel endpoint)."""
    application = _get_or_404(session, application_id)
    application.status = status_update.status
    if status_update.notes:
        application.notes = status_update.notes
    return _read(repository.save_application(session, application))


def is_registered(application: AdmissionApplication) -> bool:
    return application.status == STATUS_REGISTERED
