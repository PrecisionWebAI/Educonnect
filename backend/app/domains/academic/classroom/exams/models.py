# ============================================================
# Exam/Paper models (blueprint §2.3) — directly in exams domain.
# (Old ExamTerm/ExamPaper/ExamResult tables hata diye — sabse
# pyare current PaperBuilder backend hi yahan hai.)
#
# Kya-kya hai:
#   PaperDraft     — AI paper ka draft (blueprint + coverage +
#                    part_a AI questions + part_b teacher questions)
#   GenerationJob  — async generation ka record (status polling,
#                    LangGraph checkpoint Phase 3)
#   ExamSource     — content library row (Phase 3 RAG ke liye base)
# ============================================================

import enum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import JSON, Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin

# ------------------------------------------------------------
# Enums — database mein value string hoti hai (StrEnum → readable)
# ------------------------------------------------------------


class PaperStatus(enum.StrEnum):
    """Paper ki state — wahi flow jo existing ExamPaperStatus: draft → in_review → approved."""

    draft = "draft"
    in_review = "in_review"
    approved = "approved"


class CoverageMode(enum.StrEnum):
    """Distribution ka mode — FRONTEND ke DistributionMode ("marks"/"percent") se match.
    auto = kuch assign nahi hua → sab marks Random bucket se bharoge."""

    auto = "auto"
    marks = "marks"
    percent = "percent"


class GenerationJobStatus(enum.StrEnum):
    """Async job ki lifecycle. Frontend isi ko poll karega."""

    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    canceled = "canceled"


class SourceType(enum.StrEnum):
    """Content library source ka type — frontend ke AddType se match."""

    pdf = "pdf"
    image = "image"
    url = "url"
    text = "text"
    bank = "bank"


# ------------------------------------------------------------
# PaperDraft — AI paper builder ka main table
# ------------------------------------------------------------


class PaperDraft(TenantMixin, UUIDMixin, table=True):
    """Ek AI paper ka draft. Har field blueprint §2.3.2 se aayi hai.

    Do hisse hain:
      A) PAPER CONTEXT (Phase 2) — AI ko ye batana zaroori hai ki paper
         KISKE liye hai: class/subject/board/exam type/language/chapters.
         Bina inke model generic question bana dega ("What is science?"),
         jo Class 8 Science ke chapter ke hisaab se galat hoga.
      B) PLAN + OUTPUT — blueprint (spec), coverage_plan (intent),
         part_a (AI questions), part_b (teacher questions).

    JSON columns (`sa_type=JSON`):
      chapters      — ["Microorganisms", "Force & Pressure"]
      sources       — [{id, sourceType, label, fileName, url, chapters, ...}]
      instructions  — ["Use simple English.", "Source-only answers"]
      scope         — {includeTopics: [], excludeTopics: [], conceptCoverage: []}
      constraints   — {noDuplicates: true, minDiagram: 1, ...}
      blueprint     — [{type, count, marksEach}, ...]  (Marks Contract ka spec)
      coverage_plan — {mode, chapters: [{chapter, targetMarks, topics}]}
      part_a        — AI ke questions ({sections: [...]})
      part_b        — teacher ke custom questions ([...])
    """

    title: str
    #: The section's own subject (`classroomsubject.id`). NULL while the builder only
    #: knows the wording (`class_name` / `subject` below); the class and section are read
    #: from it when it is set.
    classroom_subject_id: UUID | None = Field(
        default=None, foreign_key="classroomsubject.id", index=True
    )
    #: The shared question paper this draft is (one draft per group)...
    paper_group_id: UUID | None = Field(
        default=None, foreign_key="exam_paper_group.id", index=True, unique=True
    )
    #: ...or the single sitting it is for (a detached paper). Both NULL = pre-exam draft.
    exam_paper_id: UUID | None = Field(
        default=None, foreign_key="exam_paper.id", index=True, unique=True
    )
    created_by: UUID | None = Field(default=None, foreign_key="app_user.id")

    # ---- (A) Paper context — AI prompt ka fuel (Phase 2) ----
    class_name: str = Field(default="")  # "8", "10-A" — display + prompt
    subject: str = Field(default="")  # "Science"
    board: str = Field(default="")  # "CBSE" | "ICSE" | "State"
    exam_type: str = Field(default="")  # "Unit Test" | "Half Yearly" | ...
    language: str = Field(default="English")
    chapters: list[str] = Field(default_factory=list, sa_type=JSON)

    # Frontend ke Step-2 (Source) ka data — AI ko "sirf isi se banao" kehne ke liye
    sources: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)
    instructions: list[str] = Field(default_factory=list, sa_type=JSON)
    scope: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    constraints: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # ---- (B) Plan + output ----
    total_marks: int = Field(default=0)  # Marks Contract ka source of truth
    duration_minutes: int = Field(default=60)

    blueprint: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    coverage_mode: CoverageMode = Field(default=CoverageMode.auto)
    coverage_plan: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    part_a: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # AI
    part_b: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # Teacher

    status: PaperStatus = Field(default=PaperStatus.draft)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# GenerationJob — async generation ka record (Phase 3 ARQ ke saath)
