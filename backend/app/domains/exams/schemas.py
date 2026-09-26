# ============================================================
# Exam/Paper schemas (blueprint §2.9) — Pydantic ke request/response
# contracts. Yahi jagah hai jahan "frontend kabhi trust nahi karte"
# ka rule asal mein dikhta hai — server-side validation.
#
# Kaunse schemas:
#   PaperDraftCreate   — POST /exams/papers (Marks Contract check yahin)
#   GenerationRequest  — POST /exams/papers/generate
#   QuestionIn/Read    — question shape (AI + teacher dono)
#   SourceIn           — sources jo generation mein bhejta hai frontend
#   PaperDraftRead     — draft ka response contract
#   JobRead            — generation job ka poll response
#   QuestionPatch      — PATCH /questions/{qid}
#   GenerateResponse   — generate ka response
# ============================================================

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import CoverageMode, GenerationJobStatus, PaperStatus

# ------------------------------------------------------------
# Blueprint section — frontend BlueprintSection.js se 1:1
#   { type, count, marksEach, hasImage? }
# ------------------------------------------------------------


class BlueprintSectionIn(BaseModel):
    type: str = Field(min_length=1)  # "MCQ", "Short", "Long", ...
    count: int = Field(ge=0)  # kitne questions is type ke
    marksEach: int = Field(ge=1)  # har question ke marks
    hasImage: bool | None = None  # optional (diagram types)


def blueprint_total(blueprint: list[BlueprintSectionIn]) -> int:
    """Marks Contract ka "expected" total = sum of (count x marksEach)."""
    return sum(s.count * s.marksEach for s in blueprint)


# ------------------------------------------------------------
# Coverage plan — frontend CoveragePlan.js se 1:1
#   { mode, chapters: [{chapter, targetMarks, auto, topics:[...]}], totalAllocated }
# ------------------------------------------------------------


class CoverageTopicIn(BaseModel):
    topic: str = ""
    targetMarks: int = Field(default=0, ge=0)


class CoverageChapterIn(BaseModel):
    chapter: str = Field(min_length=1)
    targetMarks: int = Field(default=0, ge=0)  # marks (marks mode) ya % (percent mode)
    auto: bool = True  # true = target 0 hai, Random se bheghega
    topics: list[CoverageTopicIn] = []


class CoveragePlanIn(BaseModel):
    mode: CoverageMode = CoverageMode.auto
    chapters: list[CoverageChapterIn] = []
    totalAllocated: int = Field(default=0, ge=0)  # frontend ka computed sum


# ------------------------------------------------------------
# Question — frontend QuestionDraft.js se 1:1
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
# Sources — frontend SourceItem.js se 1:1
# ------------------------------------------------------------
# ⚠️ Do shapes ko support karna zaroori hai:
#   · `SourceIn` — typed subset (purane callers / chhote clients ke liye)
#   · `dict`     — paper ka poora SourceItem (frontend ka exact shape:
#                  sourceType "A".."G", kind, strictness, chapters, fileName,
#                  url, textExcerpt, bankRef, libraryEntryId ...)
#
# Paper ke `sources` column mein hum **as-is dict** rakhte hain, kyunki
# `llm.services.build_sources()` unhi keys ko padhta hai (textExcerpt/label/pages).
# Isliye `SourceIn` mein `extra="allow"`: koi bhi naya frontend field chup-chaap
# drop na ho (yehi bug PaperDraftCreate ke saath hua tha — 10 context fields gayab).


class SourceIn(BaseModel):
    id: str = ""
    sourceType: str = "text"  # "A"|"B"|"C"|"D"|"E"|"F"|"G"
    label: str
    # Optional detail — Type-D (paste notes) aur retrieval metadata ke liye
    textExcerpt: str | None = None
    chapters: list[str] = []
    pages: str | None = None
    url: str | None = None
    fileName: str | None = None

    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------
# PaperConfigBase — DRAFT SAVE aur STATELESS GENERATE ka **ek hi** config
# ------------------------------------------------------------
# ⭐ Kyun base class? Dono jagah bilkul same config aata hai (Basics → Source →
# Blueprint → Coverage). Pehle sirf `PaperDraftCreate` tha, aur woh AI context
# fields (class_name, chapters, sources, scope...) **kaat deta tha** — Pydantic
# ka default `extra="ignore"` hai, isliye frontend jo bhejta tha woh chup-chaap
# gayab ho jata tha. Nateeja: DB mein class/subject/chapters khaali, aur LLM ko
# pata hi nahi hota tha ki Class 8 Science ka paper banana hai (generic questions).
#
# Ab fields + validators ek hi jagah, aur dono endpoints ko same server-side
# validation milti hai (Marks Contract + coverage cap).


