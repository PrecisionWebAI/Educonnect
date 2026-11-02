from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class ClassroomBase(SQLModel):
    #: Global catalog - one "Class 6" shared by every school, exactly like the
    #: role catalog. The school boundary lives on the *data* rows (students,
    #: attendance, timetable) through their `school_id`, not on the class names.
    name: str = Field(unique=True, index=True)
    level: int
    #: School stage for grouping/reporting: pre_primary, primary, middle,
    #: secondary, senior_secondary. Stored rather than derived from the name, so
    #: a school that calls them "Std VI" still reports correctly.
    stage: str = Field(default="primary")


class Classroom(ClassroomBase, UUIDMixin, table=True):
    sections: list[Section] = Relationship(back_populates="classroom")


class SectionBase(SQLModel):
    name: str
    classroom_id: UUID = Field(foreign_key="classroom.id")


class Section(SectionBase, UUIDMixin, table=True):
    #: Two "A" sections inside one class is always a mistake, so the database
    #: rejects it instead of relying on application code (the "planned" unique
    #: constraint in `info/db_mapping.txt`).
    __table_args__ = (
        UniqueConstraint("classroom_id", "name", name="uq_section_classroom_name"),
    )

    classroom: Classroom = Relationship(back_populates="sections")


class SubjectBase(SQLModel):
    #: Both unique **inside a school** - two schools may each have a "Mathematics".
    #: `Subject` adds the (school_id, name) / (school_id, code) unique indexes.
    name: str = Field(index=True)
    code: str = Field(index=True)


class Subject(SubjectBase, TenantMixin, UUIDMixin, table=True):
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_school_name"),
        UniqueConstraint("school_id", "code", name="uq_subject_school_code"),
    )



class SyllabusProgressBase(SQLModel):
    """How far a section has got through a subject's syllabus.

    The card's "course complete %" is `chapters_done / chapters_total`. It hangs
    off the **section** (the class-section is what a card shows), and the
    classroom is reached through `section.classroom_id` - no second copy of the
    class id.
    """

    section_id: UUID = Field(foreign_key="section.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    chapters_total: int = 0
    chapters_done: int = 0


class SyllabusProgress(SyllabusProgressBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(section_id, subject_id)` - one progress row per subject per section."""

    __table_args__ = (
        UniqueConstraint(
            "section_id", "subject_id", name="uq_syllabusprogress_section_subject"
        ),
    )

    updated_at: datetime = Field(default_factory=datetime.utcnow)
