"""The shapes the Exams plan serves. Snake_case, like the rest of Phase 5-7's screens."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

#: A paper's maximum is a real number with two decimals, and so is a score.
_EXACT = {"max_digits": 6, "decimal_places": 2}


class PaperScheduleIn(BaseModel):
    """One date-sheet row. Name **one** of two ways to say which subject sits it.

    * `classroom_subject_id` - one section's own subject; its chapters are
      `chapter_ids` (that section's chapter rows);
    * `subject_name` - every section of the class that already has an active subject of
      that name (case-insensitive). Two or more sections share one paper group, whose
      chapters are the **names** in `chapters`; a section without that subject is
      reported back as skipped, never created.
    """

    classroom_subject_id: UUID | None = None
    subject_name: str | None = None
    #: Which class sits a `subject_name` row. A class exam inherits the exam's class;
    #: a school-wide exam names it per row.
    class_id: UUID | None = None
    exam_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    #: What this sitting is out of. The only place a maximum is written.
    max_marks: Decimal = Field(default=Decimal("100.00"), **_EXACT)
    passing_marks: Decimal | None = Field(default=None, **_EXACT)
    room: str | None = None
    note: str | None = None
    #: The chapters this paper covers, as ids of **that section subject's** chapters.
    chapter_ids: list[UUID] = Field(default_factory=list)
    #: The chapters of a shared (or name-resolved) paper, by name, in order.
    chapters: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_way_to_name_the_subject(self):
        if (self.classroom_subject_id is None) == (
            not (self.subject_name or "").strip()
        ):
            raise ValueError(
                "Name the subject with exactly one of classroom_subject_id or subject_name."
            )
        return self


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
    """One sitting: a section's own subject, on its own date, maybe in a shared group."""

    id: UUID
    exam_id: UUID
    classroom_subject_id: UUID
    #: The section that sits it, read from the section subject.
    classroom_id: UUID
    class_id: UUID
    #: `Class 9-A`.
    section: str = ""
    #: The section subject's own name.
    subject: str
    #: The shared paper's title when the group has one; else the row shows `subject`.
    title: str
    paper_group_id: UUID | None = None
    #: True when the shared paper can no longer be edited (marks or publication exist).
    group_locked: bool = False
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
    #: True when this paper is in a group and the caller may give it its own paper.
    can_detach: bool = False


class PaperGroupRead(BaseModel):
    """A shared question paper: its title, chapters and the sections that sit it."""

    id: UUID
    exam_id: UUID
    display_title: str | None = None
    chapters: list[str] = Field(default_factory=list)
    paper_ids: list[UUID] = Field(default_factory=list)
    locked: bool = False


class PaperGroupUpdateIn(BaseModel):
    """Edit a shared paper. A field that is not sent is left alone."""

    display_title: str | None = None
    #: The whole chapter list, by name; replaces the old one.
    chapters: list[str] | None = None
    #: Applied to every paper of the group (their marks cannot exist: that locks it).
    max_marks: Decimal | None = Field(default=None, **_EXACT)
    passing_marks: Decimal | None = Field(default=None, **_EXACT)


class SkippedSectionRead(BaseModel):
    """A section that has no active subject of the requested name - no paper was made."""

    classroom_id: UUID
    section: str
    subject: str


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
    groups: list[PaperGroupRead] = Field(default_factory=list)
    #: Sections left out because they have no subject of a requested name (create only).
    skipped: list[SkippedSectionRead] = Field(default_factory=list)


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
    classroom_subject_id: UUID
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
    classroom_subject_id: UUID
    classroom_id: UUID
    #: `Class 9-A` - a result sheet of a class exam has one column per section paper.
    section: str = ""
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
