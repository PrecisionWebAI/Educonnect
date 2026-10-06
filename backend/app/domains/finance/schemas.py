from typing import Literal

from pydantic import BaseModel

from .models import FeeStructureBase, FeeTransactionBase


class FeeStructureCreate(FeeStructureBase):
    pass


class FeeStructureRead(FeeStructureBase):
    id: int


class FeeTransactionCreate(FeeTransactionBase):
    pass


class FeeTransactionRead(FeeTransactionBase):
    id: int


class StudentDuesResponse(BaseModel):
    student_id: int
    total_applicable_fees: float
    total_paid: float
    pending_balance: float


class FeeInvoiceRead(BaseModel):
    id: int
    student: str
    className: str
    head: str
    amount: float
    paid: float
    due: float
    status: str


class ExpenseItemRead(BaseModel):
    id: int
    vendor: str
    head: str
    amount: float
    date: str
    status: str


class CollectionReportRowRead(BaseModel):
    id: int
    period: str
    billed: str
    collected: str
    variance: str
    mode: str


class SalaryStructureRowRead(BaseModel):
    id: int
    staffCode: str
    name: str
    basic: float
    hra: float
    da: float
    special: float
    total: float


class FeeStructureRowCreate(BaseModel):
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


class FeeStructureRowUpdate(BaseModel):
    """Body of `PUT /finance/fee-structures/{structure_id}`."""

    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str | None = None


class FeeStructureStatusUpdate(BaseModel):
    """Body of `PUT /finance/fee-structures/{structure_id}/status`."""

    status: Literal["Active", "Draft"]


class FeeStructureRowRead(BaseModel):
    """One fee head as the Fees Structure screen shows it.

    `students` is the number of students the head applies to (a live count for
    per-class heads, the whole school for "All Classes" heads), so the "value"
    figures on the screen are arithmetic over real rows.
    """

    id: int
    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str
    students: int
    status: str


class PayrollEntryRead(BaseModel):
    id: int
    staffCode: str
    name: str
    basic: float
    allowances: float
    deductions: float
    net: float
    status: str
