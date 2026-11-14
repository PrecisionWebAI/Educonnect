"""Staff hiring - the Operations > Staff Hiring pipeline.

One table:

* `hiringcandidate` - one person in the pipeline. `status` walks the same stages
  the screen labels (Resume -> Shortlisted -> Interview -> Hired / Rejected).
  Reaching *Hired* stamps the employee id (`EMP-####`) and creates the staff
  record (see the ``staff`` domain), which is what the salary register pays.
"""

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin

# Pipeline stages, stored exactly as the screen labels them.
HIRING_STATUSES = ("Resume", "Shortlisted", "Interview", "Hired", "Rejected")
STATUS_RESUME = "Resume"
STATUS_INTERVIEW = "Interview"
STATUS_HIRED = "Hired"

#: First employee number handed out when the table is still empty, so a fresh
#: roll continues the numbering the existing staff already use (EMP-0036).
FIRST_EMP_NUMBER = 37


class HiringCandidateBase(SQLModel):
    # Assigned by the server when absent (`CAN-2026-0036`).
    candidate_no: str | None = Field(default=None, unique=True, index=True)
    candidate_name: str
    role: str
    department: str
    qualification: str | None = None
    experience: int = 0
    applied_on: date = Field(default_factory=date.today)
    interview_on: date | None = None
    # Stamped when the candidate reaches "Hired"; NULL while still in the pipeline.
    emp_id: str | None = Field(default=None, index=True)
    status: str = Field(default=STATUS_RESUME)

    # --- interview intake (the "schedule interview" form) -------------------
    phone: str | None = None
    email: str | None = None
    #: The role they applied for, as a role codename (teacher, accountant, ...).
    applied_for: str | None = None
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id")
    #: Snapshot of the subject name (a subject may be renamed later).
    subject_name: str | None = None
    resume_path: str | None = None
    #: Scheduled interview date + time (datetime, not just a date).
    interview_at: datetime | None = None
    interview_note: str | None = None

    # --- the Hired decision -------------------------------------------------
    decided_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    decided_at: datetime | None = None


class HiringCandidate(HiringCandidateBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "pipeline_hiring_table"
