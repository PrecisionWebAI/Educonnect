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
    #: The school year this week belongs to. Old rows may be NULL until the
    #: migration's current-year backfill; reads treat NULL as the current year.
    academic_year_id: UUID | None = Field(
        default=None, foreign_key="academic_year.id", index=True
    )
    #: A period belongs to one class-section - the school's `classroom` row.
    #: There is deliberately no class-wide period: "Class 10 at 9am" does not say
    #: which section is in the room.
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    #: The section's own subject (`classroomsubject.id`).
    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    teacher_id: UUID = Field(foreign_key="employee.id")
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class TimetablePeriod(TimetablePeriodBase, TenantMixin, UUIDMixin, table=True):
    """Two keys, because two different clashes are both impossible.

    * `uq_timetableperiod_teacher_slot` - a teacher cannot be in two places at the same
      hour on the same weekday;
    * `uq_timetableperiod_class_slot` - a class-section cannot be given two subjects in
      the same slot either (Phase 9). The first key alone let the grid hold "Maths and
      Science, both 09:00 Monday, both 9-A", which no substitution engine or workload
      figure could make sense of.

    PostgreSQL enforces both, so two clerks building the timetable cannot create the
    clash the screens would then have to explain - and the API turns the refusal into a
    `409` that names the teacher or the class.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "teacher_id",
            "day_of_week",
            "start_time",
            name="uq_timetableperiod_teacher_slot",
        ),
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "classroom_id",
            "day_of_week",
            "start_time",
            name="uq_timetableperiod_class_slot",
        ),
    )


class BellScheduleBase(SQLModel):
    """One slot of the school day: a teaching period or a break.

    The day's shape belongs to the **school**, not to a screen. Before Phase 9 it lived
    as six hardcoded rows in `TimetablePanel.tsx`, so a school with eight periods or a
    long lunch break had no way to say so.
    """

    #: 1, 2, 3 … in time order. A break keeps its place in the sequence, which is why the
    #: number is stored rather than recomputed from the teaching periods.
    period_no: int
    start_time: time
    end_time: time
    #: True for the rows that are not lessons - the frontend draws them as breaks and
    #: offers no subject for them.
    is_break: bool = Field(default=False)


class BellSchedule(BellScheduleBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, period_no)` - one row per slot, in one order."""

    __tablename__ = "bellschedule"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "period_no", name="uq_bellschedule_school_period"
        ),
    )
