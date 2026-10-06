# ============================================================
# Exam/Paper schemas (blueprint §2.9) — Pydantic request/response
# contracts. All input is validated server-side, so the frontend is
# never trusted and the Marks Contract is enforced here.
# ============================================================

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import CoverageMode, GenerationJobStatus, PaperStatus

# ------------------------------------------------------------
# Blueprint section — mirrors the frontend BlueprintSection shape
#   { type, count, marksEach, hasImage? }
# ------------------------------------------------------------


class BlueprintSectionIn(BaseModel):
    type: str = Field(min_length=1)  # "MCQ", "Short", "Long", ...
    count: int = Field(ge=0)  # number of questions of this type
    marksEach: int = Field(ge=1)  # marks per question
    hasImage: bool | None = None  # optional (diagram-based types)


def blueprint_total(blueprint: list[BlueprintSectionIn]) -> int:
    """Marks Contract total = sum of (count x marksEach)."""
    return sum(s.count * s.marksEach for s in blueprint)


# ------------------------------------------------------------
# Coverage plan — mirrors the frontend CoveragePlan shape
#   { mode, chapters: [{chapter, targetMarks, auto, topics:[...]}], totalAllocated }
# ------------------------------------------------------------


class CoverageTopicIn(BaseModel):
    topic: str = ""
    targetMarks: int = Field(default=0, ge=0)


class CoverageChapterIn(BaseModel):
    chapter: str = Field(min_length=1)
    targetMarks: int = Field(default=0, ge=0)  # marks or percent, per mode
    auto: bool = True  # True = target is 0, so questions are distributed randomly
    topics: list[CoverageTopicIn] = []


class CoveragePlanIn(BaseModel):
    mode: CoverageMode = CoverageMode.auto
    chapters: list[CoverageChapterIn] = []
    totalAllocated: int = Field(default=0, ge=0)  # sum computed by the frontend


# ------------------------------------------------------------
# Question — mirrors the frontend QuestionDraft shape
# ------------------------------------------------------------


class QuestionIn(BaseModel):
    id: str | None = None
    type: str = Field(min_length=1)
    text: str
    options: list[str] | None = None
    answer: str | None = None
    difficulty: str = "Medium"
    bloom: str = "Understand"
    marks: int = Field(ge=1)
    topic: str | None = None
    chapter: str = ""
    image: dict[str, Any] | None = None  # ImageRef shape (frontend)
    sourceRefs: list[str] = []
    locked: bool = False
    origin: str = "teacher"  # "ai" | "teacher"
    recommendedMarks: int | None = Field(default=None, ge=1)
    markingScheme: str | None = None


# ------------------------------------------------------------
# Sources — mirrors the frontend SourceItem shape.
# Two shapes are supported: the typed `SourceIn` subset and a raw dict
# carrying every frontend field. `extra="allow"` keeps unknown keys,
# because `llm.services.build_sources()` reads them directly.
# ------------------------------------------------------------


class SourceIn(BaseModel):
    id: str = ""
    sourceType: str = "text"  # "A"|"B"|"C"|"D"|"E"|"F"|"G"
    label: str
    # Optional detail — for Type-D (pasted notes) and retrieval metadata
    textExcerpt: str | None = None
    chapters: list[str] = []
    pages: str | None = None
    url: str | None = None
    fileName: str | None = None

    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------
# PaperConfigBase — the one config shape shared by draft-save and
# stateless generate, so both endpoints get identical validation.
# ------------------------------------------------------------