class PaperConfigBase(BaseModel):
    """Teacher ka poora paper config — server-side validated."""

    title: str = Field(min_length=1, max_length=200)
    grade_class_id: int | None = None  # Phase 1: optional (frontend IDs nahi bhejta)
    subject_id: int | None = None
    total_marks: int = Field(ge=1, le=500)  # Marks Contract ka target
    duration_minutes: int = Field(default=60, ge=1, le=600)

    # ---- (A) AI prompt ka fuel (frontend ka "Basic Details" step) ----
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
    part_b: list[QuestionIn] = []  # teacher ke custom questions

    # ---- (C) Teacher ka context (frontend "Source" aur Blueprint step) ----
    # `list[dict]` passthrough: frontend SourceItem ka exact shape (sourceType
    # "A".."G", kind, strictness, chapters, fileName, url, textExcerpt, bankRef,
    # libraryEntryId...) humein **as-is** chahiye — LLM layer ka `build_sources()`
    # inhi keys se prompt ka source block banata hai.
    sources: list[dict[str, Any]] = []
    instructions: list[str] = []
    scope: dict[str, Any] = {}
    constraints: dict[str, Any] = {}

    @model_validator(mode="after")
    def check_marks_contract(self) -> Self:
        """RULE #1 (blueprint §2.3.3): blueprint ka total == total_marks.

        Agar blueprint khaali hai → total 0 != total_marks → auto-reject.
        Ye rule SERVER side hai — frontend kuch bhi bheje, yahan pakda jayega.
        """
        total = blueprint_total(self.blueprint)
        if self.blueprint and total != self.total_marks:
            raise ValueError(
                f"Marks Contract fail: blueprint total {total} != total_marks {self.total_marks}"
            )
        return self

    @model_validator(mode="after")
    def check_coverage_within_cap(self) -> Self:
        """RULE #2: coverage ka sum target se zyada nahi ho sakta.

        marks mode  → cap = total_marks (remainder → chapter-level Random)
        percent mode → cap = 100      (remainder → chapter-level Random)
        Equal ya less = OK (Random handles bacha hua part).
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
    """POST /exams/papers (aur PATCH /exams/papers/{id}) ka body — draft save.

    Draft DB mein jaata hai, isliye iske upar Marks Contract gates bhi lagte hain
    (validators base class mein hain — dono endpoints ko same milte hain).
    """


class GenerationConfigRequest(PaperConfigBase):
    """POST /exams/generate ka body — **stateless** generate (draft DB mein nahi).

    Design (decided): teacher Generate dabaye to blueprint/paper DB mein save
    **nahi** hota. Poora config job ke `config_snapshot` mein freeze hota hai aur
    generated questions `result_snapshot` se milte hain
    (`GET /exams/jobs/{job_id}/result`). Jab teacher kahe "ye save karo", tab
    `POST /exams/papers` (upsert) se paper banega — bilkul yehi payload.
    """

    # optional: kisi existing draft se jodna ho (traceability / audit)
    link_paper_id: int | None = Field(default=None, ge=1)


# ------------------------------------------------------------
# GenerationRequest — POST /exams/papers/generate ka body
# ------------------------------------------------------------


class GenerationRequest(BaseModel):
    """Saved draft se generate — plan **server paper record se** padhta hai.

    Phase 2 rule (aur frontend ka behaviour): body mein sirf `paper_id` bhejna
    kaafi hai. Baaki fields **optional overrides** hain — jo bheja, wahi job ke
    snapshot mein jayega.

    ⚠️ PEHLE BUG THA: `total_marks` required tha (frontend `{paper_id, force}`
    bhejta hai) → 422; aur `force` field hi nahi thi → `request.force` par
    AttributeError (500). Isliye generate kabhi shuru hi nahi hota tha.
    """

    paper_id: int = Field(ge=1)  # generate kis paper ke liye
    force: bool = False  # true = chal raha duplicate job ignore karke naya banao
    total_marks: int | None = Field(default=None, ge=1, le=500)
    blueprint: list[BlueprintSectionIn] | None = None
    coverage_plan: CoveragePlanIn | None = None
    sources: list[SourceIn] | None = None
    instructions: list[str] | None = None

    @model_validator(mode="after")
    def check_marks_contract(self) -> Self:
        """Override bheja ho to usi par Marks Contract check karo.

        (`total_marks` na bheja ho to service paper record ka value use karti hai
        aur wahan bhi yahi check lagta hai — validation kabhi skip nahi hoti.)
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
    grade_class_id: int | None = None
    subject_id: int | None = None
    # context — frontend Draft/Paper tabs inhe filter ke liye use karte hain
    class_name: str = ""
    subject: str = ""
    exam_type: str = ""
    total_marks: int
    duration_minutes: int
    blueprint: Any  # JSON column ke liye flexible
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
    """`GET /papers/{id}/job` aur `GET /jobs/{id}` ka response (polling contract).

    ⚠️ PEHLE BUG THA: `service.job_read()` `result=...` pass karta tha, par ye
    field yahan define hi nahi thi — Pydantic default `extra="ignore"` ki wajah se
    `result` chup-chaap **gayab** ho jata tha (frontend ko `job.result` hamesha
    null milta tha). Ab explicitly field hai.

    `paper_id` ab **nullable** hai: stateless generate (`POST /exams/generate`)
    mein koi draft save nahi hota, isliye job kisi paper se juda hota hi nahi.
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

    Stateless generate mein questions kisi paper record mein nahi likhe jaate —
    job ke `result_snapshot` mein hote hain. Frontend yahi se uthata hai, aur
    jab teacher "save karo" bole tab `POST /exams/papers` (upsert) chalta hai.
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
    mark: int | None = Field(default=None, ge=1)  # rebalance (marks badlo)
    text: str | None = None
    answer: str | None = None
    topic: str | None = None
    chapter: str | None = None
    locked: bool | None = None
    regenerate: bool | None = None  # AI se naya generate karo


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
    """Aur kuch nahi — finalize sirf ek "human ne approve kiya" signal hai.
    Marks Contract / coverage / answers sab service layer khud DB se check karta hai.
    """

    note: str | None = None


# ------------------------------------------------------------
# POST /questions/recommend-marks — custom question ke liye suggested marks
# ------------------------------------------------------------


class MarksSuggestionRequest(BaseModel):
    """Frontend "Add my question" form se aata hai.

    `use_llm=False` (default) → sirf rules (instant, free, deterministic).
    `use_llm=True`           → judge model se second opinion (slow ~60s).
    """

    type: str = ""
    difficulty: str = "Medium"
    text: str = ""
    use_llm: bool = False


class MarksSuggestionRead(BaseModel):
    """`llm.services.suggest_marks()` ka output — marks + **kyun**.

    `reasons` UI mein dikhte hain: teacher ko "server ne 2 bola" se bharosa nahi
    hota, "base for Short = 2 + Hard difficulty +1" se hota hai.
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
# Frontend `SourceStep` ka `SourceItem` yahan **as-is** aata hai, plus paper ka
# context (class/subject/board/chapters) — kyunki library entry ko filter-able
# hona chahiye ("Class 8 → Science → Microorganisms → NCERT book").
#
# `extra="allow"` isliye: jab frontend naya field add kare (jaise `urlStatus`),
# backend use chup-chaap drop na kare — wahi bug PaperDraftCreate ke saath hua tha.


