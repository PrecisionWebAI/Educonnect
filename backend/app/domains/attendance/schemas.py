from datetime import date
from uuid import UUID
from pydantic import BaseModel

from .models import AttendanceRecordBase


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordRead(AttendanceRecordBase):
    id: UUID
    studentName: str | None = None
    className: str | None = None
    subjectName: str | None = None


class IrregularStudentRead(BaseModel):
    id: UUID
    name: str
    className: str
    absences: int
    pattern: str
    risk: str


class LeaveSyncRowRead(BaseModel):
    id: UUID
    student: str
    className: str
    from_date: str
    days: int
    autoMarked: str
    status: str


class AttendanceBulkCreate(BaseModel):
    classroom_id: UUID
    section_id: UUID
    subject_id: UUID | None = None
    date: date
    records: list[
        dict
    ]  # Expected format: [{"student_id": 1, "status": "present", "remarks": "Optional"}]
