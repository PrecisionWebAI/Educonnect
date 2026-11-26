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


class LadderRungRead(BaseModel):
    """One rung of a grading ladder: `>= min_percent` earns `grade`."""

    min_percent: Decimal
    grade: str


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
    #: Who takes it. `taken_by_*` is the teacher who actually does (the assigned one
    #: unless someone else was picked); `is_temporary` is **derived live** - true when
    #: that is not the section subject's assigned teacher (the Temporary card).
    taken_by_employee_id: UUID | None = None
    taken_by_name: str | None = None
    assigned_teacher_id: UUID | None = None
    assigned_teacher_name: str | None = None
    is_temporary: bool = False
    #: The paper's own pass line (see `marking.py`): `marks` or `grade`.
    pass_mode: str | None = None
    pass_percent: Decimal | None = None
    passing_grade: str | None = None
    #: `auto` / `na` / `manual` - how this paper's Grade column works.
    grade_mode: str = "na"
    #: This paper's own copy of the grading ladder (highest first); empty on older papers.
    grading_scale: list[LadderRungRead] = Field(default_factory=list)
    #: True when the subject teacher has written a syllabus (the row's Syllabus button).
    has_syllabus: bool = False
    #: True when this caller may write this paper's syllabus (its subject teacher, the
    #: class teacher, or leadership) - School Exam papers only.
    can_syllabus: bool = False
    #: Who writes this subject's syllabus: the assigned teacher unless another is picked
    #: (then `syllabus_is_temporary`, the "T" badge).
    syllabus_by_employee_id: UUID | None = None
    syllabus_by_name: str | None = None
    syllabus_is_temporary: bool = False
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
    #: What guardians and students read with the schedule (editable any time).
    family_note: str | None = None
    datesheet_published_at: datetime | None = None
    #: Set when the date sheet was archived (hidden from the list, never deleted).
    archived_at: datetime | None = None
    #: True when this caller may set and publish the date sheet (the class teacher of the
    #: section, or leadership) - School Exams only.
    can_manage: bool = False
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
    #: The teacher's own grade - needed for every scored child when the paper is `manual`.
    grade: str | None = None


class GradeEntryIn(BaseModel):
    student_id: UUID
    grade: str | None = None


class GradeModeIn(BaseModel):
    """Change how a paper's Grade column works - also after it was published."""

    grade_mode: str
    #: Needed for every scored child when the new mode is `manual` (the ones already on
    #: file are kept).
    grades: list[GradeEntryIn] = Field(default_factory=list)


class MarksSaveIn(BaseModel):
    entries: list[MarkEntryIn] = Field(default_factory=list)
    #: `auto` / `na` / `manual` - how this paper's Grade column works (before publishing).
    grade_mode: str | None = None


class MarkChangeIn(BaseModel):
    """A correction made **after** publication - audited, and the family is told."""

    marks_obtained: Decimal | None = Field(default=None, **_EXACT)
    absent: bool | None = None
    grade: str | None = None
    reason: str | None = None


class PaperMarkRowRead(BaseModel):
    student_id: UUID
    name: str
    admission_number: str | None = None
    section: str | None = None
    marks_obtained: Decimal | None = None
    absent: bool = False
    grade: str | None = None
    #: `obtained / total * 100` to 2 places; empty for an absent or unmarked child.
    percentage: Decimal | None = None
    #: `True` pass, `False` fail, empty for an absent or unmarked child (by this paper's
    #: own pass line).
    passed: bool | None = None
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


class MarkingDefaultsRead(BaseModel):
    """What a new paper's pass line starts from, for one total.

    The school only supplies **starting values**: the teacher may change any of them for
    this one paper (and a custom passing grade is added to this paper's copy of the
    ladder, never to the school's).
    """

    total_marks: Decimal
    #: 33% of the total (100 -> 33, 50 -> 16.5, 20 -> 6.6).
    pass_marks: Decimal
    #: The school's default pass percentage (33 unless the school set another).
    pass_percent: Decimal
    #: The passing grade that percentage earns on the ladder ("D" for 33).
    passing_grade: str | None = None
    #: The school's ladder, highest first.
    ladder: list[LadderRungRead] = Field(default_factory=list)
    #: `marks` / `grades` / `both` - what a result shows beside a child's name.
    display_mode: str = "both"


