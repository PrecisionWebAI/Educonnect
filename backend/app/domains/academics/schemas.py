from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import ClassroomBase, SectionBase, SubjectBase



# Classroom Schemas - a class in the **platform** catalog (the 15 rows every
# school reads). A school's own class-section row is not addressed here.
class ClassroomCreate(CanonicalRequest):
    """A class the way a client names it: "Class 6", its level and its stage."""

    name: str
    level: int = 0
    stage: str = "primary"


class ClassroomRead(ClassroomCreate):
    id: UUID


class ClassroomUpdate(CanonicalRequest):
    name: str | None = None
    level: int | None = None


# Section Schemas
class SectionCreate(CanonicalRequest, SectionBase):
    pass


class SectionRead(SectionBase):
    id: UUID


# Subject Schemas
class SubjectCreate(CanonicalRequest, SubjectBase):
    pass


class SubjectRead(SubjectBase):
    id: UUID


class ClassInfoRead(BaseModel):
    id: UUID
    name: str
    section: str = "A"
    classTeacher: str = "Staff"
    strength: int = 40


# ---------------------------------------------------------------------------
# Class catalogue - the vocabulary the client renders
#
# One payload so the frontend keeps no class list of its own: adding a class in
# the database makes every dropdown, filter and stage chip follow.
# ---------------------------------------------------------------------------


class CatalogSectionRead(BaseModel):
    id: UUID
    name: str
    # camelCase like the rest of the academics payloads (`className`), because
    # the Angular-less client never converts key case on these routes.
    classroomId: UUID


class CatalogClassRead(BaseModel):
    id: UUID
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
