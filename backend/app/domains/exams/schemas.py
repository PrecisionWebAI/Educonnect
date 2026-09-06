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


class QuestionItemRead(BaseModel):
    id: int
    subject: str
    chapter: str
    type: str
    difficulty: str
    text: str
    marks: int


class PaperDraftFullRead(BaseModel):
    id: int
    title: str
    subject: str
    status: str
    questions: int
    totalMarks: int
    updated: str


class ExamScheduleItemRead(BaseModel):
    id: int
    subject: str
    date: str
    time: str
    rooms: list[str]
    invigilator: str


class ExamMarkingRowRead(BaseModel):
    id: int
    student: str
    subject: str
    obtained: float
    max: float
    status: str


class PaperReviewItemRead(BaseModel):
    id: int
    title: str
    subject: str
    author: str
    due: str


class ResultRowRead(BaseModel):
    id: int
    exam: str
    className: str
    passRate: float
    avgScore: float
    topper: str


class DisputeRowRead(BaseModel):
    id: int
    student: str
    exam: str
    subject: str
    reason: str
    status: str


class MarksRowRead(BaseModel):
    subject: str
    max: float
    obtained: float


class MarksEntryRead(BaseModel):
    studentId: int
    studentName: str
    className: str
    exam: str
    rows: list[MarksRowRead]
