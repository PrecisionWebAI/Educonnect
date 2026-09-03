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


class HomeworkSubmissionCreate(BaseModel):
    homework_id: int
    student_id: int
    content_url: str | None = None
    status: SubmissionStatus


class HomeworkSubmissionRead(HomeworkSubmissionBase):
    id: int


class ClassDiaryCreate(ClassDiaryBase):
    pass


class ClassDiaryRead(ClassDiaryBase):
    id: int
