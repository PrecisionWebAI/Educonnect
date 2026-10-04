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
    classroom_id: int = Field(foreign_key="classroom.id")
    frequency: FeeFrequency
    # Free text on purpose - schools word due dates differently ("10th of
    # month", "5th of term", "At admission") and the fee card shows the wording.
    due_day: str | None = None
    # "Draft" until the office publishes the card, "Active" afterwards. Plain
    # text (not an enum) so the stored value is the value the screen shows.
    status: str = Field(default="Draft")


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
