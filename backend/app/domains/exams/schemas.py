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
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .models import CoverageMode, GenerationJobStatus, PaperStatus


# ------------------------------------------------------------
# Blueprint section — frontend BlueprintSection.js se 1:1
#   { type, count, marksEach, hasImage? }
# ------------------------------------------------------------

class BlueprintSectionIn(BaseModel):
    type: str = Field(min_length=1)          # "MCQ", "Short", "Long", ...
    count: int = Field(ge=0)                  # kitne questions is type ke
    marksEach: int = Field(ge=1)              # har question ke marks
    hasImage: bool | None = None              # optional (diagram types)


def blueprint_total(blueprint: list[BlueprintSectionIn]) -> int:
    """Marks Contract ka "expected" total = Σ (count × marksEach)."""
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
    targetMarks: int = Field(default=0, ge=0)   # marks (marks mode) ya % (percent mode)
    auto: bool = True                            # true = target 0 hai, Random se bheghega
    topics: list[CoverageTopicIn] = []


class CoveragePlanIn(BaseModel):
    mode: CoverageMode = CoverageMode.auto
    chapters: list[CoverageChapterIn] = []
    totalAllocated: int = Field(default=0, ge=0)   # frontend ka computed sum


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
    image: dict[str, Any] | None = None       # ImageRef shape (frontend)
    sourceRefs: list[str] = []
    locked: bool = False
    origin: str = "teacher"                   # "ai" | "teacher"
    recommendedMarks: int | None = Field(default=None, ge=1)
    markingScheme: str | None = None


# ------------------------------------------------------------
# Sources (generation request ke saath) — frontend SourceItem.js se 1:1
# ------------------------------------------------------------

class SourceIn(BaseModel):
    id: str = ""
    sourceType: str = "text"                  # "A"|"B"|"C"|"D"|"E"|"F"|"G"
    label: str
# ------------------------------------------------------------
# PaperDraftCreate — POST /exams/papers ka body
# STAR: yahin Marks Contract + Coverage Rule server-side validate
# hote hain — galat data API tak aate hi 422 reject ho jata hai.
# ------------------------------------------------------------

class PaperDraftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    grade_class_id: int | None = None          # Phase 1: optional (frontend IDs nahi bhejta)
    subject_id: int | None = None
    total_marks: int = Field(ge=1, le=500)     # Marks Contract ka target
    duration_minutes: int = Field(default=60, ge=1, le=600)
    blueprint: list[BlueprintSectionIn] = []
    coverage_mode: CoverageMode = CoverageMode.auto
    coverage_plan: CoveragePlanIn = CoveragePlanIn()
    part_b: list[QuestionIn] = []              # teacher ke custom questions

    @model_validator(mode="after")
    def check_marks_contract(self) -> "PaperDraftCreate":
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
    def check_coverage_within_cap(self) -> "PaperDraftCreate":
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


# ------------------------------------------------------------
# GenerationRequest — POST /exams/papers/generate ka body
# ------------------------------------------------------------

class GenerationRequest(BaseModel):
    paper_id: int = Field(ge=1)             # generate kis paper ke liye
    blueprint: list[BlueprintSectionIn] = []
    coverage_plan: CoveragePlanIn = CoveragePlanIn()
    sources: list[SourceIn] = []
    instructions: list[str] = []
    total_marks: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def check_marks_contract(self) -> "GenerationRequest":
        total = blueprint_total(self.blueprint)
        if self.blueprint and total != self.total_marks:
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
    total_marks: int
    duration_minutes: int
    blueprint: Any                    # JSON column ke liye flexible
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
    id: int
    paper_id: int
    status: GenerationJobStatus | str
    stages: dict[str, Any] = {}
    error: str | None = None
    trace_id: str | None = None
    model_info: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class GenerateResponse(BaseModel):
    questions: list[QuestionIn]
    paper_id: int | None = None


# ------------------------------------------------------------
# PATCH /papers/{id}/questions/{qid} — partial update
# ------------------------------------------------------------

class QuestionPatch(BaseModel):
    mark: int | None = Field(default=None, ge=1)   # rebalance (marks badlo)
    text: str | None = None
    answer: str | None = None
    topic: str | None = None
    chapter: str | None = None
    locked: bool | None = None
    regenerate: bool | None = None                  # AI se naya generate karo


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
    note: str | None = None
    kind: str = "knowledge"                   # "knowledge" | "pattern"
    strictness: str = "Flexible"
    chapters: list[str] = []
    teacherName: str | None = None
    pages: str | None = None
    tags: list[str] = []
    fileName: str | None = None
    fileSize: str | None = None
    url: str | None = None
    textExcerpt: str | None = None
    bankRef: str | None = None