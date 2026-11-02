from datetime import date
from uuid import UUID
from pydantic import BaseModel


class SalaryPaymentRead(BaseModel):
    """The register row as the screen shows it.

    The table stores the money plus `employee_id`; the code, name, designation
    and department below are read through that link, so the register can never
    describe a person who no longer exists.
    """

    id: UUID
    employee_id: UUID
    staff_code: str
    staff_name: str
    designation: str
    department: str
    month: str
    gross: float = 0.0
    deductions: float = 0.0
    net: float = 0.0
    status: str
    paid_on: date | None = None


class EmployeeSalaryRead(BaseModel):
    """An employee's current salary row."""

    id: UUID
    employee_id: UUID
    salary_monthly: float
    effective_from: date


class PayrollRunRequest(BaseModel):
    """Body of `POST /salary/payroll/run`."""

    month: str


class PayrollRunResult(BaseModel):
    """How many rows the run moved into Processing."""

    month: str
    queued: int

