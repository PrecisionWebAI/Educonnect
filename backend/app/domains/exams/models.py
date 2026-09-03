import enum
from datetime import date
from typing import Any

from sqlmodel import JSON, Field, SQLModel


class ExamPaperStatus(enum.StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"


class ExamTermBase(SQLModel):
    name: str  # e.g. "Midterm 2026"
    grade_class_id: int = Field(foreign_key="gradeclass.id")
    start_date: date
    end_date: date


class ExamTerm(ExamTermBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ExamPaperBase(SQLModel):
    exam_term_id: int = Field(foreign_key="examterm.id")
    subject_id: int = Field(foreign_key="subject.id")
    status: ExamPaperStatus = Field(default=ExamPaperStatus.draft)


class ExamPaper(ExamPaperBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Storing AI generated paper structure in JSON
    content_json: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)


class ExamResultBase(SQLModel):
    exam_paper_id: int = Field(foreign_key="exampaper.id")
    student_id: int = Field(foreign_key="studentprofile.id")
    marks_obtained: float
    ai_feedback: str | None = None


class ExamResult(ExamResultBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
