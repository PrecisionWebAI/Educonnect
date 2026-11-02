from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class ClassroomBase(SQLModel):
    #: Unique **inside a school** - every school has its own "Class 6". `Classroom`
    #: adds the (school_id, name) unique index.
    name: str = Field(index=True)
    level: int
    #: School stage for grouping/reporting: pre_primary, primary, middle,
    #: secondary, senior_secondary. Stored rather than derived from the name, so
    #: a school that calls them "Std VI" still reports correctly.
    stage: str = Field(default="primary")


class Classroom(ClassroomBase, TenantMixin, UUIDMixin, table=True):
    """A class owned by one school: "Class 6" exists once per school.

    It used to be a global catalog row shared by every school, which meant a class
    teacher assigned to it, a fee structure filed against it or a student placed in
    it was visible to every other school. `app/core/db.py` narrows every query by
    `school_id`, so the isolation is only as good as the columns it can filter on -
    hence the tenant column here.
    """

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_classroom_school_name"),
    )

    sections: list[Section] = Relationship(back_populates="classroom")


class SectionBase(SQLModel):
    name: str
    classroom_id: UUID = Field(foreign_key="classroom.id")


class Section(SectionBase, TenantMixin, UUIDMixin, table=True):
    #: Two "A" sections inside one class is always a mistake, so the database
    #: rejects it instead of relying on application code (the "planned" unique
    #: constraint in `info/db_mapping.txt`). Scoped by school like the class is.
    __table_args__ = (
        UniqueConstraint(
            "school_id", "classroom_id", "name", name="uq_section_school_classroom_name"
        ),
    )

    classroom: Classroom = Relationship(back_populates="sections")

    #: Who runs this class-section: one teacher, or nobody yet.
    #:
    #: It is a column rather than a `classteacherassignment` row because the rule
    #: *is* "at most one class teacher per section" - the column cannot express
    #: anything else, so the rule needs no application code to hold. The teacher is
    #: an `employee`, not a user: only staff take a class.
    class_teacher_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )


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


class SubjectTeacherBase(SQLModel):
    """Which teacher takes a subject in one class-section.

    The mapping belongs to the subject - it is *about* a subject - so it lives
    here next to `Subject` rather than with the timetable. It is keyed by
    `(section, subject)` and not by subject alone: a school has a single
    "Mathematics" row but many teachers of it, because Class 9-A and Class 9-B
    usually have different ones.
    """

    section_id: UUID = Field(foreign_key="section.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    #: An `employee`, not a user: only staff take a class.
    teacher_id: UUID = Field(foreign_key="employee.id")


class SubjectTeacher(SubjectTeacherBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(section_id, subject_id)` - one teacher per subject per section."""

    __table_args__ = (
        UniqueConstraint(
            "section_id", "subject_id", name="uq_subjectteacher_section_subject"
        ),
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
