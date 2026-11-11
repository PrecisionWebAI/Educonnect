from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import FeeTransactionBase


class FeeTransactionCreate(CanonicalRequest, FeeTransactionBase):
    pass


class FeeTransactionRead(FeeTransactionBase):
    id: UUID


class StudentDuesResponse(BaseModel):
    student_id: UUID
    total_applicable_fees: float
    total_paid: float
    pending_balance: float


class FeeInvoiceRead(BaseModel):
    #: Not a table row: an invoice *is* the (student, fee head) pair, so the key is
    #: that pair - `"<student uuid>:<fee structure uuid>"`.
    id: str
    student: str
    className: str
    head: str
    amount: float
    paid: float
    due: float
    status: str


class CollectionReportRowRead(BaseModel):
    #: A computed period summary, not a table row - the key is the period.
    id: str
    period: str
    billed: str
    collected: str
    variance: str
    mode: str


class SalaryStructureRowRead(BaseModel):
    id: UUID
    staffCode: str
    name: str
    basic: float
    hra: float
    da: float
    special: float
    total: float


class PayrollEntryRead(BaseModel):
    id: UUID
    staffCode: str
    name: str
    basic: float
    allowances: float
    deductions: float
    net: float
    status: str
