"""Staff members hired through the Staff Hiring screen.

One table:

* ``staffprofile`` - the staff member the school actually has: their login
  (``stf.*`` / ``tea.*``), employee code (EMP-####), role, department and the
  KYC / bank / salary detail the hire form collects. Filling the Registration
  form writes this row directly (there is no separate staging table). This is
  the staff equivalent of ``studentprofile`` and the table the rest of the
  product points at.

The candidate pipeline (``hiringcandidate`` in the ``hiring`` domain) stays a
separate funnel of people who *might* be hired one day; it does not feed this
flow.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class EmployeeBase(SQLModel):
    """An employee - login + employee record in one place (the main table).

    The roles this person holds are **not** a column here: they live in
    `user_role` (`app/domains/auth/models.py`), so one employee can be a teacher
    *and* the librarian without a second row or a duplicated field.
    """

    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    employee_code: str = Field(unique=True, index=True)  # EMP-0043 (the employee id)
    department: str
    qualification: str | None = None
    experience_years: int = 0
    joining_date: date

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


class Employee(EmployeeBase, TenantMixin, table=True):
    __tablename__ = "employee"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
