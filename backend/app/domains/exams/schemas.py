from typing import Any

from pydantic import BaseModel

from .models import ExamPaperBase, ExamResultBase, ExamTermBase


class ExamTermCreate(ExamTermBase):
    pass


class ExamTermRead(ExamTermBase):
    id: int


class ExamPaperCreate(ExamPaperBase):
    content_json: dict[str, Any]


class ExamPaperRead(ExamPaperBase):
    id: int
    content_json: dict[str, Any]


class ExamResultCreate(ExamResultBase):
    pass


class ExamResultRead(ExamResultBase):
    id: int


class BulkExamResultCreate(BaseModel):
    exam_paper_id: int
    results: list[
        dict
    ]  # [{"student_id": 1, "marks_obtained": 95.5, "ai_feedback": "Good"}]
