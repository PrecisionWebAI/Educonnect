from datetime import date
from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import AttendanceRecordBase



class AttendanceRecordCreate(CanonicalRequest, AttendanceRecordBase):
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


class AttendanceBulkCreate(CanonicalRequest):
    """A whole register in one call.

    Only the section is named - the class is `section.class_id`, so there is
    no second class id to keep in step with it.
    """

    section_id: UUID
    subject_id: UUID | None = None
    date: date
    records: list[
        dict
    ]  # Expected format: [{"student_id": 1, "status": "present", "remarks": "Optional"}]
