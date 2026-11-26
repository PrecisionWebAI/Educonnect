"""The shapes of one person's week, as the teacher's own "My week" panel reads it.

The capacity rule, the duty forms and the analytics that used to live here went with the
Workload tab.
"""

from datetime import time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WeekSlotRead(BaseModel):
    """One cell of the week grid: a taught period or a duty.

    `kind` is what the grid colours differently, and it is the reason periods and
    duties can share one list - a teacher does not experience them as two weeks.
    """

    kind: Literal["period", "duty"]
    day: str
    day_label: str
    start: time | None = None
    end: time | None = None
    #: `09:00-09:45`; empty when the duty has no hours.
    slot: str = ""
    #: The subject for a period, the duty's own name for a duty.
    subject: str
    #: `Class 9-A` for a period; None for a duty.
    class_label: str | None = None
    room: str | None = None
    title: str | None = None
    period_id: UUID | None = None
    duty_id: UUID | None = None


class WeekDayRead(BaseModel):
    """One column of the grid. A day with nothing in it is still a day."""

    day: str
    day_label: str
    slots: list[WeekSlotRead] = Field(default_factory=list)
    periods: int = 0
    duties: int = 0


class StaffWeekRead(BaseModel):
    """One person's week: the grid, its two totals and the duty hours beside them."""

    id: UUID
    name: str
    department: str
    days: list[WeekDayRead] = Field(default_factory=list)
    periods: int = 0
    duties: int = 0
    #: Hours of *duty* only - see the note in `__init__.py` on why these are not
    #: folded into the period count.
    duty_hours: float = 0.0
    #: Days with neither a period nor a duty, so the screen can say "3 free days".
    empty_days: int = 0
