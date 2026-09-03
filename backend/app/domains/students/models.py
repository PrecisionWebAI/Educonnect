from datetime import date

from sqlmodel import Field, SQLModel


class StudentProfileBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", unique=True)
    admission_number: str = Field(unique=True, index=True)
    date_of_birth: date
    guardian_name: str
    grade_class_id: int | None = Field(default=None, foreign_key="gradeclass.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")


class StudentProfile(StudentProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
