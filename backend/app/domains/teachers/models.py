from datetime import date

from sqlmodel import Field, SQLModel


class TeacherProfileBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", unique=True)
    department: str
    qualification: str
    joining_date: date


class TeacherProfile(TeacherProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
