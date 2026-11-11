import enum
from datetime import date
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class PaymentMode(enum.StrEnum):
    cash = "cash"
    upi = "upi"
    card = "card"
    cheque = "cheque"
    bank_transfer = "bank_transfer"


class FeeTransactionBase(SQLModel):
    student_id: UUID = Field(foreign_key="student.id")
    fee_structure_id: UUID = Field(foreign_key="feestructure.id")
    amount_paid: float
    date: date
    payment_mode: PaymentMode
    receipt_number: str = Field(unique=True, index=True)


class FeeTransaction(FeeTransactionBase, TenantMixin, UUIDMixin, table=True):
    pass
