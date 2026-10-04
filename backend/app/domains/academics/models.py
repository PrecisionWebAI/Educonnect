from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class GradeClassBase(SQLModel):
    name: str = Field(unique=True, index=True)
    level: int
    #: School stage for grouping/reporting: pre_primary, primary, middle,
    #: secondary, senior_secondary. Stored rather than derived from the name, so
    #: a school that calls them "Std VI" still reports correctly.
    stage: str = Field(default="primary")


class GradeClass(GradeClassBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sections: list[Section] = Relationship(back_populates="grade_class")


class SectionBase(SQLModel):
    name: str
    grade_class_id: int = Field(foreign_key="gradeclass.id")


class Section(SectionBase, table=True):
    #: Two "A" sections inside one class is always a mistake, so the database
    #: rejects it instead of relying on application code (the "planned" unique
    #: constraint in `info/db_mapping.txt`).
    __table_args__ = (
        UniqueConstraint("grade_class_id", "name", name="uq_section_grade_name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    grade_class: GradeClass = Relationship(back_populates="sections")


class SubjectBase(SQLModel):
    name: str = Field(unique=True, index=True)
    code: str = Field(unique=True, index=True)


class Subject(SubjectBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
