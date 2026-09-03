from pydantic import BaseModel

from .models import GradeClassBase, SectionBase, SubjectBase


# GradeClass Schemas
class GradeClassCreate(GradeClassBase):
    pass


class GradeClassRead(GradeClassBase):
    id: int


class GradeClassUpdate(BaseModel):
    name: str | None = None
    level: int | None = None


# Section Schemas
class SectionCreate(SectionBase):
    pass


class SectionRead(SectionBase):
    id: int


# Subject Schemas
class SubjectCreate(SubjectBase):
    pass


class SubjectRead(SubjectBase):
    id: int