# ------------------------------------------------------------


class GenerationJob(TenantMixin, UUIDMixin, table=True):
    """Ek generation run ka record.

    - `status` = single source of truth for progress polling.
    - `graph_state` = LangGraph checkpoint (resume-after-crash, Phase 3).
    - `blueprint_snapshot` / `coverage_snapshot` = job shuru hone par
      kya config tha (baad mein change bhi ho to job wahi generate kare).
    - `trace_id` = har job ka unique log id (debugging + logs).
    - `config_snapshot` = **stateless generate** ka poora config (Basics + Source
      + Blueprint + Coverage + part_b). Jab teacher "blueprint DB mein save mat
      karo" chahta hai, tab plan yahin freeze hota hai (paperdraft row nahi banti).
    - `result_snapshot` = stateless flow mein generated questions + summary
      (`GET /exams/jobs/{id}/result` yahin se padhta hai). Draft-save flow mein
      ye khaali rehta hai kyunki questions `paperdraft.part_a` mein jaate hain.
    """

    # ⚠️ nullable: stateless generate (`POST /exams/generate`) mein koi draft
    # save nahi hota — job ka koi paper nahi hota. Draft flow mein pehle jaisa hi
    # paper_id set hota hai (koi behaviour change nahi).
    paper_id: UUID | None = Field(default=None, foreign_key="paperdraft.id", index=True)
    #: Who asked for this run. A job's output is the paper's questions, so the job
    #: is as private as the paper - `paper_id` alone cannot say whose it is for a
    #: stateless run (there is no paper), hence this column.
    created_by: UUID | None = Field(default=None, foreign_key="app_user.id")
    status: GenerationJobStatus = Field(default=GenerationJobStatus.queued)

    graph_state: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    stages: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    blueprint_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    coverage_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    config_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    result_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    model_info: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    error: str | None = None
    trace_id: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# ExamSource — content library row (Phase 3 RAG ke liye base)
# ------------------------------------------------------------


