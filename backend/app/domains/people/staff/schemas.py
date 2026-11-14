"""Request/response models for the staff (employee) flow."""

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, Field

from app.core import lifecycle
from app.core.text import CanonicalRequest


class StaffProfileCreate(CanonicalRequest):
    """Body of the hire form on the Staff Hiring screen.

    Filling it creates the `staffprofile` row (and its login) directly.
    """

    full_name: str
    #: The roles this hire holds. The first one is the primary (the dashboard that
    #: opens at login). A person may hold several - a principal who also teaches,
    #: a teacher who also runs the library.
    role_codenames: list[str] = Field(default_factory=list)
    #: Legacy single-role field; used only when `role_codenames` is empty.
    role_codename: str | None = None
    department: str
    qualification: str | None = None
    experience_years: int = 0
    contact_email: str | None = None
    joining_date: dt.date | None = None
    # --- expanded employee detail (KYC / bank / salary) -------------------
    phone: str | None = None
    #: The subjects this teacher can teach (many per teacher).
    subject_ids: list[UUID] = Field(default_factory=list)
    #: Legacy single-subject field; used only when `subject_ids` is empty.
    subject_id: UUID | None = None
    address: str | None = None
    emergency_contact: str | None = None
    aadhaar_no: str | None = None
    pan_no: str | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    ifsc: str | None = None
    salary_monthly: float | None = None
    previous_employer_monthly_salary: float | None = None
    #: When this hire came from the pipeline, the candidate to mark as Hired.
    candidate_id: UUID | None = None


class LoginCredential(BaseModel):
    """One login handed over at hire time (password shown exactly once)."""

    role: str
    full_name: str
    email: str
    password: str | None = None
    created: bool = True


class StaffPasswordResetRead(BaseModel):
    full_name: str
    email: str
    password: str


class StaffProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    employee_code: str
    full_name: str
    email: str
    #: The primary role - the one shown in the Hired tab's Role column.
    role_codename: str
    #: Every role held, primary first.
    role_codenames: list[str] = Field(default_factory=list)
    department: str
    qualification: str | None = None
    experience_years: int = 0
    joining_date: dt.date
    is_teacher: bool
    # --- lifecycle (a person who left is deactivated, not deleted) ----------
    #: True while they work here; False once their staff side was switched off
    #: (`app/domains/staff/lifecycle.py`) - roles come off and the day they left is
    #: stamped, but nothing is deleted, so the register still explains itself.
    isActive: bool = True
    #: The day the office says they left (it can be back-dated), and when the button
    #: was pressed. Both `None` while they are on the staff roll.
    leftOn: str | None = None
    deactivatedAt: str | None = None
    #: The roles that were withdrawn at that moment, so the screen can say what they
    #: lost - and reactivating restores exactly these.
    deactivatedRoles: list[str] = Field(default_factory=list)
    #: True when the login signs in. A teacher who is also a parent keeps their login
    #: (it still opens the parent side), so this can stay True on a deactivated row.
    loginActive: bool = True
    # --- expanded employee detail ------------------------------------------
    contact_email: str | None = None
    phone: str | None = None
    #: Every subject this teacher can teach.
    subject_ids: list[UUID] = Field(default_factory=list)
    address: str | None = None
    emergency_contact: str | None = None
    aadhaar_no: str | None = None
    pan_no: str | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    ifsc: str | None = None
    salary_monthly: float | None = None
    previous_employer_monthly_salary: float | None = None


#: The lifecycle vocabulary - the request body and the answer the button gets - is shared
#: with the Students directory (`app/core/lifecycle.py`), so "deactivate" means the same
#: thing on both screens and the sentence they show is written once.
LifecycleRequest = lifecycle.LifecycleRequest
StaffLifecycleRead = lifecycle.LifecycleRead


class StaffProfileCreateRead(StaffProfileRead):
    """The hire response: the employee plus the login handed over once."""

    credentials: list[LoginCredential] | None = None
