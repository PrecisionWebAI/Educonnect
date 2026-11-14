"""The shapes the profile drawer reads and writes.

Two conventions, both inherited from the hub:

* a fact that may not exist is `None`, never a stand-in (`grade: str | None`, not
  `""`), so the drawer can print "—" instead of inventing a value;
* a *fixed vocabulary* is a `Literal`, which serves two purposes at once - the
  set of words is closed (the API cannot grow a sixth employment event the screen
  has no label for) and `CanonicalRequest` leaves it alone, so "Designation
  changed" keeps its capitals instead of being stored as "designation changed".

Writes go through `CanonicalRequest` (text stored in canonical form, phone
numbers reduced to ten digits) like every other request body in the product.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest

#: The events the employment history records. `Joined` and `Left` bracket a
#: person's time here; the other three are the changes a salary or a seniority
#: claim is argued from.
EmploymentEvent = Literal[
    "Joined",
    "Promoted",
    "Transferred",
    "Designation changed",
    "Left",
]

#: The employment types payroll prints. A closed list, unlike `department`.
EmploymentType = Literal["Full-time", "Part-time", "Contract", "Guest"]


# --- qualifications -------------------------------------------------------


class QualificationCreate(CanonicalRequest):
    degree: str = Field(min_length=1, max_length=120)
    institution: str | None = Field(default=None, max_length=160)
    year_completed: int | None = Field(default=None, ge=1900, le=2100)
    grade: str | None = Field(default=None, max_length=40)


class QualificationUpdate(CanonicalRequest):
    """Every field optional: a PATCH says what changed, not what is true.

    `exclude_unset` is what the service applies, so omitting `institution` leaves
    it alone while sending `null` clears it - the two are different requests.
    """

    degree: str | None = Field(default=None, min_length=1, max_length=120)
    institution: str | None = Field(default=None, max_length=160)
    year_completed: int | None = Field(default=None, ge=1900, le=2100)
    grade: str | None = Field(default=None, max_length=40)


class QualificationRead(BaseModel):
    id: UUID
    degree: str
    institution: str | None = None
    year_completed: int | None = None
    grade: str | None = None


# --- experience -----------------------------------------------------------


class ExperienceCreate(CanonicalRequest):
    employer: str = Field(min_length=1, max_length=160)
    designation: str | None = Field(default=None, max_length=120)
    from_date: date
    #: NULL means "still working there".
    to_date: date | None = None
    note: str | None = None


class ExperienceUpdate(CanonicalRequest):
    employer: str | None = Field(default=None, min_length=1, max_length=160)
    designation: str | None = Field(default=None, max_length=120)
    from_date: date | None = None
    to_date: date | None = None
    note: str | None = None


class ExperienceRead(BaseModel):
    id: UUID
    employer: str
    designation: str | None = None
    from_date: date
    to_date: date | None = None
    note: str | None = None


# --- certifications -------------------------------------------------------


class CertificationCreate(CanonicalRequest):
    name: str = Field(min_length=1, max_length=160)
    issuer: str | None = Field(default=None, max_length=160)
    issued_on: date | None = None
    valid_till: date | None = None
    reference_no: str | None = Field(default=None, max_length=80)


class CertificationUpdate(CanonicalRequest):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    issuer: str | None = Field(default=None, max_length=160)
    issued_on: date | None = None
    valid_till: date | None = None
    reference_no: str | None = Field(default=None, max_length=80)


class CertificationRead(BaseModel):
    id: UUID
    name: str
    issuer: str | None = None
    issued_on: date | None = None
    valid_till: date | None = None
    reference_no: str | None = None


# --- history --------------------------------------------------------------


class HistoryRead(BaseModel):
    """One employment event. Read-only: the history is append-only."""

    id: UUID
    event: str
    effective_on: date
    from_value: str | None = None
    to_value: str | None = None
    note: str | None = None
    #: The name of whoever recorded it, or None when no login is credited.
    recorded_by: str | None = None
    created_at: datetime | None = None


# --- the post -------------------------------------------------------------


class EmploymentUpdate(CanonicalRequest):
    """The employee columns the profile's Overview edits.

    Deliberately **not** the person's name, department or employee code: those are
    the hire record (`people/staff`), and editing them from a profile drawer would
    give one fact two owners.
    """

    designation: str | None = Field(default=None, max_length=120)
    employment_type: EmploymentType | None = None
    probation_end: date | None = None
    reports_to_employee_id: UUID | None = None


class SubjectsUpdate(CanonicalRequest):
    """Replace the teacher's subject list (the whole list, not a delta)."""

    subject_ids: list[UUID] = Field(default_factory=list)


# --- documents -------------------------------------------------------------
#
# The read has **no path and no key**. `storage_key` is server-side plumbing: a
# response that carried it would hand out the dossier folder's layout, and a
# client could then ask for a file it was never granted. The drawer addresses a
# document by its row id and the download route resolves the file itself.


class DocumentRead(BaseModel):
    id: UUID
    #: One of `labels.DOC_TYPES` (`aadhaar`, `degree`, …).
    doc_type: str
    #: The screen's word for `doc_type` (`Aadhaar Card`), so the drawer does not
    #: carry a second copy of the vocabulary.
    doc_type_label: str = ""
    title: str | None = None
    file_name: str
    content_type: str | None = None
    size_bytes: int = 0
    #: The date somebody with `teachers.update` saw the original; `None` = pending.
    verified_on: date | None = None
    verified_by: str | None = None
    uploaded_by: str | None = None
    created_at: datetime | None = None


class DocumentVerify(CanonicalRequest):
    """Mark a document as seen (or un-see it, when the scan was the wrong paper)."""

    verified: bool = True
    note: str | None = Field(default=None, max_length=400)


class KycRead(BaseModel):
    """Aadhaar / PAN / bank detail, **masked unless it was asked for and allowed**.

    `masked` is what the drawer keys on: it never has to guess whether
    ``XXXX XXXX 9012`` is a mask or a value somebody typed. `can_reveal` says
    whether this caller may ask for the full one, so the "Show full" control is
    not a button that always fails.
    """

    aadhaar_no: str | None = None
    pan_no: str | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    ifsc: str | None = None
    masked: bool = True
    can_reveal: bool = False


# --- the audit trail -------------------------------------------------------


class AuditRead(BaseModel):
    """One line of who changed what. Append-only: nothing here is edited."""

    id: UUID
    employee_id: UUID
    #: The person's name, so the school-wide feed does not print an id.
    employee_name: str = ""
    section: str
    action: str
    row_id: UUID | None = None
    summary: str
    changed_by: str | None = None
    created_at: datetime | None = None


# --- everything the drawer reads at once -----------------------------------


class ProfileLists(BaseModel):
    """The inner tabs' lists, read in a fixed number of statements.

    One object rather than five endpoints for the drawer to join: a profile
    opened from the directory needs all of it at once, and five round trips
    would let the tabs disagree while they load. `documents` arrives with them
    for the same reason - and without a key or a path, so the list cannot be
    used to fetch a file the caller was not granted.
    """

    qualifications: list[QualificationRead] = Field(default_factory=list)
    experiences: list[ExperienceRead] = Field(default_factory=list)
    certifications: list[CertificationRead] = Field(default_factory=list)
    history: list[HistoryRead] = Field(default_factory=list)
    documents: list[DocumentRead] = Field(default_factory=list)
