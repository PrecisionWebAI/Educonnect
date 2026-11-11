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
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import UniqueConstraint
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
    #: The class the paper is for - a `classname` row. Nullable because the
    #: builder may only know the wording (`class_name` below).
    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id", index=True)
    #: The section the paper is for ("A") - a `section` row. Class + section
    #: together are the class-section it will be sat in.
    section_id: UUID | None = Field(
        default=None, foreign_key="section.section_id", index=True
    )
    created_by: UUID | None = Field(default=None, foreign_key="user.id")

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
    created_by: UUID | None = Field(default=None, foreign_key="user.id")
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


    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id", index=True)
    created_by: UUID | None = Field(default=None, foreign_key="user.id")

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
    chapter: str = Field(default="")
    topic: str = ""
    qtype: str = ""
    marks: int = Field(default=0)
    created_by: UUID | None = Field(default=None, foreign_key="user.id")
    used_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# Marks & results — the "academics and marks" side of a classroom
# ------------------------------------------------------------


class ExamBase(SQLModel):
    """A named exam the school runs ("Mid-Term", "Unit Test 2")."""

    name: str
    #: Free text: schools word terms differently ("Term 1", "Half yearly").
    term: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    #: "Scheduled" / "Ongoing" / "Completed" - the label the screen shows.
    status: str = Field(default="Scheduled")


class Exam(ExamBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "exam"

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExamSubjectBase(SQLModel):
    """One subject an exam covers, and the marks it is out of.

    The exam declares its subjects once, here, so a `Mark` can hold just the score.
    Repeating `max_marks` on every student's row meant dozens of copies of the same
    number, and any one of them could disagree with the others.
    """

    exam_id: UUID = Field(foreign_key="exam.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id")
    max_marks: float = Field(default=100.0)


class ExamSubject(ExamSubjectBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(exam_id, subject_id)` - one row per subject per exam."""

    __table_args__ = (
        UniqueConstraint("exam_id", "subject_id", name="uq_examsubject_exam_subject"),
    )


class MarkBase(SQLModel):
    """One subject's mark for one student in one exam.

    Neither the class-section nor `max_marks` is copied here: the placement comes
    from the student, and the maximum comes from `ExamSubject`. A mark therefore
    cannot be filed under a class the student was never in, nor scored out of
    something the exam does not say.
    """

    exam_id: UUID = Field(foreign_key="exam.id", index=True)
    student_id: UUID = Field(foreign_key="student.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id")
    marks_obtained: float
    grade: str | None = None
    #: The teacher/admin who entered the mark (NULL for imported rows).
    entered_by: UUID | None = Field(default=None, foreign_key="user.id")


class Mark(MarkBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(exam_id, student_id, subject_id)` - one mark per subject per exam."""

    __tablename__ = "marks"

    __table_args__ = (
        UniqueConstraint(
            "exam_id",
            "student_id",
            "subject_id",
            name="uq_marks_exam_student_subject",
        ),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