class ExamSource(TenantMixin, UUIDMixin, table=True):
    """Content library ka ek source (PDF/image/URL/text/bank) — Phase 3 RAG ka base.

    - `storage_key` — upload folder ka file name (bagair file wale sources jaise
      URL/text/paste-notes ke liye None). MinIO/S3 par shift hote waqt bas yeh key
      badalti hai (baaki code same).
    - `metadata_json` — JSON mein koi bhi extra info (file size, tags, ingest ke
      warnings, retrieval stats...).
      NOTE: column ka naam "metadata" nahi rakha, kyunki SQLModel ke paas already
      `.metadata` attribute hota hai (table registry) — clash ho jaata hai!
    - `version` — re-upload → naya version row (purana keep) [blueprint §2.3.1].
    - `content_hash` — source ke **content** ka sha256 (file bytes / text / url).
      Isi se duplicate indexing rukti hai: same teacher ne wahi PDF dobara save
      kiya to hum purana row (aur uske vectors) reuse karte hain, dobara embed
      nahi karte (`repository.find_source_by_hash`).
    - `replaces_id` — version chain (naya version purane ko point karta hai),
      taaki re-upload par purane source ke **stale vectors** delete ho jayein.
    - `status` / `chunk_count` / `error` — **ingestion ka per-source status**.
      Background ingest chalti hai, isliye teacher ko saaf pata chale: pending →
      ingesting → ready / failed (aur fail hone par kyun).
      `status` ko plain string rakha hai (DB enum nahi) — kyunki status list
      badalti rehti hai (partial, skipped...) aur Postgres enum ko alter karna
      migration ka dard hai; string + code-level constants zyada practical hai.

    ⚠️ `class_id` / `subject_id` ab **nullable** hain: source library
    frontend se class/subject *naam* ke saath aati hai (IDs ka mapping endpoint
    Phase 1 mein nahi bana), isliye FK khaali ho sakti hai. `class_name` /
    `subject` strings hamesha bhar jaate hain — wahi retrieval filter mein use
    hote hain.
    """

    #: The section subject this source belongs to, when that is unambiguous. The source
    #: library is class-level, so NULL is normal; the free-text `subject` below is what
    #: retrieval filters on.
    classroom_subject_id: UUID | None = Field(
        default=None, foreign_key="classroomsubject.id", index=True
    )
    created_by: UUID | None = Field(default=None, foreign_key="app_user.id")

    source_type: SourceType
    title: str
    # Content library filters (blueprint §1.2.1): class/subject/board + chapters
    class_name: str = ""
    subject: str = ""
    board: str = ""
    teacher_name: str = ""
    kind: str = "knowledge"  # "knowledge" | "pattern" (§1.2: pattern se answer nahi)
    strictness: str = "Strict"  # Strict | Flexible | Creative
    tags: list[str] = Field(default_factory=list, sa_type=JSON)
    chapters: list[str] = Field(default_factory=list, sa_type=JSON)

    storage_key: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    page_count: int | None = None

    # ---- Ingestion status (RAG) ----
    status: str = "pending"  # pending | ingesting | ready | failed
    chunk_count: int = Field(default=0)
    error: str | None = None

    # ---- Dedup + versioning (Phase 3.1 — persistent indexing) ----
    # Same content dobara save → wahi row reuse (re-embed nahi).
    content_hash: str | None = Field(default=None, index=True)
    # Re-upload / replace par purana source id (stale vectors us se delete hote hain).
    replaces_id: UUID | None = Field(default=None, foreign_key="examsource.id")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# QuestionUsageLog — anti-repeat ledger (blueprint §1.2.1 / §2.3.5)
# ------------------------------------------------------------


class QuestionUsageLog(TenantMixin, UUIDMixin, table=True):
    """ "Ye question kis paper mein kab use hua" — reuse rokne ka record.

    Kyun alag table (paperdraft ke JSON mein nahi)? Kyunki anti-repeat **cross-paper**
    sawaal hai: aaj ka Half-Yearly ko 6 mahine purane Unit Test ke questions
    pata hone chahiye. JSON ke andar dhoondhna = har paper padhna; table + index
    = ek query.

    `fingerprint` = normalised text ka hash (`rag/usage.fingerprint()`), isliye
    chhota badla hua question bhi pakda ja sakta hai (semantic check bhi hai:
    `is_duplicate()` token overlap dekhta hai).
    """

    fingerprint: str = Field(index=True)
    text: str
    paper_id: UUID | None = Field(default=None, foreign_key="paperdraft.id", index=True)
    class_name: str = Field(default="", index=True)
    #: The class the question was used for - a `classname` row. The wording above
    #: is kept so an older row still reads.
    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    subject: str = Field(default="", index=True)
    #: The section subject the question was used for, when known (old rows: NULL).
    classroom_subject_id: UUID | None = Field(
        default=None, foreign_key="classroomsubject.id", index=True
    )
    chapter: str = Field(default="")
    topic: str = ""
    qtype: str = ""
    marks: int = Field(default=0)
    created_by: UUID | None = Field(default=None, foreign_key="app_user.id")
    used_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# Marks & results — the "academics and marks" side of a classroom
#
# The shape after Phase 7 (one fact, one home):
#
#   exam          — the event ("Mid-Term 2026"). draft → scheduled → marks_entry
#                   → published; `published_at` is the moment families could see it.
#   exam_paper    — one sitting: (exam, class, subject) with the date, the room and
#                   **what it is out of**. This is the only place `max_marks` lives
#                   now; the old per-exam table said it, and Phase 7 dropped it.
#   exam_paper_chapter — what a sitting covers (`chapter` rows from Phase 5).
#   marks         — one student's score on one paper, `numeric(6,2)`.
#   marks_audit   — every change made *after* publication, with who and when.
#   grade_scale   — the school's own A/B/C boundaries.
# ------------------------------------------------------------


