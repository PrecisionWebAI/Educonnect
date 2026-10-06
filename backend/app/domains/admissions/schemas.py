import datetime
from typing import Literal

from pydantic import BaseModel

from .models import AdmissionApplicationBase


class AdmissionApplicationCreate(AdmissionApplicationBase):
    """Body accepted by the Admission form.

    Every field is optional on purpose: the same endpoint stores a half-filled
    draft *and* a completed registration. `application_no` is assigned by the
    server when the client does not send one.
    """


class SeparationRecordRead(BaseModel):
    """The separation block as one object (see `AdmissionApplication.separation`)."""

    dropped_class: str | None = None
    reason: str | None = None
    session: str | None = None
    # Annotated as `datetime.date`, not `date`: the field itself is called
    # `date`, and a bare `date | None` would be resolved against that field.
    date: datetime.date | None = None


class LoginCredential(BaseModel):
    """A login the server created (or reused) while registering an application.

    `password` is present **only** on the response that created the login: the
    plain value is never stored, so it can never be shown again.
    """

    role: Literal["student", "guardian"]
    full_name: str
    email: str
    password: str | None = None
    #: False when an existing login was reused (a parent's second child).
    created: bool = True


class PasswordResetRead(BaseModel):
    """A freshly minted first-time password, returned exactly once."""

    role: Literal["student", "guardian"]
    full_name: str
    email: str
    password: str


class AdmissionApplicationRead(AdmissionApplicationBase):
    id: int
    separation: SeparationRecordRead | None = None
    #: The records this application created (see AdmissionApplication).
    student_id: int | None = None
    student_user_id: int | None = None
    guardian_user_id: int | None = None
    promoted_at: datetime.datetime | None = None
    #: Filled on the response that registered the application, so the office can
    #: hand over the logins; null on every other read.
    credentials: list[LoginCredential] | None = None
    #: The logins this application created (emails only - the password is gone
    #: once it has been shown), so the Registered tab can show them and reset one.
    #: Named `*_login_email` because the form already carries contact emails.
    student_login_email: str | None = None
    guardian_login_email: str | None = None
    #: Set when the student could not be placed in a class (e.g. the form named a
    #: class the school does not have) - the student is still created.
    placement_note: str | None = None


class SeparationRecordWrite(BaseModel):
    """Body of `PUT /admissions/applications/{application_id}/separation`."""

    reason: str
    session: str
    date: datetime.date
    dropped_class: str | None = None


class AdmissionApplicationUpdate(AdmissionApplicationBase):
    """Body of `PUT /admissions/applications/{application_id}` (full row)."""


class AdmissionStatusUpdate(BaseModel):
    status: Literal["Draft", "Registered"]
    notes: str | None = None