class SourceCreate(BaseModel):
    """`POST /exams/sources` (aur upload ka metadata) ka body."""

    title: str = Field(min_length=1, max_length=200)
    sourceType: str = (
        "D"  # frontend ka code: "A".."G" (service sematic kind banata hai)
    )
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
    grade_class_id: int | None = None
    subject_id: int | None = None
    version: int = Field(default=1, ge=1)

    # ---- dedup / versioning (Phase 3.1) ----
    # `contentHash` — client ne pehle se hash nikaal liya ho to bhej de (upload
    # flow file ke bytes ka sha256 bhejta hai). Khaali chhodo to server khud
    # compute karta hai (text/URL/notes ke liye).
    contentHash: str | None = None
    # `replacesId` — ye source kis purane source ko replace kar raha hai
    # (re-upload/version): purane ke stale vectors delete ho jaate hain.
    replacesId: int | None = None

    model_config = ConfigDict(extra="allow")


class SourceRead(BaseModel):
    """Content Library ka ek row (frontend `SourceLibraryItem` ka superset).

    `status`/`chunk_count`/`error` ingestion ka sach batate hain:
        pending → ingesting → ready (chunks>0) | failed (error mein wajah)
    """

    id: int
    title: str
    sourceType: str  # "A".."G" (frontend ko wahi code wapas milta hai)
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
    # true = ye response kisi **pehle se mojood** source ka hai (same content
    # dobara save hua tha) → frontend usi `id` ko reuse kare, naya na maane.
    deduplicated: bool = False


class SourceUploadRead(BaseModel):
    """Upload ka response — file save ho gayi aur ingest background mein lag gaya."""

    sourceId: int
    storageKey: str
    status: str = "pending"
    message: str = ""
    # true = same file pehle se indexed thi, isliye naya ingest nahi chala
    deduplicated: bool = False


class IngestResultRead(BaseModel):
    """Ingest ka result (diagnostics + teacher ko saaf wajah)."""

    sourceId: int
    status: str
    chunks: int = 0
    pages: int = 0
    collection: str | None = None
    warnings: list[str] = []
    error: str | None = None
