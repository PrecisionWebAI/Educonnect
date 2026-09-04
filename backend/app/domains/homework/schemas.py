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
    id: int
    subject: str | None = None
    className: str | None = None
    due: str | None = None
    assignedBy: str | None = None


class HomeworkSubmissionCreate(BaseModel):
    homework_id: int
    student_id: int
    content_url: str | None = None
    status: SubmissionStatus


class HomeworkSubmissionRead(HomeworkSubmissionBase):
    id: int


class SubmissionItemRead(BaseModel):
    id: int
    homeworkTitle: str
    student: str
    status: str
    submittedAt: str


class ClassDiaryCreate(ClassDiaryBase):
    pass


class ClassDiaryRead(ClassDiaryBase):
    id: int


class DiaryEntryRead(BaseModel):
    id: int
    className: str
    day: str
    subject: str
    topic: str
    homework: str
    activity: str
