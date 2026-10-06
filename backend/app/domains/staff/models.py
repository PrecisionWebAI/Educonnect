"""Staff members hired through the Staff Hiring screen.

Two tables, mirroring the admission flow:

* ``staffregistration`` - the short registration form the office fills for a
  new hire (one row per hire). Submitting it *is* the hiring action.
* ``staffprofile`` - the staff member the school actually has: their login
  (``stf.*`` / ``tea.*``), employee code (EMP-####), role and department. This
  is the staff equivalent of ``studentprofile`` and the table the rest of the
  product points at.

The candidate pipeline (``hiringcandidate`` + ``staffvacancy`` in the
``hiring`` domain) stays a separate funnel of people who *might* be hired one
day; it does not feed this flow.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.domains.auth.models import utcnow


class StaffProfileBase(SQLModel):
    """A hired staff member - login + employee record in one place."""

    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    employee_code: str = Field(unique=True, index=True)  # EMP-0043
    role_codename: str  # the role they were hired for (teacher, accountant, ...)
    department: str
    qualification: str | None = None
    experience_years: int = 0
    joining_date: date
    # Teaching roles also get a ``teacherprofile`` row so the class assignment
    # and timetable screens can place them; this is the link back to it.
    teacher_profile_id: int | None = Field(
        default=None, foreign_key="teacherprofile.id"
    )


class StaffProfile(StaffProfileBase, table=True):
    __tablename__ = "staffprofile"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class StaffRegistrationBase(SQLModel):
    """The short hire-registration form (name, role, department, ...)."""

    full_name: str
    role_codename: str
    department: str
    qualification: str | None = None
    experience_years: int = 0
    contact_email: str | None = None
    joining_date: date
    notes: str | None = None


class StaffRegistration(StaffRegistrationBase, table=True):
    __tablename__ = "staffregistration"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    # --- promotion link (filled on submit; never cleared) -----------------
    staff_profile_id: int | None = Field(
        default=None, foreign_key="staffprofile.id", unique=True
    )
    user_id: int | None = Field(default=None, foreign_key="user.id")
    promoted_at: datetime | None = None