class ExamStatus(enum.StrEnum):
    """Where an exam has got to. Stored as these words so a query can filter."""

    draft = "draft"
    scheduled = "scheduled"
    done = "done"
    marks_entry = "marks_entry"
    published = "published"
    #: A test the teacher called off. The row stays (marks may exist, families were told),
    #: unlike a delete, which is only allowed while nothing hangs from it.
    cancelled = "cancelled"


class ExamScope(enum.StrEnum):
    """How wide the exam runs - one class, or the whole school."""

    class_level = "class"
    school = "school"


class ExamType(enum.StrEnum):
    """What kind of sitting this is. A class test is always `class_test`; a school exam
    is one of the others, and `custom` means the teacher typed the name (in `exam.name`).
    """

    class_test = "class_test"
    unit_test = "unit_test"
    periodic_test = "periodic_test"
    mid_term_test = "mid_term_test"
    half_yearly = "half_yearly"
    annual = "annual"
    pre_board = "pre_board"
    practical = "practical"
    custom = "custom"


class PassMode(enum.StrEnum):
    """How a paper's pass line is stated: a minimum number of marks, or a passing grade."""

    marks = "marks"
    grade = "grade"


#: The type words a caller may send. Older rows hold free text ("Mid-term"); the column
#: stays a plain string so they keep reading, and the new write paths validate here.
EXAM_TYPES: tuple[str, ...] = tuple(kind.value for kind in ExamType)

#: The types a School Exam may carry (everything but the class test).
SCHOOL_EXAM_TYPES: tuple[str, ...] = tuple(
    kind.value for kind in ExamType if kind is not ExamType.class_test
)

#: The pass-mode words a caller may send.
PASS_MODES: tuple[str, ...] = tuple(mode.value for mode in PassMode)

#: The status words a caller may send. A typo is refused rather than stored.
EXAM_STATUSES: tuple[str, ...] = tuple(status.value for status in ExamStatus)

#: The scope words a caller may send.
EXAM_SCOPES: tuple[str, ...] = tuple(scope.value for scope in ExamScope)


class ExamBase(SQLModel):
    """A named exam the school runs ("Mid-Term", "Unit Test 2")."""

    name: str
    #: Free text: schools word terms differently ("Term 1", "Half yearly").
    term: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    #: One of `EXAM_STATUSES`. Phase 7 replaced the free text ("Scheduled") with the
    #: lifecycle, because the reminder and the rank display both branch on it.
    status: str = Field(default=ExamStatus.draft)
    #: `class` (one class sits it) or `school` (every class does).
    scope: str = Field(default=ExamScope.class_level)
    #: The class catalog row (`classname.class_id`) this exam belongs to.
    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    #: The class-section, when the exam is one section's. NULL = class/school wide.
    classroom_id: UUID | None = Field(
        default=None, foreign_key="classroom.id", index=True
    )
    academic_year_id: UUID | None = Field(
        default=None, foreign_key="academic_year.id", index=True
    )
    #: How the school words it ("Unit test", "Mid term", "Pre-board").
    exam_type: str | None = None
    #: Who planned it - the teacher for a class test, the office for a school exam.
    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    note: str | None = None
    #: What the guardian and the student read with the schedule. Separate from `note`
    #: (the school's own remark): editing it is **not** a reschedule.
    family_note: str | None = None
    #: Set when the class teacher publishes the date sheet; NULL until then, so families
    #: see nothing and no notification went out. Separate from `published_at` (marks).
    datesheet_published_at: datetime | None = None
    datesheet_published_by_user_id: UUID | None = Field(
        default=None, foreign_key="app_user.id"
    )
    #: Set when a date sheet is archived: hidden from the list, never deleted.
    archived_at: datetime | None = None
    #: Set when the marks are published; NULL until then, so "unpublished" is a value.
    published_at: datetime | None = None


