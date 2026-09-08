import enum
from datetime import date, datetime

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
    subject_id: int | None = Field(default=None, foreign_key="subject.id")
    date: date
    status: AttendanceStatus
    remarks: str | None = None
    overridden_by_id: int | None = Field(default=None, foreign_key="user.id")


class AttendanceRecord(AttendanceRecordBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class AttendanceAuditLogBase(SQLModel):
    attendance_record_id: int = Field(foreign_key="attendancerecord.id")
    changed_by_id: int = Field(foreign_key="user.id")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    previous_status: AttendanceStatus | None = None
    new_status: AttendanceStatus
    previous_remarks: str | None = None
    new_remarks: str | None = None


class AttendanceAuditLog(AttendanceAuditLogBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
