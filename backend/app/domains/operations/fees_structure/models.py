"""A fee head - one row per class and fee (the Operations > Fees Structure card).

`class_id` points at the platform catalog (`classname`), not at a class-section:
a fee is published for "Class 10", not for "Class 10-A".
"""

import enum
from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class FeeFrequency(enum.StrEnum):
    monthly = "monthly"
    term = "term"
    yearly = "yearly"
    one_time = "one_time"


class FeeStructureBase(SQLModel):
    name: str  # e.g., "Tuition Fee"
    #: `numeric(12,2)` (Rule 4) - a fee head's amount is money, not a measurement.
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    #: The class this fee head is for - a `classname` row ("Class 10").
    class_id: UUID = Field(foreign_key="classname.class_id", index=True)
    frequency: FeeFrequency
    # Free text on purpose - schools word due dates differently ("10th of
    # month", "5th of term", "At admission") and the fee card shows the wording.
    due_day: str | None = None
    # "Draft" until the office publishes the card, "Active" afterwards. Plain
    # text (not an enum) so the stored value is the value the screen shows.
    status: str = Field(default="Draft")


class FeeStructure(FeeStructureBase, TenantMixin, UUIDMixin, table=True):
    pass