class Exam(ExamBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "exam"

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExamPaperBase(SQLModel):
    """One sitting of one **section subject**: the date-sheet row.

    A paper belongs to a classroom subject (Class 9-A's "Mathematics"); the section and
    the class are read from it, so a mark can never name a subject its paper does not.
    Sections that sit the same question paper share an `exam_paper_group`; the group
    links papers, never subjects. `max_marks` / `passing_marks` are stated here, once
    per paper - a `Mark` then carries only the score.
    """

    exam_id: UUID = Field(foreign_key="exam.id", index=True)
    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    #: The shared question paper, when one is set for several sections. NULL = this
    #: section's paper is its own.
    paper_group_id: UUID | None = Field(
        default=None, foreign_key="exam_paper_group.id", index=True
    )
    exam_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    #: `numeric(6,2)` - not money, but 12.5 out of 25 is still exact.
    max_marks: Decimal = Field(
        default=Decimal("100.00"), max_digits=6, decimal_places=2
    )
    passing_marks: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    room: str | None = None
    note: str | None = None
    #: The teacher who takes this test. NULL = the section subject's own teacher. Whether
    #: that is the assigned or a temporary teacher is **derived live** from the course,
    #: never stored, so it cannot drift when the course teacher changes.
    taken_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    #: How this paper's pass line is stated (`PassMode`). `marks`: the teacher gives a
    #: number (`passing_marks`, pre-filled with 33% of the total); `grade`: the teacher
    #: gives the lowest passing grade (`passing_grade`, "D" or a custom one). NULL on
    #: older papers, which keep their `passing_marks` as before.
    pass_mode: str | None = None
    #: The pass line **as a percentage of the total**, whichever way it was stated: the
    #: service keeps it equal to `passing_marks / max_marks * 100` (marks) or to the
    #: passing grade's lower bound (grade). It is what the "40%" beside the number shows.
    pass_percent: Decimal | None = Field(default=None, max_digits=5, decimal_places=2)
    #: The lowest grade that still passes, when `pass_mode` is `grade`. Its percentage
    #: lives in `grading_scale` (a custom grade the teacher typed is added there).
    passing_grade: str | None = None
    #: This paper's own copy of the grading ladder: `[{"min_percent": 90, "grade": "A1"}]`.
    #: A snapshot, so changing the school ladder later never rewrites an old result.
    grading_scale: list[dict[str, Any]] | None = Field(default=None, sa_type=JSON)
    #: What the subject teacher says will come in the exam, in their own words.
    syllabus_text: str | None = None
    #: How the Grade column of this paper's marks sheet works: `auto` (from the ladder),
    #: `na` (no grade) or `manual` (the teacher types each grade into `marks.grade`).
    grade_mode: str = Field(default="na", max_length=10)
    #: Who is to write this subject's syllabus. NULL = the subject's assigned teacher; a
    #: different teacher is a temporary writer (the same S / T idea as "Test Taken By").
    syllabus_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    #: Set when **this sitting's** marks were published. Per paper, because Class 9's
    #: Science teacher may be ready before the Maths one - and the principal's screen
    #: asks "which papers are still unpublished".
    published_at: datetime | None = None


class ExamPaper(ExamPaperBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(exam_id, classroom_subject_id)` - one sitting per section subject."""

    __tablename__ = "exam_paper"

    __table_args__ = (
        UniqueConstraint(
            "exam_id",
            "classroom_subject_id",
            name="uq_exampaper_exam_classroom_subject",
        ),
        # "Same section subject on the same date" - the duplicate-test warning's lookup.
        Index("ix_exam_paper_subject_date", "classroom_subject_id", "exam_date"),
    )


class ExamPaperGroup(TenantMixin, UUIDMixin, table=True):
    """One shared question paper sat by several sections of an exam.

    The group links **papers**, not subjects: 9-A's "English" and 9-B's "English
    Literature" may share a paper without either subject changing its name. Its chapters
    are names (`ExamPaperGroupChapter`) because chapter ids belong to one section each.
    """

    __tablename__ = "exam_paper_group"

    exam_id: UUID = Field(foreign_key="exam.id", index=True)
    #: Shown on the datesheet and the question paper; NULL = each row shows its own
    #: subject name.
    display_title: str | None = None
    #: A convenience stamp. The truth is "any paper has marks or is published", read
    #: live - see `plan.groups.is_locked`.
    locked_at: datetime | None = None
    locked_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExamPaperGroupChapter(TenantMixin, UUIDMixin, table=True):
    """A chapter of a shared paper, by name, in order. `UNIQUE(group, sequence)`."""

    __tablename__ = "exam_paper_group_chapter"

    __table_args__ = (
        UniqueConstraint(
            "paper_group_id", "sequence", name="uq_exampapergroupchapter_group_seq"
        ),
    )

    paper_group_id: UUID = Field(foreign_key="exam_paper_group.id", index=True)
    sequence: int
    name: str


class ExamPaperChapter(TenantMixin, UUIDMixin, table=True):
    """A chapter (Phase 5's `chapter`) that this sitting covers. `UNIQUE` pair.

    The syllabus of a unit test is a set of chapters, so it is rows here - not a text
    field that drifts from the plan the Course tab shows.
    """

    __tablename__ = "exam_paper_chapter"

    __table_args__ = (
        UniqueConstraint(
            "exam_paper_id", "chapter_id", name="uq_exampaperchapter_paper_chapter"
        ),
    )

    exam_paper_id: UUID = Field(foreign_key="exam_paper.id", index=True)
    chapter_id: UUID = Field(foreign_key="chapter.id", index=True)


class MarkBase(SQLModel):
    """One subject's mark for one student on one paper.

    Neither the class-section nor `max_marks` is copied here: the placement comes from
    the student, and the maximum from the paper. `exam_id` / `subject_id` are kept (the
    older Academics read still filters on them) and the **service writes them from the
    chosen paper**, so a mark cannot name a subject its paper does not - there is a
    test for exactly that.
    """

    student_id: UUID = Field(foreign_key="student.id", index=True)
    #: The sitting - the one fact a mark hangs from. The exam and the subject are read
    #: from the paper, so a mark can never name a subject its paper does not.
    exam_paper_id: UUID = Field(foreign_key="exam_paper.id", index=True)
    #: `numeric(6,2)`; NULL when the student was absent (`is_absent` is the fact).
    marks_obtained: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    #: Absent is not zero: a zero is a score, an absence has no score.
    is_absent: bool = Field(default=False)
    #: The teacher's own grade - written only when the paper's `grade_mode` is `manual`;
    #: otherwise the grade is derived from `grade_scale` at read time.
    grade: str | None = None
    #: The teacher/admin who entered the mark (NULL for imported rows).
    entered_by: UUID | None = Field(default=None, foreign_key="app_user.id")
    #: The student's placement that session (`enrollment`), so a mark belongs to one
    #: year and one enrollment record and promotion/de-promotion can follow it.
    enrollment_id: UUID | None = Field(
        default=None, foreign_key="enrollment.id", index=True
    )


class Mark(MarkBase, TenantMixin, UUIDMixin, table=True):
    """Two unique keys, both true statements:

    * `(exam_paper_id, student_id)` - one score per paper per student (Phase 7);
    * `(exam_id, student_id, subject_id)` - kept from before, so a row written by an
      older path cannot duplicate either. The single writer fills both sets of columns
      from the same paper, so the two keys can never disagree.
    """

    __tablename__ = "marks"

    __table_args__ = (
        UniqueConstraint("exam_paper_id", "student_id", name="uq_marks_paper_student"),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarksAudit(TenantMixin, UUIDMixin, table=True):
    """One change made to a mark after its exam was published.

    Nothing is overwritten silently once a family has seen the result: the old value,
    the new value, who changed it and when stay here, and the service refuses the edit
    if it cannot write the row.
    """

    __tablename__ = "marks_audit"

    marks_id: UUID = Field(foreign_key="marks.id", index=True)
    old_value: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    new_value: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    #: Whether the change was "absent" being set or cleared.
    old_absent: bool = Field(default=False)
    new_absent: bool = Field(default=False)
    changed_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str | None = None


class GradeScaleBase(SQLModel):
    """One boundary of the school's ladder: `>= min_percent` earns `grade`.

    Rows, not code: a school that calls 90 "A+" and another that calls it "A1" both say
    so here, and the result screen reads the ladder instead of a range table hardcoded
    in Python.
    """

    min_percent: Decimal = Field(max_digits=5, decimal_places=2)
    grade: str
    #: Ordering hint for a screen that lists the ladder (90, 80, 70 ...).
    label: str | None = None


class GradeScale(GradeScaleBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, min_percent)` - one grade per boundary for this school."""

    __tablename__ = "grade_scale"

    __table_args__ = (
        UniqueConstraint("min_percent", name="uq_gradescale_school_min_percent"),
    )
