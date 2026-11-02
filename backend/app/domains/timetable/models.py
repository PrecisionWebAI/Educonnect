import enum
from datetime import time
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class DayOfWeek(enum.StrEnum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class TimetablePeriodBase(SQLModel):
    #: A period belongs to one class-section; the class comes from
    #: `section.classroom_id`. There is deliberately no class-wide period - "Class
    #: 10 at 9am" does not say which section is in the room.
    section_id: UUID = Field(foreign_key="section.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class TimetablePeriod(TimetablePeriodBase, TenantMixin, UUIDMixin, table=True):
    pass
