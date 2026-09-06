from datetime import date

from pydantic import BaseModel

from .models import AttendanceRecordBase


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordRead(AttendanceRecordBase):
    id: int
    studentName: str | None = None
    className: str | None = None


class IrregularStudentRead(BaseModel):
    id: int
    name: str
    className: str
    absences: int
    pattern: str
    risk: str


class LeaveSyncRowRead(BaseModel):
    id: int
    student: str
    className: str
    from_date: str
    days: int
    autoMarked: str
    status: str


class AttendanceBulkCreate(BaseModel):
    grade_class_id: int
    section_id: int
    date: date
    records: list[
        dict
    ]  # Expected format: [{"student_id": 1, "status": "present", "remarks": "Optional"}]
