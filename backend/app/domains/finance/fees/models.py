import enum
from datetime import date
from decimal import Decimal
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
    #: `numeric(12,2)` in the database (Rule 4). `Decimal` on the model is what keeps
    #: a rupee exact; the **API** still serves a float, because the screens do
    #: arithmetic with it and JSON has no decimal type.
    amount_paid: Decimal = Field(max_digits=12, decimal_places=2)
    date: date
    payment_mode: PaymentMode
    receipt_number: str = Field(unique=True, index=True)


class FeeTransaction(FeeTransactionBase, TenantMixin, UUIDMixin, table=True):
    pass
