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
from datetime import datetime
from typing import Any

from sqlmodel import JSON, Field, SQLModel


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

class PaperDraft(SQLModel, table=True):
    """Ek AI paper ka draft. Har field blueprint §2.3.2 se aayi hai.

    JSON columns (`sa_type=JSON`):
      blueprint  — section config: [{type, count, marks_each}, ...]
      coverage_plan — {chapters: [{chapter, target_marks}], mode}
      part_a     — AI generate kiye questions ({sections: [...]})
      part_b     — teacher ke custom questions
    """

    id: int | None = Field(default=None, primary_key=True)

    title: str
    # Phase 1: frontend abhi class/subject IDs nahi bhejta (sirf names) —
    # isliye nullable rakha. Jab mapping API banegi (Phase 1 router/service),
    # yahan real IDs aayengi.
    grade_class_id: int | None = Field(default=None, foreign_key="gradeclass.id", index=True)
    subject_id: int | None = Field(default=None, foreign_key="subject.id", index=True)
    created_by: int | None = Field(default=None, foreign_key="user.id")

    total_marks: int = Field(default=0)      # Marks Contract ka source of truth
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

class GenerationJob(SQLModel, table=True):
    """Ek generation run ka record.

    - `status` = single source of truth for progress polling.
    - `graph_state` = LangGraph checkpoint (resume-after-crash, Phase 3).
    - `blueprint_snapshot` / `coverage_snapshot` = job shuru hone par
      kya config tha (baad mein change bhi ho to job wahi generate kare).
    - `trace_id` = har job ka unique log id (debugging + logs).
    """

    id: int | None = Field(default=None, primary_key=True)

    paper_id: int = Field(foreign_key="paperdraft.id", index=True)
    status: GenerationJobStatus = Field(default=GenerationJobStatus.queued)

    graph_state: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    stages: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    blueprint_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    coverage_snapshot: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    model_info: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    error: str | None = None
    trace_id: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------
# ExamSource — content library row (Phase 3 RAG ke liye base)
# ------------------------------------------------------------

class ExamSource(SQLModel, table=True):
    """Content library ka ek source (PDF/image/URL/text/bank).

    - `storage_key` — MinIO/S3 file ka path (bagair file wale sources
      jaise URL/text ke liye None).
    - `metadata_json` — JSON mehar koi bhi extra info (file size, tags...).
      NOTE: name "metadata" nahi rakha, kyunki SQLModel ke paas already
      `.metadata` attribute hota hai (table registry) — clash hoga!
    - `version` — re-upload → naya version row (old keep) [blueprint §2.3.1].
    """

    id: int | None = Field(default=None, primary_key=True)

    grade_class_id: int = Field(foreign_key="gradeclass.id", index=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    created_by: int | None = Field(default=None, foreign_key="user.id")

    source_type: SourceType
    title: str
    chapters: list[str] = Field(default_factory=list, sa_type=JSON)

    storage_key: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    page_count: int | None = None

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)