class ClassTestCreateIn(BaseModel):
    """Schedule one class test for one or several sections of the **same class**.

    A section subject belongs to one section only, so the subject is named once - by the
    anchor section's own row - and every other chosen section is matched by that
    subject's name; a section that has no such subject is refused, never invented.
    """

    #: The anchor: the section subject the teacher picked (from the course list).
    classroom_subject_id: UUID
    #: Every section that sits the test (at least the anchor's), all of one class.
    section_ids: list[UUID] = Field(min_length=1)
    exam_date: date
    total_marks: Decimal = Field(gt=0, **_EXACT)
    #: Who takes the test. Leave empty for each section's assigned teacher.
    taken_by_employee_id: UUID | None = None
    family_note: str | None = None
    #: Free text: what will come in the test (chapters, topics, anything).
    syllabus_text: str | None = None
    #: How the Grade column of the marks sheet works: `na` (default), `auto`, `manual`.
    grade_mode: str | None = None
    # --- this test's own pass line (marks or grade) ---
    pass_mode: str | None = None
    passing_marks: Decimal | None = Field(default=None, **_EXACT)
    passing_grade: str | None = None
    custom_min_percent: Decimal | None = Field(default=None, **_EXACT)
    #: Send true after the duplicate warning was read and the teacher chose "create anyway".
    confirm_duplicate: bool = False
    academic_year_id: UUID | None = None


class ClassTestUpdateIn(BaseModel):
    """Edit a class test. A field that is **not sent** is left alone.

    `taken_by_employee_id: null` (sent) means "back to each section's assigned teacher";
    `family_note: null` or `""` clears the note.
    """

    exam_date: date | None = None
    total_marks: Decimal | None = Field(default=None, gt=0, **_EXACT)
    taken_by_employee_id: UUID | None = None
    family_note: str | None = None
    #: `null` or `""` clears it.
    syllabus_text: str | None = None
    grade_mode: str | None = None
    pass_mode: str | None = None
    passing_marks: Decimal | None = Field(default=None, **_EXACT)
    passing_grade: str | None = None
    custom_min_percent: Decimal | None = Field(default=None, **_EXACT)
    #: The full list of sections that should sit it (sections can be added or removed).
    section_ids: list[UUID] | None = Field(default=None, min_length=1)
    confirm_duplicate: bool = False


class DuplicateExamRead(BaseModel):
    """Another test for the same section, subject and date - shown before saving."""

    exam_id: UUID
    name: str
    exam_date: date | None = None
    subject: str
    total_marks: Decimal
    section: str
    created_by: str | None = None
    status: str


class SchoolExamRowIn(BaseModel):
    """One subject of the date sheet: its date, its total, its own pass line."""

    classroom_subject_id: UUID
    exam_date: date
    total_marks: Decimal = Field(gt=0, **_EXACT)
    pass_mode: str | None = None
    passing_marks: Decimal | None = Field(default=None, **_EXACT)
    passing_grade: str | None = None
    custom_min_percent: Decimal | None = Field(default=None, **_EXACT)
    #: `na` (default), `auto` or `manual` - how this subject's Grade column works.
    grade_mode: str | None = None
    #: Who takes this subject's paper. Empty = the subject's assigned teacher; anyone else
    #: is a temporary teacher (the same S / T idea as a class test).
    taken_by_employee_id: UUID | None = None


class SchoolExamCreateIn(BaseModel):
    """Set the date sheet of one section for one school exam (Unit Test ... Custom)."""

    #: The section whose date sheet this is (its own courses are the rows).
    classroom_id: UUID
    exam_type: str
    #: The teacher's own name for the exam - required when the type is `custom`.
    custom_name: str | None = None
    family_note: str | None = None
    rows: list[SchoolExamRowIn] = Field(min_length=1)
    academic_year_id: UUID | None = None
    #: Other sections of the same class that get the same sheet (each in its own date
    #: sheet). A subject a section does not have is left off that section's sheet.
    section_ids: list[UUID] | None = None
    #: Send true after the duplicate warning was read and "create anyway" was chosen.
    confirm_duplicate: bool = False


class SectionChoiceRead(BaseModel):
    """A class-section that can be picked next to the one on screen."""

    classroom_id: UUID
    label: str
    #: The names of the section's active subjects (to know which sections can sit a test).
    subjects: list[str] = Field(default_factory=list)


