import enum
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint, text
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
    student_id: UUID = Field(foreign_key="student.id")
    #: The register this row belongs to - the school's `classroom` row for that
    #: class-section. The class and section come from it, so neither is copied here.
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id")
    date: date
    status: AttendanceStatus
    remarks: str | None = None
    overridden_by_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    #: The approved leave this day is about, when one covers it.
    #:
    #: The register shows `leave` **derived** from the request (`service.register`),
    #: so the status is never typed twice; this link exists so the office can open the
    #: request from the row, and so a cancelled leave can be traced back.
    leave_request_id: UUID | None = Field(
        default=None, foreign_key="leaverequest.id", index=True
    )


class AttendanceRecord(AttendanceRecordBase, TenantMixin, UUIDMixin, table=True):
    """One child, one day, one subject - **once**.

    Two keys, and they are the reason a re-save can never double the register:

    * `UNIQUE(school_id, student_id, date, subject_id)` - the obvious one; PostgreSQL
      treats two NULL subjects as different values, so on its own it would let the
      day-level row (no subject) be written again;
    * a **partial** unique index on `(school_id, student_id, date) WHERE subject_id IS
      NULL` closes exactly that hole: a day-level mark is single, a per-subject mark is
      single per subject.

    The service reads-then-writes and says `409` when it loses a race; these keys are
    what makes that a rare path instead of a silent duplicate.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "student_id",
            "date",
            "subject_id",
            name="uq_attendancerecord_school_student_date_subject",
        ),
        Index(
            "uq_attendancerecord_school_student_date_day",
            "school_id",
            "student_id",
            "date",
            unique=True,
            postgresql_where=text("subject_id IS NULL"),
            sqlite_where=text("subject_id IS NULL"),
        ),
    )


class AttendanceAuditLogBase(SQLModel):
    attendance_record_id: UUID = Field(foreign_key="attendancerecord.id")
    changed_by_id: UUID = Field(foreign_key="app_user.id")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    previous_status: AttendanceStatus | None = None
    new_status: AttendanceStatus
    previous_remarks: str | None = None
    new_remarks: str | None = None


class AttendanceAuditLog(AttendanceAuditLogBase, TenantMixin, UUIDMixin, table=True):
    pass