class PaperConfigBase(BaseModel):
    """The teacher's full paper config, validated server-side."""

    title: str = Field(min_length=1, max_length=200)
    classroom_id: int | None = None  # optional: the frontend sends no IDs yet
    subject_id: int | None = None
    total_marks: int = Field(ge=1, le=500)  # Marks Contract target
    duration_minutes: int = Field(default=60, ge=1, le=600)

    # ---- (A) AI prompt context (frontend "Basic Details" step) ----
    class_name: str = ""
    subject: str = ""
    board: str = "CBSE"
    exam_type: str = "Unit Test"
    language: str = "English"
    chapters: list[str] = []

    # ---- (B) Plan ----
    blueprint: list[BlueprintSectionIn] = []
    coverage_mode: CoverageMode = CoverageMode.auto
    coverage_plan: CoveragePlanIn = CoveragePlanIn()
    part_b: list[QuestionIn] = []  # teacher's custom questions

    # ---- (C) Teacher context (frontend "Source" and Blueprint steps) ----
    # `list[dict]` passthrough: the frontend SourceItem shape is kept as-is,
    # because `llm.services.build_sources()` reads those exact keys.
    sources: list[dict[str, Any]] = []
    instructions: list[str] = []
    scope: dict[str, Any] = {}
    constraints: dict[str, Any] = {}

    @model_validator(mode="after")
    def check_marks_contract(self) -> Self:
        """RULE #1 (blueprint §2.3.3): blueprint total == total_marks.

        Enforced server-side, so an empty or mismatched blueprint is rejected
        no matter what the frontend sends.
        """
        total = blueprint_total(self.blueprint)
        if self.blueprint and total != self.total_marks:
            raise ValueError(
                f"Marks Contract fail: blueprint total {total} != total_marks {self.total_marks}"
            )
        return self

    @model_validator(mode="after")
    def check_coverage_within_cap(self) -> Self:
        """RULE #2: the coverage sum may not exceed the target.

        marks mode   -> cap = total_marks (remainder goes to chapter Random)
        percent mode -> cap = 100        (remainder goes to chapter Random)
        Equal or less is fine; Random handles the remainder.
        """
        allocated = sum(c.targetMarks for c in self.coverage_plan.chapters)
        cap = self.total_marks if self.coverage_mode == CoverageMode.marks else 100
        if allocated > cap:
            raise ValueError(
                f"Coverage sum {allocated} exceeds cap {cap} "
                f"(mode={self.coverage_mode.value})"
            )
        return self


class PaperDraftCreate(PaperConfigBase):
    """Body for POST /exams/papers (and PATCH /exams/papers/{id}) — draft save.

    The draft is persisted, so it also passes the Marks Contract gates.
    """


class GenerationConfigRequest(PaperConfigBase):
    """Body for POST /exams/generate — **stateless** generate (nothing saved).

    The full config is frozen into the job's `config_snapshot`, and the
    generated questions come from `result_snapshot`
    (`GET /exams/jobs/{job_id}/result`). Only when the teacher explicitly saves
    does `POST /exams/papers` (upsert) create the paper with the same payload.
    """

    # optional: link to an existing draft (traceability / audit)
    link_paper_id: int | None = Field(default=None, ge=1)


# ------------------------------------------------------------
# GenerationRequest — body for POST /exams/papers/generate
# ------------------------------------------------------------


class GenerationRequest(BaseModel):
    """Generate from a saved draft — the plan is read from the paper record.

    Only `paper_id` is required; every other field is an optional override that
    is written into the job snapshot.
    """

    paper_id: int = Field(ge=1)  # paper to generate for
    force: bool = False  # True = ignore an in-flight duplicate job and start fresh
    total_marks: int | None = Field(default=None, ge=1, le=500)
    blueprint: list[BlueprintSectionIn] | None = None
    coverage_plan: CoveragePlanIn | None = None
    sources: list[SourceIn] | None = None
    instructions: list[str] | None = None

    @model_validator(mode="after")
    def check_marks_contract(self) -> Self:
        """Validate the Marks Contract against any supplied overrides.

        When `total_marks` is omitted the service falls back to the paper record
        and applies the same check there, so validation is never skipped.
        """
        if self.blueprint and self.total_marks is not None:
            total = blueprint_total(self.blueprint)
            if total != self.total_marks:
                raise ValueError(
                    f"Marks Contract fail: blueprint total {total} != total_marks {self.total_marks}"
                )
        return self


# ------------------------------------------------------------
# Responses — PAPER
# ------------------------------------------------------------


