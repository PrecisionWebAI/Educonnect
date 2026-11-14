import enum
from datetime import time
from uuid import UUID

from sqlalchemy import UniqueConstraint
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
    #: A period belongs to one class-section - the school's `classroom` row.
    #: There is deliberately no class-wide period: "Class 10 at 9am" does not say
    #: which section is in the room.
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class TimetablePeriod(TimetablePeriodBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, teacher_id, day_of_week, start_time)` - one room, one teacher.

    The rule this key states is the one a substitution engine and a workload figure
    both assume: a teacher cannot be in two places at the same hour on the same
    weekday. PostgreSQL enforces it, so two clerks building the timetable cannot
    create the clash the screens would then have to explain.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "teacher_id",
            "day_of_week",
            "start_time",
            name="uq_timetableperiod_teacher_slot",
        ),
    )
