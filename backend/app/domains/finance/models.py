import enum
from datetime import date

from sqlmodel import Field, SQLModel


class FeeFrequency(enum.StrEnum):
    monthly = "monthly"
    term = "term"
    yearly = "yearly"
    one_time = "one_time"


class PaymentMode(enum.StrEnum):
    cash = "cash"
    upi = "upi"
    card = "card"
    cheque = "cheque"
    bank_transfer = "bank_transfer"


class FeeStructureBase(SQLModel):
    name: str  # e.g., "Tuition Fee"
    amount: float
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    frequency: FeeFrequency


class FeeStructure(FeeStructureBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class FeeTransactionBase(SQLModel):
    student_id: int = Field(foreign_key="studentprofile.id")
    fee_structure_id: int = Field(foreign_key="feestructure.id")
    amount_paid: float
    date: date
    payment_mode: PaymentMode
    receipt_number: str = Field(unique=True, index=True)


class FeeTransaction(FeeTransactionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
