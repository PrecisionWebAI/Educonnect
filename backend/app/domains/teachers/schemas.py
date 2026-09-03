from datetime import date

from pydantic import BaseModel

from .models import TeacherProfileBase


class TeacherCreate(TeacherProfileBase):
    pass


class TeacherRead(TeacherProfileBase):
    id: int


class TeacherUpdate(BaseModel):
    department: str | None = None
    qualification: str | None = None
    joining_date: date | None = None
