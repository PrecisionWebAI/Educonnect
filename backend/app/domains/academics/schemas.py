from pydantic import BaseModel

from .models import ClassroomBase, SectionBase, SubjectBase


# Classroom Schemas
class ClassroomCreate(ClassroomBase):
    pass


class ClassroomRead(ClassroomBase):
    id: int


class ClassroomUpdate(BaseModel):
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


class ClassInfoRead(BaseModel):
    id: int
    name: str
    section: str = "A"
    classTeacher: str = "Staff"
    strength: int = 40


class ClassMatrixRowRead(BaseModel):
    id: int
    className: str
    strength: int
    boys: int
    girls: int
    avgAttendance: float


# ---------------------------------------------------------------------------
# Class catalogue - the vocabulary the client renders
#
# One payload so the frontend keeps no class list of its own: adding a class in
# the database makes every dropdown, filter and stage chip follow.
# ---------------------------------------------------------------------------


class CatalogSectionRead(BaseModel):
    id: int
    name: str
    # camelCase like the rest of the academics payloads (`className`), because
    # the Angular-less client never converts key case on these routes.
    classroomId: int


class CatalogClassRead(BaseModel):
    id: int
    name: str
    level: int
    stage: str
    sections: list[CatalogSectionRead] = []


class ClassCatalogRead(BaseModel):
    classes: list[CatalogClassRead] = []
    #: Every section name in use ("A" ... "J"), alphabetical.
    sectionNames: list[str] = []
    #: Every stage in use, in the order a school grows.
    stages: list[str] = []
