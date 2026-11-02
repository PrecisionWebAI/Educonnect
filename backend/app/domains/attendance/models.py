import enum
from datetime import date, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class AttendanceStatus(enum.StrEnum):
    present = "present"
    absent = "absent"
    leave = "leave"
    late = "late"
    half_day = "half_day"


class AttendanceRecordBase(SQLModel):
    student_id: UUID = Field(foreign_key="studentprofile.id")
    #: The register this row belongs to. The class comes from
    #: `section.classroom_id`, so it is not copied here.
    section_id: UUID = Field(foreign_key="section.id")
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id")
    date: date
    status: AttendanceStatus
    remarks: str | None = None
    overridden_by_id: UUID | None = Field(default=None, foreign_key="user.id")


class AttendanceRecord(AttendanceRecordBase, TenantMixin, UUIDMixin, table=True):
    pass


class AttendanceAuditLogBase(SQLModel):
    attendance_record_id: UUID = Field(foreign_key="attendancerecord.id")
    changed_by_id: UUID = Field(foreign_key="user.id")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    previous_status: AttendanceStatus | None = None
    new_status: AttendanceStatus
    previous_remarks: str | None = None
    new_remarks: str | None = None


class AttendanceAuditLog(AttendanceAuditLogBase, TenantMixin, UUIDMixin, table=True):
    pass
