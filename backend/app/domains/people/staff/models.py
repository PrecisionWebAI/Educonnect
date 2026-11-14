"""Staff members hired through the Staff Hiring screen.

One table:

* ``staffprofile`` - the staff member the school actually has: their login
  (``stf.*`` / ``tea.*``), employee code (EMP-####), role, department and the
  KYC / bank / salary detail the hire form collects. Filling the Registration
  form writes this row directly (there is no separate staging table). This is
  the staff equivalent of ``Student`` and the table the rest of the
  product points at.

The candidate pipeline (``hiringcandidate`` in the ``hiring`` domain) stays a
separate funnel of people who *might* be hired one day; it does not feed this
flow.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class EmployeeBase(SQLModel):
    """An employee - login + employee record in one place (the main table).

    The roles this person holds are **not** a column here: they live in
    `user_role` (`app/domains/auth/models.py`), so one employee can be a teacher
    *and* the librarian without a second row or a duplicated field.
    """

    user_id: UUID = Field(foreign_key="user.id", unique=True, index=True)
    employee_code: str = Field(unique=True, index=True)  # EMP-0043 (the employee id)
    department: str
    qualification: str | None = None
    experience_years: int = 0
    joining_date: date

    # --- the post itself (the profile drawer's Overview) -------------------
    #: What the person is called on the roll ("Senior Teacher", "Lab Assistant").
    #: NULL until somebody sets it: "designation = department" would be a claim
    #: the school never made, and the profile shows the blank honestly.
    designation: str | None = None
    #: The wording payroll and the profile print: Full-time / Part-time / Contract
    #: / Guest. Kept as the words themselves, not a code the UI must translate.
    employment_type: str | None = None
    #: The day probation ends. NULL means the post has no probation (or nobody
    #: recorded one) - not "probation ended today".
    probation_end: date | None = None
    #: Who this person reports to, as another employee in the same school. A
    #: self-reference rather than a free-text name: the profile drawer shows the
    #: reporting line, and a rename must not break it.
    reports_to_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )

    # --- employee detail (the hire form) ----------------------------------
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    # KYC / payroll
    aadhaar_no: str | None = Field(default=None, index=True)
    pan_no: str | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    ifsc: str | None = None
    previous_employer_monthly_salary: float | None = None

    # --- lifecycle (a person who left is deactivated, not deleted) ---------
    #: The day they stopped working here. Kept beside the record so the salary
    #: register and the register's history still explain themselves.
    left_on: date | None = None
    #: When the school deactivated the staff side of this person. Their **login is
    #: only switched off when they hold no other role** - a teacher whose child
    #: studies here keeps signing in as a parent.
    deactivated_at: datetime | None = None
    #: The staff roles that were withdrawn at deactivation, comma-separated, so
    #: reactivating them restores exactly the access they had.
    deactivated_roles: str | None = None


class Employee(EmployeeBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "employee"

    created_at: datetime = Field(default_factory=utcnow)

    #: A phone number and an email are unique **inside a school** (partial indexes,
    #: so a blank or missing value never collides): the same number cannot sit on two
    #: employees, because the school would not know who it is ringing.
    __table_args__ = (
        Index(
            "uq_employee_school_email",
            "school_id",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL AND email <> ''"),
        ),
        Index(
            "uq_employee_school_phone",
            "school_id",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL AND phone <> ''"),
        ),
    )
