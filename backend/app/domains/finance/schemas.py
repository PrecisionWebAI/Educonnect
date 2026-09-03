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
