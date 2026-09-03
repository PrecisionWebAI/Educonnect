from datetime import date

from pydantic import BaseModel

from .models import StudentProfileBase


class StudentCreate(StudentProfileBase):
    pass


class StudentRead(StudentProfileBase):
    id: int


class StudentUpdate(BaseModel):
    date_of_birth: date | None = None
    guardian_name: str | None = None
    grade_class_id: int | None = None
    section_id: int | None = None
