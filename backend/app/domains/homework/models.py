import enum
from datetime import date

from sqlmodel import Field, SQLModel


class SubmissionStatus(enum.StrEnum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class HomeworkAssignmentBase(SQLModel):
    title: str
    description: str
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")
    subject_id: int = Field(foreign_key="subject.id")
    teacher_id: int = Field(foreign_key="teacherprofile.id")
    due_date: date


class HomeworkAssignment(HomeworkAssignmentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class HomeworkSubmissionBase(SQLModel):
    homework_id: int = Field(foreign_key="homeworkassignment.id")
    student_id: int = Field(foreign_key="studentprofile.id")
    content_url: str | None = None
    status: SubmissionStatus = Field(default=SubmissionStatus.pending)
    teacher_feedback: str | None = None


class HomeworkSubmission(HomeworkSubmissionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ClassDiaryBase(SQLModel):
    student_id: int = Field(foreign_key="studentprofile.id")
    teacher_id: int = Field(foreign_key="teacherprofile.id")
    date: date
    note: str


class ClassDiary(ClassDiaryBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