class PaperDraftRead(BaseModel):
    id: int
    title: str
    classroom_id: int | None = None
    subject_id: int | None = None
    # context — the frontend Draft/Paper tabs filter on these
    class_name: str = ""
    subject: str = ""
    exam_type: str = ""
    total_marks: int
    duration_minutes: int
    blueprint: Any  # flexible for the JSON column
    coverage_mode: CoverageMode | str
    coverage_plan: Any
    part_a: Any
    part_b: Any
    status: PaperStatus | str
    created_at: datetime
    updated_at: datetime


class PaperSavedRead(BaseModel):
    paperId: int
    status: PaperStatus | str = PaperStatus.draft


# ------------------------------------------------------------
# Responses — JOB (polling)
# ------------------------------------------------------------


class JobRead(BaseModel):
    """Response for `GET /papers/{id}/job` and `GET /jobs/{id}` (polling contract).

    `paper_id` is nullable because a stateless generate (`POST /exams/generate`)
    saves no draft, so the job belongs to no paper.
    """

    id: int
    paper_id: int | None = None
    status: GenerationJobStatus | str
    stages: dict[str, Any] = {}
    result: dict[str, Any] = {}
    error: str | None = None
    trace_id: str | None = None
    model_info: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class JobResultRead(BaseModel):
    """`GET /exams/jobs/{job_id}/result` — generated questions (stateless flow).

    Nothing is written to a paper record; the questions live in the job's
    `result_snapshot` until the teacher saves them via `POST /exams/papers`.
    """

    job_id: int
    paper_id: int | None = None
    status: GenerationJobStatus | str
    questions: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    quality: dict[str, Any] = {}
    coverage: list[dict[str, Any]] = []
    error: str | None = None


class GenerateResponse(BaseModel):
    questions: list[QuestionIn]
    paper_id: int | None = None


# ------------------------------------------------------------
# PATCH /papers/{id}/questions/{qid} — partial update
# ------------------------------------------------------------


class QuestionPatch(BaseModel):
    mark: int | None = Field(default=None, ge=1)  # rebalance (change marks)
    text: str | None = None
    answer: str | None = None
    topic: str | None = None
    chapter: str | None = None
    locked: bool | None = None
    regenerate: bool | None = None  # ask the AI to generate a new version


# ------------------------------------------------------------
# POST /papers/{id}/questions/regenerate — scoped bulk regeneration
# ------------------------------------------------------------


class QuestionRegenerateRequest(BaseModel):
    """Regenerate **only** these questions — the rest of the paper never moves.

    The server keeps just the ids that exist in `part_a` **and are unlocked**;
    everything else is reported back in `skipped_locked` / `skipped_unknown`.
    Because each job reuses the old question's slot (type/marks/chapter), the
    Marks Contract cannot change.
    """

    question_ids: list[str] = Field(min_length=1)


class QuestionRegenerateResult(BaseModel):
    """What was actually queued, plus what was refused and why."""

    job_id: int
    queued: list[str] = []
    skipped_locked: list[str] = []
    skipped_unknown: list[str] = []


# ------------------------------------------------------------
# POST /papers/{id}/questions/{qid}/takeover — teacher replaces an AI question
# ------------------------------------------------------------


class QuestionTakeoverRequest(BaseModel):
    """The teacher's own version of an AI question ("Write my own").

    The question moves from `part_a` to `part_b` and its `origin` becomes
    "teacher", so from here on it is rendered and counted as a Custom question.
    """

    text: str = Field(min_length=1)
    answer: str | None = None
    mark: int | None = Field(default=None, ge=1)
    topic: str | None = None
    chapter: str | None = None


# ------------------------------------------------------------
# POST /exams/questions/custom — body
# ------------------------------------------------------------


class CustomQuestionCreate(BaseModel):
    paper_id: int = Field(ge=1)
    question: QuestionIn


# ------------------------------------------------------------
# POST /papers/{id}/finalize
# ------------------------------------------------------------


class FinalizeRequest(BaseModel):
    """Nothing but a "human approved this" signal — the service layer re-checks
    the Marks Contract, coverage and answers from the DB.
    """

    note: str | None = None


