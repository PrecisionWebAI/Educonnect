from datetime import date

from sqlmodel import Field, SQLModel


class TeacherProfileBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", unique=True)
    department: str
    qualification: str
    joining_date: date


class TeacherProfile(TeacherProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TeacherAssignmentBase(SQLModel):
    """Maps a teacher to a specific class and subject."""

    teacher_id: int = Field(foreign_key="teacherprofile.id")
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")
    subject_id: int = Field(foreign_key="subject.id")


class TeacherAssignment(TeacherAssignmentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ClassTeacherAssignmentBase(SQLModel):
    """Maps a teacher to a specific class/section as the official Class Teacher."""

    teacher_id: int = Field(foreign_key="teacherprofile.id")
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")


class ClassTeacherAssignment(ClassTeacherAssignmentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
