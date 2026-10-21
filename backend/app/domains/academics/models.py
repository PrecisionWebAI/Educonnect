from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

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


class Classroom(ClassroomBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sections: list[Section] = Relationship(back_populates="classroom")


class SectionBase(SQLModel):
    name: str
    classroom_id: int = Field(foreign_key="classroom.id")


class Section(SectionBase, table=True):
    #: Two "A" sections inside one class is always a mistake, so the database
    #: rejects it instead of relying on application code (the "planned" unique
    #: constraint in `info/db_mapping.txt`).
    __table_args__ = (
        UniqueConstraint("classroom_id", "name", name="uq_section_classroom_name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    classroom: Classroom = Relationship(back_populates="sections")


class SubjectBase(SQLModel):
    #: Both unique **inside a school** - two schools may each have a "Mathematics".
    #: `Subject` adds the (school_id, name) / (school_id, code) unique indexes.
    name: str = Field(index=True)
    code: str = Field(index=True)


class Subject(SubjectBase, TenantMixin, table=True):
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_school_name"),
        UniqueConstraint("school_id", "code", name="uq_subject_school_code"),
    )

    id: int | None = Field(default=None, primary_key=True)
