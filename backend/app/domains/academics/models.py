from sqlmodel import Field, Relationship, SQLModel


class GradeClassBase(SQLModel):
    name: str = Field(unique=True, index=True)
    level: int


class GradeClass(GradeClassBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sections: list[Section] = Relationship(back_populates="grade_class")


class SectionBase(SQLModel):
    name: str
    grade_class_id: int = Field(foreign_key="gradeclass.id")


class Section(SectionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    grade_class: GradeClass = Relationship(back_populates="sections")


class SubjectBase(SQLModel):
    name: str = Field(unique=True, index=True)
    code: str = Field(unique=True, index=True)


class Subject(SubjectBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
