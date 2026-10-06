from pydantic import BaseModel

from .models import SalaryPaymentBase


class SalaryPaymentRead(SalaryPaymentBase):
    id: int


class PayrollRunRequest(BaseModel):
    """Body of `POST /salary/payroll/run`."""

    month: str


class PayrollRunResult(BaseModel):
    """How many rows the run moved into Processing."""

    month: str
    queued: int
