from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.core.text import CanonicalRequest

from .models import FeeStructureBase


class FeeStructureCreate(CanonicalRequest, FeeStructureBase):
    pass


class FeeStructureRead(FeeStructureBase):
    id: UUID


class FeeStructureRowCreate(CanonicalRequest):
    """Body of `POST /finance/fee-structures` (the New Fee Head modal).

    `class_name` is the class the head applies to, exactly as the UI lists it
    ("Grade 6"); the service resolves it to `classname.class_id`. `frequency` is
    the UI label ("Monthly"), not the enum value.
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

    `students` is the number of students the head applies to (a live count per
    class), so the "value" figures on the screen are arithmetic over real rows.
    """

    id: UUID
    head: str
    class_name: str
    frequency: str
    amount: float
    due_day: str
    students: int
    status: str
