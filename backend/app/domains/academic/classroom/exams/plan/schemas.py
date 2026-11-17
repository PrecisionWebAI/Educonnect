"""The shapes the Exams plan serves. Snake_case, like the rest of Phase 5-7's screens."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

#: A paper's maximum is a real number with two decimals, and so is a score.
_EXACT = {"max_digits": 6, "decimal_places": 2}


class PaperScheduleIn(BaseModel):
    """One row of the date sheet a caller sends."""

    subject_id: UUID
    #: Which class sits this paper. Needed for a school-wide exam (each class has its
    #: own paper per subject); a class exam inherits the exam's class.
    class_id: UUID | None = None
    exam_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    #: What this sitting is out of. The only place a maximum is written.
    max_marks: Decimal = Field(default=Decimal("100.00"), **_EXACT)
    passing_marks: Decimal | None = Field(default=None, **_EXACT)
    room: str | None = None
    note: str | None = None
    #: The chapters this paper covers (Phase 5 `chapter` ids).
    chapter_ids: list[UUID] = Field(default_factory=list)


class ExamCreateIn(BaseModel):
    name: str
    term: str | None = None
    exam_type: str | None = None
    #: `class` (one class sits it) or `school` (every class does - the office only).
    scope: str = "class"
    class_id: UUID | None = None
    classroom_id: UUID | None = None
    academic_year_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    #: `draft` or `scheduled`. Publishing is its own endpoint, on purpose.
    status: str = "draft"
    note: str | None = None
    papers: list[PaperScheduleIn] = Field(default_factory=list)


class ExamUpdateIn(BaseModel):
    """What may change after the fact. `None` means "leave it alone"."""

    name: str | None = None
    term: str | None = None
    exam_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None
    status: str | None = None
    #: When given, the date sheet is **replaced** row by row (the whole set wins).
    papers: list[PaperScheduleIn] | None = None


class ExamPaperRead(BaseModel):
    """One sitting as the plan screen draws it."""

    id: UUID
    exam_id: UUID
    subject_id: UUID
    subject: str
    class_id: UUID
    exam_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    max_marks: Decimal
    passing_marks: Decimal | None = None
    room: str | None = None
    note: str | None = None
    published_at: datetime | None = None
    chapter_ids: list[UUID] = Field(default_factory=list)
    chapters: list[str] = Field(default_factory=list)
    marks_entered: int = 0
    #: True when this caller may change the paper (the office, or its subject teacher).
    can_edit: bool = False


class ExamRead(BaseModel):
    id: UUID
    name: str
    term: str | None = None
    exam_type: str | None = None
    scope: str
    status: str
    class_id: UUID | None = None
    classroom_id: UUID | None = None
    academic_year_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None
    published_at: datetime | None = None
    papers: list[ExamPaperRead] = Field(default_factory=list)


class MarkEntryIn(BaseModel):
    """One child's score on the paper being saved."""

    student_id: UUID
    marks_obtained: Decimal | None = Field(default=None, **_EXACT)
    #: An absence is a fact of its own: the score is empty, not zero.
    absent: bool = False


class MarksSaveIn(BaseModel):
    entries: list[MarkEntryIn] = Field(default_factory=list)


class MarkChangeIn(BaseModel):
    """A correction made **after** publication - audited, and the family is told."""

    marks_obtained: Decimal | None = Field(default=None, **_EXACT)
    absent: bool | None = None
    reason: str | None = None


class PaperMarkRowRead(BaseModel):
    student_id: UUID
    name: str
    admission_number: str | None = None
    section: str | None = None
    marks_obtained: Decimal | None = None
    absent: bool = False
    grade: str | None = None
    #: True when this row was changed after the paper was published (audit exists).
    changed_after_publish: bool = False


class MarksSavedRead(BaseModel):
    paper_id: UUID
    exam_id: UUID
    exam_status: str
    written: int
    absent: int
    rows: list[PaperMarkRowRead] = Field(default_factory=list)


class ResultMarkRead(BaseModel):
    """One subject on a child's result."""

    paper_id: UUID
    subject_id: UUID
    subject: str
    max_marks: Decimal
    obtained: Decimal | None = None
    absent: bool = False
    grade: str | None = None
    passed: bool | None = None


class ResultRowRead(BaseModel):
    """One child's line: every paper, the total, the grade and the rank."""

    student_id: UUID
    name: str
    admission_number: str | None = None
    class_name: str | None = None
    section: str | None = None
    marks: list[ResultMarkRead] = Field(default_factory=list)
    total: Decimal = Decimal("0")
    out_of: Decimal = Decimal("0")
    percent: Decimal | None = None
    grade: str | None = None
    #: Competition rank within the cohort the setting names; `None` when the student
    #: sat nothing, or when the school turned ranks off.
    rank: int | None = None
    #: The teachers' line for this child: how many papers they were absent for.
    absent_count: int = 0
    passed_all: bool | None = None


class ResultPaperRead(BaseModel):
    """A paper's own figures - the teachers' and the principal's view."""

    paper_id: UUID
    subject_id: UUID
    subject: str
    exam_date: date | None = None
    max_marks: Decimal
    passing_marks: Decimal | None = None
    published: bool = False
    average: Decimal | None = None
    highest: Decimal | None = None
    lowest: Decimal | None = None
    entered: int = 0
    absent: int = 0


class ResultsRead(BaseModel):
    exam_id: UUID
    name: str
    status: str
    #: `section` / `class` / `school` - what the rank is against (the school's setting).
    rank_display: str
    #: `percentage` / `grade` - which number the report card prints.
    grade_scale: str
    papers: list[ResultPaperRead] = Field(default_factory=list)
    rows: list[ResultRowRead] = Field(default_factory=list)
    #: Papers whose marks nobody has published yet - the principal's to-do list.
    unpublished: list[UUID] = Field(default_factory=list)
    #: True when `rows` was narrowed to the caller's own children (student/parent).
    own_only: bool = False