# ------------------------------------------------------------
# POST /questions/recommend-marks — suggested marks for a custom question
# ------------------------------------------------------------


class MarksSuggestionRequest(BaseModel):
    """Sent by the frontend "Add my question" form.

    `use_llm=False` (default) -> rules only (instant, free, deterministic).
    `use_llm=True`           -> a second opinion from the judge model (~60s).
    """

    type: str = ""
    difficulty: str = "Medium"
    text: str = ""
    use_llm: bool = False


class MarksSuggestionRead(BaseModel):
    """Output of `llm.services.suggest_marks()` — the marks plus the reasoning.

    `reasons` are shown in the UI: a bare number is not trusted, but
    "base for Short = 2 + Hard difficulty +1" is.
    """

    marks: int
    base: int | None = None
    source: str = "rules"  # "rules" | "rules+llm"
    reasons: list[str] = []
    llm_marks: int | None = None
    llm_error: str | None = None


# ------------------------------------------------------------
# CONTENT LIBRARY — sources (blueprint §1.2.1 / §2.9)
# ------------------------------------------------------------
# The frontend `SourceStep` `SourceItem` is accepted as-is plus the paper
# context (class/subject/board/chapters), so entries stay filterable.
# `extra="allow"` keeps any new frontend field instead of dropping it.
# ------------------------------------------------------------


class SourceCreate(BaseModel):
    """Body for `POST /exams/sources` (and upload metadata)."""

    title: str = Field(min_length=1, max_length=200)
    sourceType: str = "D"  # frontend code "A".."G"; the service derives the kind
    label: str = ""
    kind: str = "knowledge"  # "knowledge" | "pattern"
    strictness: str = "Strict"  # Strict | Flexible | Creative
    chapters: list[str] = []
    tags: list[str] = []
    teacherName: str = ""
    url: str | None = None
    textExcerpt: str | None = None
    fileName: str | None = None
    pages: str | None = None
    libraryEntryId: str | None = None
    bankRef: str | None = None

    # ---- paper context (library filters) ----
    class_name: str = ""
    subject: str = ""
    board: str = ""
    classroom_id: int | None = None
    subject_id: int | None = None
    version: int = Field(default=1, ge=1)

    # ---- dedup / versioning (Phase 3.1) ----
    # `contentHash` — the client may send a precomputed hash (the upload flow
    # sends the file's sha256). Leave empty and the server computes it for
    # text/URL/notes sources.
    contentHash: str | None = None
    # `replacesId` — the older source this one replaces; its stale vectors are
    # deleted on re-upload.
    replacesId: int | None = None

    model_config = ConfigDict(extra="allow")


class SourceRead(BaseModel):
    """One Content Library row (a superset of the frontend `SourceLibraryItem`).

    `status`/`chunk_count`/`error` reflect ingestion state:
        pending -> ingesting -> ready (chunks>0) | failed (reason in `error`)
    """

    id: int
    title: str
    sourceType: str  # "A".."G" (the same code the frontend sent)
    kind: str = "knowledge"
    class_name: str = ""
    subject: str = ""
    board: str = ""
    chapters: list[str] = []
    tags: list[str] = []
    teacher_name: str = ""
    version: int = 1
    status: str = "pending"
    chunk_count: int = 0
    page_count: int | None = None
    error: str | None = None
    url: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    # ---- dedup / versioning (Phase 3.1) ----
    content_hash: str | None = None
    replaces_id: int | None = None
    # True = an existing source already had this content, so the frontend should
    # reuse `id` instead of creating a new entry.
    deduplicated: bool = False


class SourceUploadRead(BaseModel):
    """Upload response — the file is stored and ingestion runs in the background."""

    sourceId: int
    storageKey: str
    status: str = "pending"
    message: str = ""
    # True = the same file was already indexed, so no new ingest was started
    deduplicated: bool = False


class IngestResultRead(BaseModel):
    """Ingest result — diagnostics plus a clear reason for the teacher."""

    sourceId: int
    status: str
    chunks: int = 0
    pages: int = 0
    collection: str | None = None
    warnings: list[str] = []
    error: str | None = None
