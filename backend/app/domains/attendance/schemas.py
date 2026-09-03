from datetime import date

from pydantic import BaseModel

from .models import AttendanceRecordBase


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordRead(AttendanceRecordBase):
    id: int


class AttendanceBulkCreate(BaseModel):
    grade_class_id: int
    section_id: int
    date: date
    records: list[
        dict
    ]  # Expected format: [{"student_id": 1, "status": "present", "remarks": "Optional"}]
