import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.core import contacts
from app.core.text import CanonicalRequest
from .models import AdmissionApplicationBase

#: A body that carries a field the server does **not** store is refused, not quietly
#: trimmed. The admission form used to post the father's and mother's phone and email
#: long after the server stopped having columns for them, and Pydantic's default
#: ("ignore what you do not know") made what the office typed vanish without a word.
#: `422` naming the field is the honest answer; the form itself no longer sends them.
_STRICT = ConfigDict(extra="forbid")


class AdmissionGuardianBlock(CanonicalRequest):
    """The **guardian block**: the person the form names as the child's contact.

    Deliberately *not* part of `AdmissionApplicationBase`: a guardian is their own
    row (`guardian`, joined to the child through `student_guardian_relationship`),
    shared with any siblings, so nothing about them is copied onto the student. This
    block is the form's way of naming them, which is why the three fields a family
    cannot be reached without - the name, the phone, the email - are required here.

    The email is required because it **is** the guardian's login; a phone is how the
    school rings the family, never what anybody signs in with.
    """

    guardian_name: str
    guardian_phone: str
    guardian_email: str
    guardian_relation: str | None = None
    guardian_occupation: str | None = None
    guardian_address: str | None = None


class AdmissionGuardianPatch(CanonicalRequest):
    """The same block on an **edit**, where leaving a field out means "leave it".

    The guardian has a card of their own (`academic/classroom/students/guardians.py`) and edits made
    there and here go through the same "one contact, one person" rule
    (`app/core/contacts.py`), so the admission form only touches what the office
    actually retyped on it.
    """

    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    guardian_relation: str | None = None
    guardian_occupation: str | None = None
    guardian_address: str | None = None


class AdmissionApplicationCreate(
    AdmissionApplicationBase, AdmissionGuardianBlock, CanonicalRequest
):
    """Body accepted by the Admission form.

    There is no draft: the form is saved **once**, and what it posts is a student
    the school admits - so the body carries the guardian block as well, and the
    server refuses a form that is missing what a student cannot be without
    (`REQUIRED_TO_ADMIT` in `service.py`). `admission_number` is assigned by the
    server when the client does not send one.
    """

    model_config = _STRICT


class SeparationRecordRead(BaseModel):
    """The separation block as one object (see `AdmissionApplication.separation`)."""

    dropped_class: str | None = None
    reason: str | None = None
    session: str | None = None
    # Annotated as `datetime.date`, not `date`: the field itself is called
    # `date`, and a bare `date | None` would be resolved against that field.
    date: datetime.date | None = None


class LoginCredential(BaseModel):
    """A login the server created (or reused) while admitting an application.

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


#: The popup payload is owned by the rule module (`app/core/contacts.py`): every form
#: that captures a contact - admission, hire, interview - shows the same one, so the
#: schema lives with the rule instead of being copied per domain.
ContactChildRead = contacts.ContactChildRead
ContactLookupRead = contacts.ContactLookupRead


class AdmissionApplicationRead(AdmissionApplicationBase):
    """One student, as the admission screens show them.

    The row holds the student; the **guardian block is read back from the person**
    (the primary `guardian` of this child), because that is where it lives now - a
    family's second child repeats the same contact without repeating the row.
    """

    id: UUID
    separation: SeparationRecordRead | None = None
    #: The student this row is - its own id. Kept as a field because the screens
    #: address the directory by `student_id` (View, Logins, Delete).
    student_id: UUID | None = None
    student_user_id: UUID | None = None
    guardian_user_id: UUID | None = None
    #: Filled on the response that created the student, so the office can hand over
    #: the logins; null on every other read.
    credentials: list[LoginCredential] | None = None
    #: The logins this student has (emails only - the password is gone once it has
    #: been shown), so the table can show them and reset one.
    #: Named `*_login_email` because the guardian block already carries contacts.
    student_login_email: str | None = None
    guardian_login_email: str | None = None
    #: Set when the student could not be placed in a class (e.g. the form named a
    #: class the school does not have) - the student is still created.
    placement_note: str | None = None

    # ---- the guardian block, read from the person --------------------------
    guardian_name: str | None = None
    guardian_relation: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    guardian_occupation: str | None = None
    guardian_address: str | None = None


class SeparationRecordWrite(CanonicalRequest):
    """Body of `PUT /admissions/applications/{application_id}/separation`."""

    reason: str
    session: str
    date: datetime.date
    dropped_class: str | None = None


class AdmissionApplicationUpdate(
    AdmissionApplicationBase, AdmissionGuardianPatch, CanonicalRequest
):
    """Body of `PUT /admissions/applications/{application_id}` (full row)."""

    model_config = _STRICT
