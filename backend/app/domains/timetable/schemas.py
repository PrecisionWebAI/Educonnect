from uuid import UUID
from pydantic import BaseModel

from .models import TimetablePeriodBase


class TimetablePeriodCreate(TimetablePeriodBase):
    pass


class TimetablePeriodRead(TimetablePeriodBase):
    id: UUID


class TimetableSlotRead(BaseModel):
    day: str
    period: str
    className: str
    subject: str
    teacher: str
