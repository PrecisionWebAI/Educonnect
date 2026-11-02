from uuid import UUID
from pydantic import BaseModel

from .models import (
    ClassDiaryBase,
    HomeworkAssignmentBase,
    HomeworkSubmissionBase,
    SubmissionStatus,
)


class HomeworkAssignmentCreate(HomeworkAssignmentBase):
    pass


class HomeworkAssignmentRead(HomeworkAssignmentBase):
    id: UUID
    subject: str | None = None
    className: str | None = None
    due: str | None = None
    assignedBy: str | None = None


class HomeworkSubmissionCreate(BaseModel):
    homework_id: UUID
    student_id: UUID
    content_url: str | None = None
    status: SubmissionStatus


class HomeworkSubmissionRead(HomeworkSubmissionBase):
    id: UUID


class SubmissionItemRead(BaseModel):
    id: UUID
    homeworkTitle: str
    student: str
    status: str
    submittedAt: str


class ClassDiaryCreate(ClassDiaryBase):
    pass


class ClassDiaryRead(ClassDiaryBase):
    id: UUID


class DiaryEntryRead(BaseModel):
    id: UUID
    className: str
    day: str
    subject: str
    topic: str
    homework: str
    activity: str
