"""Admission application - the Operations > Admission form, stored row by row.

One row is one application (`admissionapplication`). It mirrors the admission
form field for field, which is why almost every column is a nullable string:
a **draft** is saved half-filled, so "not answered yet" has to be storable.

Deliberate design notes
-----------------------
* No foreign keys. An applicant is not a student yet - there is no `user`
  (no login), no `studentprofile`, and the requested class may not even exist
  in `gradeclass`. `applied_for_class_level` therefore records what the family
  *asked for* (free text, e.g. "Grade 6"), not a class id.
* `status` is plain text (`Draft` / `Registered`) instead of a database enum,
  so the workflow the screen shows maps 1:1 onto the stored value. It replaced
  the old `admissionstatus` enum (pending/under_review/approved/rejected),
  which described a funnel the UI never had.
* The separation block ("why/when the student left") lives on the same row
  instead of a second table: at most one separation can be recorded per
  application, and keeping it here means the Registered table needs no join.
  The `separation` property exposes it as a single nested object.
"""

from datetime import date

from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Stored values (kept as plain strings so the UI wording *is* the stored value)
# ---------------------------------------------------------------------------

STATUS_DRAFT = "Draft"
STATUS_REGISTERED = "Registered"


class AdmissionApplicationBase(SQLModel):
    """Every column of the admission form. All optional: drafts are partial."""

    # ---- workflow --------------------------------------------------------
    # Assigned by the server when the client does not send one
    # (`ADM-<year>-<sequence>`); NOT NULL because every saved row has a number.
    application_no: str = Field(default="", unique=True, index=True)
    status: str = Field(default=STATUS_DRAFT)
    created_on: date = Field(default_factory=date.today)
    notes: str | None = None

    # ---- student ---------------------------------------------------------
    student_first_name: str | None = None
    student_middle_name: str | None = None
    student_last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    religion: str | None = None
    category: str | None = None
    mother_tongue: str | None = None
    nationality: str | None = None
    aadhaar_id: str | None = None
    address: str | None = None
    permanent_address: str | None = None

    # ---- previous school -------------------------------------------------
    previous_school_name: str | None = None
    previous_class_passed: str | None = None
    previous_board: str | None = None
    transfer_certificate_no: str | None = None
    old_unique_id: str | None = None

    # ---- father ----------------------------------------------------------
    father_name: str | None = None
    father_occupation: str | None = None
    father_phone: str | None = None
    father_email: str | None = None
    father_annual_income: str | None = None

    # ---- mother ----------------------------------------------------------
    mother_name: str | None = None
    mother_occupation: str | None = None
    mother_phone: str | None = None
    mother_email: str | None = None
    mother_annual_income: str | None = None

    # ---- guardian (when neither parent is the primary contact) -----------
    guardian_name: str | None = None
    guardian_relation: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    guardian_occupation: str | None = None
    guardian_address: str | None = None

    # ---- placement + logistics -------------------------------------------
    applied_for_class_level: str | None = None
    current_class_or_last_class: str | None = None
    applied_section_preference: str | None = None
    needs_transport: str | None = None
    transport_route: str | None = None
    needs_hostel: str | None = None

    # ---- separation (filled in when the student leaves) ------------------
    separation_dropped_class: str | None = None
    separation_reason: str | None = None
    separation_session: str | None = None
    separation_date: date | None = None


class AdmissionApplication(AdmissionApplicationBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    @property
    def separation(self) -> dict | None:
        """The separation block as one object, or None while still enrolled.

        Derived (not stored) so the four columns above stay the single source
        of truth; `AdmissionApplicationRead` validates this straight into its
        nested `separation` field.
        """
        if self.separation_date is None and not self.separation_reason:
            return None
        return {
            "dropped_class": self.separation_dropped_class,
            "reason": self.separation_reason,
            "session": self.separation_session,
            "date": self.separation_date,
        }
