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


class PayrollEntryRead(BaseModel):
    id: int
    staffCode: str
    name: str
    basic: float
    allowances: float
    deductions: float
    net: float
    status: str
