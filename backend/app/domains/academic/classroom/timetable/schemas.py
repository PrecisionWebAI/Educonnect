"""Timetable shapes.

The API speaks `section_id` for the class-section a period belongs to (the column is
`classroom_id`), and `HH:MM` times in, `HH:MM:SS` out - exactly what the grid sends and
what `lib/…/hhmm()` trims.
"""

from datetime import time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest

from .models import DayOfWeek


class TimetablePeriodCreate(CanonicalRequest):
    """One slot: this class-section, this subject, this teacher, this hour."""

    section_id: UUID
    #: The section's own subject (`classroomsubject.id`).
    classroom_subject_id: UUID
    teacher_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class TimetablePeriodRead(BaseModel):
    id: UUID
    section_id: UUID
    academic_year_id: UUID | None = None
    classroom_subject_id: UUID
    #: The subject's name, read from the section subject.
    subject: str | None = None
    teacher_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class BellSlotRead(BaseModel):
    """One slot of the school's day, as the grid draws it."""

    period_no: int
    #: "P1", "P2" … for lessons; "Break" for the rows that are not lessons.
    label: str
    start_time: time
    end_time: time
    is_break: bool
    #: True for the extra classes (E1, E2 ...).
    extra: bool = False


class BreakWrite(BaseModel):
    """A break in the day: where it falls and how long it runs."""

    #: The lesson number it follows (1 = right after P1).
    after_period: int = Field(ge=1)
    minutes: int = Field(default=20, ge=5, le=120)


class ExtraClassesWrite(BaseModel):
    """The optional extra classes (E1, E2 ...) that follow the regular day."""

    #: 0 clears them.
    count: int = Field(default=0, ge=0, le=8)
    breaks: list[BreakWrite] = []
    start_time: time = time(15, 0)
    period_minutes: int = Field(default=40, ge=10, le=120)
    #: Extra classes sit before or after the regular periods, never between them.
    position: Literal["before", "after"] = "after"


class BellScheduleWrite(BaseModel):
    """The day's shape in the words a school uses: how many periods, which breaks.

    The server lays the rows out in time order, so the client never sends clock times
    for each slot.
    """

    periods: int = Field(ge=1, le=12)
    breaks: list[BreakWrite] = []
    start_time: time = time(8, 0)
    period_minutes: int = Field(default=45, ge=10, le=120)
    #: Confirm that placed periods beyond the new last period may be removed.
    force: bool = False
    #: Extra classes; leave out to keep what the school already has.
    extra: ExtraClassesWrite | None = None


class WeekOffRead(BaseModel):
    """Weekdays the school is closed (`date.weekday()`: 0 = Monday) and the
    `"5#1"` Saturday-style rules (a partial off)."""

    days: list[int]
    nth: list[str]


class TimetableSlotRead(BaseModel):
    """The school-wide week, names only (the personal timetable view reads this)."""

    day: str
    period: str
    className: str
    subject: str
    teacher: str
    #: The teacher's employee id: counts and clashes match on this, not the name.
    teacherId: UUID | None = None
    #: The class-section (`classroom_id`) the period belongs to.
    sectionId: UUID | None = None
