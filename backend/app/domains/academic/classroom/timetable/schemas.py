"""Timetable shapes.

The API speaks `section_id` for the class-section a period belongs to (the column is
`classroom_id`), and `HH:MM` times in, `HH:MM:SS` out - exactly what the grid sends and
what `lib/…/hhmm()` trims.
"""

from datetime import time
from uuid import UUID

from pydantic import BaseModel

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


class TimetableSlotRead(BaseModel):
    """The school-wide week, names only (the personal timetable view reads this)."""

    day: str
    period: str
    className: str
    subject: str
    teacher: str
