from typing import Literal
from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import FeeStructureBase, FeeTransactionBase



class FeeStructureCreate(CanonicalRequest, FeeStructureBase):
    pass


class FeeStructureRead(FeeStructureBase):
    id: UUID


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


class FeeStructureRowCreate(CanonicalRequest):
    """Body of `POST /finance/fee-structures` (the New Fee Head modal).

    `class_name` is the class the head applies to, exactly as the UI lists it
    ("Grade 6"); the service resolves it to `classroom.id`. `frequency` is the
    UI label ("Monthly"), not the enum value.
    """

    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str | None = None


class FeeStructureRowUpdate(CanonicalRequest):
    """Body of `PUT /finance/fee-structures/{structure_id}`."""

    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str | None = None


class FeeStructureStatusUpdate(CanonicalRequest):
    """Body of `PUT /finance/fee-structures/{structure_id}/status`."""

    status: Literal["Active", "Draft"]


class FeeStructureRowRead(BaseModel):
    """One fee head as the Fees Structure screen shows it.

    `students` is the number of students the head applies to (a live count for
    per-class heads, the whole school for "All Classes" heads), so the "value"
    figures on the screen are arithmetic over real rows.
    """

    id: UUID
    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str
    students: int
    status: str


class PayrollEntryRead(BaseModel):
    id: UUID
    staffCode: str
    name: str
    basic: float
    allowances: float
    deductions: float
    net: float
    status: str
