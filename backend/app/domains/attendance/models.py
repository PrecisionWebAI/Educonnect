import enum
from datetime import date

from sqlmodel import Field, SQLModel


class AttendanceStatus(enum.StrEnum):
    present = "present"
    absent = "absent"
    leave = "leave"
    late = "late"
    half_day = "half_day"


class AttendanceRecordBase(SQLModel):
    student_id: int = Field(foreign_key="studentprofile.id")
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    section_id: int = Field(foreign_key="section.id")
    date: date
    status: AttendanceStatus
    remarks: str | None = None


class AttendanceRecord(AttendanceRecordBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
