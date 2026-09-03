import enum
from datetime import time

from sqlmodel import Field, SQLModel


class DayOfWeek(enum.StrEnum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class TimetablePeriodBase(SQLModel):
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")
    subject_id: int = Field(foreign_key="subject.id")
    teacher_id: int = Field(foreign_key="teacherprofile.id")
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    room: str | None = None


class TimetablePeriod(TimetablePeriodBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
