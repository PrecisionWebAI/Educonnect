import enum
from datetime import date
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class SubmissionStatus(enum.StrEnum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class HomeworkAssignmentBase(SQLModel):
    title: str
    description: str
    classroom_id: UUID = Field(foreign_key="classroom.id")
    section_id: UUID | None = Field(default=None, foreign_key="section.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    due_date: date


class HomeworkAssignment(HomeworkAssignmentBase, TenantMixin, UUIDMixin, table=True):
    pass


class HomeworkSubmissionBase(SQLModel):
    homework_id: UUID = Field(foreign_key="homeworkassignment.id")
    student_id: UUID = Field(foreign_key="studentprofile.id")
    content_url: str | None = None
    status: SubmissionStatus = Field(default=SubmissionStatus.pending)
    teacher_feedback: str | None = None


class HomeworkSubmission(HomeworkSubmissionBase, TenantMixin, UUIDMixin, table=True):
    pass


class ClassDiaryBase(SQLModel):
    student_id: UUID = Field(foreign_key="studentprofile.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    #: The class / section the entry belongs to. Back-filled from the student's
    #: placement, so a diary entry is reachable from the classroom it was
    #: written for (the classroom is the hub everything hangs off).
    classroom_id: UUID | None = Field(
        default=None, foreign_key="classroom.id", index=True
    )
    section_id: UUID | None = Field(default=None, foreign_key="section.id", index=True)
    date: date
    note: str


class ClassDiary(ClassDiaryBase, TenantMixin, UUIDMixin, table=True):
    pass
