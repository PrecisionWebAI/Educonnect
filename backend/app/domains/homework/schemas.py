from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import (

    ClassLogBase,
    HomeworkAssignmentBase,
    HomeworkSubmissionBase,
    SubmissionStatus,
)


class HomeworkAssignmentCreate(CanonicalRequest, HomeworkAssignmentBase):
    pass


class HomeworkAssignmentRead(HomeworkAssignmentBase):
    id: UUID
    subject: str | None = None
    className: str | None = None
    due: str | None = None
    assignedBy: str | None = None


class HomeworkSubmissionCreate(CanonicalRequest):
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


class ClassLogCreate(CanonicalRequest, ClassLogBase):
    pass


class ClassLogRead(ClassLogBase):
    id: UUID


class DiaryEntryRead(BaseModel):
    id: UUID
    className: str
    day: str
    subject: str
    topic: str
    homework: str
    activity: str