class SchoolExamUpdateIn(BaseModel):
    """Edit a date sheet. A field that is **not sent** is left alone; `rows`, when sent,
    is the whole sheet (a subject left out is taken off it)."""

    exam_type: str | None = None
    custom_name: str | None = None
    family_note: str | None = None
    rows: list[SchoolExamRowIn] | None = Field(default=None, min_length=1)
    confirm_duplicate: bool = False


class SyllabusIn(BaseModel):
    """What the subject teacher says will come in the exam - free text."""

    syllabus_text: str | None = None
    #: Who writes it. Left out = unchanged; `null` = back to the assigned teacher.
    by_employee_id: UUID | None = None


class SyllabusRead(BaseModel):
    paper_id: UUID
    exam_id: UUID
    subject: str
    section: str
    exam_name: str
    syllabus_text: str | None = None
    #: True when this caller may change it.
    can_edit: bool = False


class MarkAuditRead(BaseModel):
    """One correction made to a published mark: who, when, from what to what."""

    student_id: UUID
    student_name: str
    old_value: Decimal | None = None
    new_value: Decimal | None = None
    old_absent: bool = False
    new_absent: bool = False
    changed_by: str | None = None
    changed_at: datetime
    reason: str | None = None


# ---------------------------------------------------------------------------
# The result overview: per test, subject-wise so far, and overall - one kind at a time
# ---------------------------------------------------------------------------


class OverviewStatsRead(BaseModel):
    """What a section did on one test (the teacher's class view, never a family's)."""

    #: Children who have a score (absent children are not counted here).
    marked: int = 0
    absent: int = 0
    average_marks: Decimal | None = None
    average_percentage: Decimal | None = None
    highest: Decimal | None = None
    lowest: Decimal | None = None
    passed: int = 0
    failed: int = 0


class OverviewTestRead(BaseModel):
    """One test (one paper) as a column of the result table."""

    paper_id: UUID
    exam_id: UUID
    exam_name: str
    exam_type: str | None = None
    subject: str
    section: str = ""
    exam_date: date | None = None
    total_marks: Decimal
    pass_mode: str | None = None
    pass_percent: Decimal | None = None
    passing_marks: Decimal | None = None
    passing_grade: str | None = None
    #: Only a published test counts anywhere in the overview; this is always `True` for
    #: a family, and tells the staff which tests are still waiting to be published.
    published: bool = True
    #: The class view's figures; empty for a family.
    stats: OverviewStatsRead | None = None


class OverviewEntryRead(BaseModel):
    """One child's result on one test."""

    paper_id: UUID
    obtained: Decimal | None = None
    #: Shown as "Absent" and left out of every percentage.
    absent: bool = False
    percentage: Decimal | None = None
    grade: str | None = None
    #: By **that test's own** pass line; empty for an absent or unmarked child.
    passed: bool | None = None


class OverviewSubjectRead(BaseModel):
    """One subject across all the tests so far: `sum obtained / sum total`."""

    subject: str
    obtained: Decimal
    total: Decimal
    percentage: Decimal | None = None
    grade: str | None = None
    tests_counted: int = 0
    tests_absent: int = 0


class OverviewTotalRead(BaseModel):
    """Every subject together: `sum obtained / sum total` over all the tests so far."""

    obtained: Decimal = Decimal(0)
    total: Decimal = Decimal(0)
    percentage: Decimal | None = None
    grade: str | None = None
    tests_counted: int = 0
    tests_absent: int = 0
    tests_passed: int = 0
    tests_failed: int = 0


class OverviewStudentRead(BaseModel):
    student_id: UUID
    name: str
    admission_number: str | None = None
    classroom_id: UUID | None = None
    section: str = ""
    entries: list[OverviewEntryRead] = Field(default_factory=list)
    subjects: list[OverviewSubjectRead] = Field(default_factory=list)
    overall: OverviewTotalRead = Field(default_factory=OverviewTotalRead)


class ResultOverviewRead(BaseModel):
    """Class Test results **or** School Exam results for the year on screen - never mixed."""

    #: `class_test` or `school_exam`.
    kind: str
    academic_year_id: UUID | None = None
    #: `section` (the class view: staff) or `family` (the caller's own children).
    view: str
    classroom_id: UUID | None = None
    section: str = ""
    tests: list[OverviewTestRead] = Field(default_factory=list)
    students: list[OverviewStudentRead] = Field(default_factory=list)
    #: Tests that exist but are not published yet (staff only; a family never hears of them).
    unpublished: int = 0
    #: `marks` / `grades` / `both` - what the screen should show.
    display_mode: str = "both"
