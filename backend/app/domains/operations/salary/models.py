"""Staff salary - what an employee is paid, and what they were actually paid.

Two tables, one per question the screen asks:

* `employeesalary` - **what this employee is paid now** (the monthly figure the
  hire form collects). One current row per employee; `employee_id` is UNIQUE.
  It lives here, not on `employee`, so the person record stays about the person
  and a salary change is a row of its own.
* `salarypayment` - the monthly **register**: one row per employee per month.
  It stores the money and `employee_id` (plus `school_id` from the tenant mixin)
  and nothing about who the person is: the code, name, designation and
  department the register shows are read *through* `employee_id`, so a rename or
  a promotion cannot leave the register describing somebody who no longer
  exists.

`month` is stored as the label the register shows ("Sep 2026") because the
screen groups and filters by exactly that string. `status` walks
Pending -> Processing -> Paid; `paid_on` is stamped when the row is marked Paid,
which is what makes "Paid" trustworthy.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow

# Register states, stored exactly as the screen labels them.
STATUS_PENDING = "Pending"
STATUS_PROCESSING = "Processing"
STATUS_PAID = "Paid"


class EmployeeSalaryBase(SQLModel):
    """An employee's current salary - one row per employee."""

    employee_id: UUID = Field(foreign_key="employee.id", unique=True, index=True)
    #: `numeric(12,2)` (Rule 4) - the figure payroll actually pays, stored exactly.
    salary_monthly: Decimal = Field(
        default=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    #: When this figure started applying (a raise is a new row's date).
    effective_from: date = Field(default_factory=date.today)


class EmployeeSalary(EmployeeSalaryBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "employeesalary"

    created_at: datetime = Field(default_factory=utcnow)


class SalaryPaymentBase(SQLModel):
    #: Who is being paid. Everything the register displays is read through this.
    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    month: str = Field(index=True)  # "Sep 2026"
    #: The three money columns, `numeric(12,2)` (Rule 4). `net` is stored, not derived:
    #: a payslip that was handed over must keep the figure it was handed over with,
    #: even after the deduction rules change.
    gross: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    deductions: Decimal = Field(
        default=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    net: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    status: str = Field(default=STATUS_PENDING)
    paid_on: date | None = None


class SalaryPayment(SalaryPaymentBase, TenantMixin, UUIDMixin, table=True):
    pass
