# ============================================================
# Exam/Paper schemas (blueprint §2.9) — Pydantic ke request/response
# contracts. Yahi jagah hai jahan "frontend kabhi trust nahi karte"
# ka rule asal mein dikhta hai — server-side validation.
#
# Kaunse schemas:
#   PaperDraftCreate   — POST /exams/papers (Marks Contract check yahin)
#   PaperDraftRead     — draft ka response contract (context + plan + output)
#   GenerationRequest  — POST /exams/papers/generate (sirf paper_id bhejo)
#   QuestionSlot       — blueprint ka khaali slot (LLM ise bharta hai)
#   QuestionIn/Read    — question shape (AI + teacher dono)
#   SourceIn           — source jo teacher ne Step-2 mein add kiya
#   PaperScopeIn       — include/exclude topics + concept coverage
#   PaperConstraintsIn — generation ke rules (noDuplicates, minDiagram...)
#   JobRead            — generation job ka poll response (+ result summary)
#   QuestionPatch      — PATCH /questions/{qid}
#   GenerateResponse   — generate ka response
#   MarksSuggestion*   — POST /questions/recommend-marks (File 18)
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
# Sources (paper ke saath) — frontend SourceItem.js se 1:1
# ------------------------------------------------------------


class SourceIn(BaseModel):
    """Ek source jo teacher ne Step-2 (Source) mein add kiya.

    Pehle isme sirf 3 field the — aur baaki source fields galti se
    `FinalizeRequest` ke andar chale gaye the (File 11 mein fix hua).
    Ab frontend ka poora SourceItem shape yahin hai.
    """

    id: str = ""
    sourceType: str = "text"  # "pdf" | "image" | "url" | "text" | "bank" | "bundle"
    label: str  # teacher ka diya hua naam ("NCERT Ch2 · page 12-28")
    kind: str = "knowledge"  # "knowledge" (source se banao) | "pattern" (style copy)
    strictness: str = "Flexible"  # "Strict" | "Flexible" | "Creative"
    chapters: list[str] = []  # is source ke chapters
    teacherName: str | None = None
    pages: str | None = None  # "12-28"
    tags: list[str] = []
    fileName: str | None = None  # PDF/image ka original name
    fileSize: str | None = None  # "2.4 MB" (display string)
    url: str | None = None
    textExcerpt: str | None = None  # pasted notes ka excerpt
    bankRef: str | None = None  # question bank ka reference


# ------------------------------------------------------------
# Scope — frontend PaperScope se 1:1
#   { chapterWeights, includeTopics, excludeTopics, conceptCoverage }
# ------------------------------------------------------------


class ScopeChapterWeightIn(BaseModel):
    chapter: str = ""
    pct: int = Field(default=0, ge=0, le=100)


class PaperScopeIn(BaseModel):
    """Content scope — chapters/topics ka fine control (Step 2 se aata hai)."""

    chapterWeights: list[ScopeChapterWeightIn] = []
    includeTopics: list[str] = []
    excludeTopics: list[str] = []
    conceptCoverage: list[str] = []


# ------------------------------------------------------------
# Constraints — frontend PaperConstraints se 1:1
#   { noDuplicates, noAnswerLeak, sourceOnly, minApplication, minDiagram, avoidReuse }
# ------------------------------------------------------------


class PaperConstraintsIn(BaseModel):
    """Generation ke rules — AI ko inhi ke andar rehna hai (Step 4)."""

    noDuplicates: bool = True  # semantic duplicate questions nahi
    noAnswerLeak: bool = True  # question mein answer chhupa na ho
    sourceOnly: bool = True  # sirf uploaded source se
    minApplication: int = Field(default=1, ge=0, le=20)  # kam se kam N application Q
    minDiagram: int = Field(default=1, ge=0, le=20)  # kam se kam N diagram-based Q
    avoidReuse: bool = True  # pichhle papers ke questions avoid karo


# ------------------------------------------------------------
# PaperDraftCreate — POST /exams/papers ka body
# STAR: yahin Marks Contract + Coverage Rule server-side validate
# hote hain — galat data API tak aate hi 422 reject ho jata hai.
# ------------------------------------------------------------


class PaperDraftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    grade_class_id: int | None = None  # Phase 1: optional (frontend IDs nahi bhejta)
    subject_id: int | None = None

    # ---- Paper context (Phase 2 — AI prompt ka fuel) ----
    # Bina inke AI generic questions banata hai; inke saath chapter-specific.
    class_name: str = Field(default="", max_length=20)  # "8"
    subject: str = Field(default="", max_length=100)  # "Science"
    board: str = Field(default="", max_length=50)  # "CBSE"
    exam_type: str = Field(default="", max_length=50)  # "Unit Test"
    language: str = Field(default="English", max_length=50)
    chapters: list[str] = []  # Step-2 mein select kiye chapters

    # ---- Sources + instructions + scope + constraints (frontend Steps) ----
    sources: list[SourceIn] = []
    instructions: list[str] = []
    scope: PaperScopeIn = PaperScopeIn()
    constraints: PaperConstraintsIn = PaperConstraintsIn()

    # ---- Plan + output ----
    total_marks: int = Field(ge=1, le=500)  # Marks Contract ka target
    duration_minutes: int = Field(default=60, ge=1, le=600)
    blueprint: list[BlueprintSectionIn] = []
    coverage_mode: CoverageMode = CoverageMode.auto
    coverage_plan: CoveragePlanIn = CoveragePlanIn()
    part_b: list[QuestionIn] = []  # teacher ke custom questions

    @model_validator(mode="after")
    def check_marks_contract(self) -> PaperDraftCreate:
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
    def check_coverage_within_cap(self) -> PaperDraftCreate:
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
    """POST /exams/papers/generate ka body (Phase 2).

    **Design change (Phase 2):** ab sirf `paper_id` bhejna kaafi hai. Baaki sab
    — blueprint, coverage_plan, sources, instructions, total_marks — SERVER
    **paper record se** padhta hai.

    Kyun: "frontend kabhi trust nahi karte" (production principle #2).
    Marks Contract ka source of truth **DB hai**, request body nahi. Warna
    koi bhi client aake blueprint badal kar galat paper banwa sakta hai.

    Neeche wale sirf **optional overrides** hain (backward compatibility +
    tests ke liye). Server inhe paper ke values se replace karta hai — yaani
    request mein bhejo to bhi DB jeetega.
    """

    paper_id: int = Field(ge=1)

    # ---- optional overrides (server paper se replace karega) ----
    blueprint: list[BlueprintSectionIn] | None = None
    coverage_plan: CoveragePlanIn | None = None
    sources: list[SourceIn] | None = None
    instructions: list[str] | None = None
    total_marks: int | None = Field(default=None, ge=1, le=500)

    force: bool = False  # true = chal raha job ho to bhi naya job banao

    @model_validator(mode="after")
    def check_marks_contract(self) -> GenerationRequest:
        """Override diya ho to bhi Marks Contract check (defence in depth)."""
        if self.blueprint and self.total_marks:
            total = blueprint_total(self.blueprint)
            if total != self.total_marks:
                raise ValueError(
                    f"Marks Contract fail: blueprint total {total} "
                    f"!= total_marks {self.total_marks}"
                )
        return self


# ------------------------------------------------------------
# Generation ka internal plan — service + llm layer ke beech
# ------------------------------------------------------------


class QuestionSlot(BaseModel):
    """Blueprint ka ek "khaali slot" — LLM ise bhar deta hai.

    Ye hamare architecture ka core idea hai: **AI se marks ka faisla nahi
    karate**. Hum pehle deterministic plan banate hain (`type, marks,
    difficulty, chapter, topic`), phir LLM sirf uska *content* likhta hai.
    Isse Marks Contract kabhi nahi tootega.
    """

    slot_id: str  # "Q1", "Q2", ...
    type: str  # "MCQ" | "Short" | "Long" ...
    marks: int = Field(ge=1)
    difficulty: str = "Medium"
    bloom: str = "Understand"
    chapter: str = ""
    topic: str = ""
    hasImage: bool = False
    origin: str = "ai"  # ye slot AI bharega; teacher question part_b mein hai


# ------------------------------------------------------------
# Responses — PAPER
# ------------------------------------------------------------


class PaperDraftRead(BaseModel):
    id: int
    title: str
    grade_class_id: int | None = None
    subject_id: int | None = None

    # ---- Paper context (Phase 2) — frontend inhi se wizard rehydrate karta hai ----
    class_name: str = ""
    subject: str = ""
    board: str = ""
    exam_type: str = ""
    language: str = "English"
    chapters: list[str] = []
    sources: Any = []
    instructions: list[str] = []
    scope: Any = {}
    constraints: Any = {}

    # ---- Plan + output ----
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
    id: int
    paper_id: int
    status: GenerationJobStatus | str
    stages: dict[str, Any] = {}
    # `result` = job ke aakhir mein summary. DB mein alag column nahi banaya —
    # `stages["result"]` mein hi rehta hai (migration bachaayi). Service ise
    # yahan expose karta hai: {question_count, marks_total, ai_budget, trimmed}
    result: dict[str, Any] = {}
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
    """POST /papers/{id}/finalize ka body.

    NOTE (File 11 fix): pehle isme **source ke fields** (kind, strictness,
    chapters, teacherName, pages, tags, fileName, fileSize, url, textExcerpt,
    bankRef) galti se chale gaye the — copy-paste accident. Ab ye sirf `note`
    rakhta hai; source fields apni jagah (`SourceIn`) par hain.
    """

    note: str | None = None


# ------------------------------------------------------------
# POST /questions/recommend-marks — server-side marks suggestion (File 18)
# ------------------------------------------------------------


class MarksSuggestionRequest(BaseModel):
    """Teacher ka adhoora question → server suggested marks dega.

    Frontend jab "Add my question" form kholta hai, tab ye call karta hai —
    taaki teacher ko ek **reasonable default** mile (aur woh chahe to badal de).
    """

    type: str = Field(default="Short", description="Question type, e.g. MCQ, Long.")
    difficulty: str = Field(default="Medium", description="Easy | Medium | Hard.")
    text: str = Field(
        default="", description="Question text (length se marks badhte hain)."
    )
    use_llm: bool = Field(
        default=False,
        description="True = judge model se second opinion (slow). Default rules-only.",
    )


class MarksSuggestionRead(BaseModel):
    """Suggestion + **kyun** — teacher ko reason dikhana trust banata hai."""

    marks: int
    base: int
    source: str  # "rules" | "rules+llm"
    reasons: list[str] = Field(default_factory=list)
