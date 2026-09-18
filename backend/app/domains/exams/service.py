# ============================================================
# Exam/Paper service — BUSINESS LOGIC (blueprint §2.9).
#
# Policy (production):
#   · router patli (HTTP + validation), repo dumb (SQL),
#     SERVICE = dimaag: rules, checks, gates, errors yahin.
#   · Har "mila nahi" → HTTPException(404). Har rule-tod → 4xx.
# ============================================================

import copy
import logging
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import Session

from . import repository
from .models import GenerationJob, PaperDraft, PaperStatus
from .schemas import GenerationRequest, PaperDraftCreate, QuestionIn, QuestionPatch

logger = logging.getLogger("eduverse.exams.service")


# ------------------------------------------------------------
# Helpers (private — `_` prefix = module ke andar ka internal)
# ------------------------------------------------------------


def _get_paper_or_404(session: Session, paper_id: int) -> PaperDraft:
    """Paper missing → 404. Ye pattern har endpoint mein dohrayega.

    Sorta service ka sabse common helper — "pehle resource dhundo,
    nahi mila to jaldi 404 bhej do (badme garbage handle mat karo)".
    """
    paper = repository.get_paper_by_id(session, paper_id)
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found",
        )
    return paper


def new_trace_id() -> str:
    """Har job ka unique log id — debugging + logs mein bharosa."""
    return f"tr-{uuid4().hex[:12]}"


# ------------------------------------------------------------
# Draft save — POST /exams/papers
# ------------------------------------------------------------


def save_draft(
    session: Session,
    payload: PaperDraftCreate,
    paper_id: int | None = None,
    created_by: int | None = None,
) -> PaperDraft:
    """Validated schema → repository upsert.

    `model_dump(exclude_unset=True)` = sirf wahi fields jo client ne
    bheji hain (defaults DB model khud laga lega). Update me bhi safe:
    jo field nahi bhejna, woh overwrite nahi hoga.
    """
    data = payload.model_dump(exclude_unset=True)
    return repository.upsert_paper(session, data, paper_id, created_by)


def get_paper(session: Session, paper_id: int) -> PaperDraft:
    """Paper fetch (404 wala helper) — aur bhi aane wale features ise use karenge."""
    return _get_paper_or_404(session, paper_id)


# ------------------------------------------------------------
# Generation enqueue — POST /exams/papers/generate
# ------------------------------------------------------------


def enqueue_generation(
    session: Session,
    paper_id: int,
    request: GenerationRequest,
) -> GenerationJob:
    """Generate request → job record banao (status=queued).

    Snapshots = request ka blueprint + coverage plan freeze at job start.
    Phase 3 mein yahin ARQ pe enqueue hoga; abhi bas record ban gaya hai.
    """
    paper = _get_paper_or_404(session, paper_id)
    job = repository.create_generation_job(
        session,
        paper_id=paper.id,
        blueprint_snapshot=request.blueprint
        and [b.model_dump() for b in request.blueprint],
        coverage_snapshot=request.coverage_plan.model_dump(),
        trace_id=new_trace_id(),
    )
    logger.info("generation queued paper=%s job=%s", paper_id, job.id)
    return job


def get_job_status(session: Session, paper_id: int) -> GenerationJob:
    """Polling: paper ka latest job. Job nahi → 404."""
    job = repository.get_latest_job_by_paper(session, paper_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No generation job for paper {paper_id} yet",
        )
    return job


# ------------------------------------------------------------
# Recommend marks — question type/difficulty/length se
# ------------------------------------------------------------
# Same base-map jo frontend (`DEFAULT_MARKS_BY_TYPE`) rakhta hai —
# server-side source of truth is HERE (frontend kabhi trust nahi karte).

BASE_MARKS_BY_TYPE: dict[str, int] = {
    "MCQ": 1,
    "TrueFalse": 1,
    "FillBlanks": 1,
    "Match": 2,
    "AssertionReason": 2,
    "MultipleSelect": 2,
    "VeryShort": 1,
    "Short": 2,
    "Long": 4,
    "Essay": 5,
    "CaseStudy": 5,
    "Diagram": 3,
    "Map": 2,
    "Graph": 3,
    "LabelDiagram": 2,
}


def recommend_marks(
    qtype: str, difficulty: str = "Medium", text_length: int = 0
) -> int:
    """Production-style recommendation rule (deterministic, testable).

    base (type ke hisaab se) + Hard bonus + lamba text bonus → clamp 1..10.
    AI/LLM recommend marks nahi karega — rule-based hamesha predictable.
    """
    marks = BASE_MARKS_BY_TYPE.get(qtype, 2)
    if difficulty == "Hard":
        marks += 1
    if text_length > 120:
        marks += 1
    if text_length > 300:
        marks += 1
    return max(1, min(marks, 10))


# ------------------------------------------------------------
# Custom question — POST /exams/questions/custom
# ------------------------------------------------------------


def add_custom_question(
    session: Session,
    paper_id: int,
    question: QuestionIn,
) -> PaperDraft:
    """Teacher ka question part_b mein append karo (origin=teacher).

    recommendedMarks frontend bhej sakta hai, warna server khud lagayega —
    isi layering ko "recommended marks computed server-side" kehte hain.
    """
    paper = _get_paper_or_404(session, paper_id)
    part_b = list(paper.part_b or [])

    q = question.model_dump(exclude_unset=True)
    q["id"] = q.get("id") or f"tq-{uuid4().hex[:8]}"
    q["origin"] = "teacher"
    if q.get("recommendedMarks") is None:
        q["recommendedMarks"] = recommend_marks(
            question.type, question.difficulty, len(question.text or "")
        )
    part_b.append(q)

    return repository.update_paper(session, paper, {"part_b": part_b})


# ------------------------------------------------------------
# Patch question — PATCH /exams/papers/{id}/questions/{qid}
# ------------------------------------------------------------


def _apply_patch(questions: list, qid: str, updates: dict) -> bool:
    """Questions ki list mein qid dhundho aur updates laga do.

    Latex ke hisaab se part_a/part_b dono JSON lists hain — is helper se
    dono mein same logic chalega.
    """
    for q in questions:
        if q.get("id") == qid:
            for key, value in updates.items():
                q[key] = value
            return True
    return False


def patch_question(
    session: Session,
    paper_id: int,
    qid: str,
    patch: QuestionPatch,
) -> PaperDraft:
    """Question lock/edit/rebalance. `regenerate: true` = Phase 2 ka kaam.

    JSONB GOTCHA (yahan solving ki):
      SQLAlchemy JSON columns ko STRUCTURE se compare karta hai —
      isliye stored list ko IN-PLACE mutate karke wahi object wapas
      assign karne par UPDATE chalti hi nahi (committed snapshot bhi
      wahi mutated object hai).
      FIX: pehle deepcopy (fresh object), copy pe mutate karo,
      phir assign karo — ab committed se structure alag = dirty ✓
    """
    paper = _get_paper_or_404(session, paper_id)
    updates = patch.model_dump(exclude_unset=True, exclude={"regenerate"})

    found = False
    data: dict = {}

    # part_a (AI) — list form
    if isinstance(paper.part_a, list):
        part_a = copy.deepcopy(paper.part_a)
        if _apply_patch(part_a, qid, updates):
            found = True
            data["part_a"] = part_a
    # part_a (AI) — dict form {sections:[{questions:[...]}]}
    elif isinstance(paper.part_a, dict):
        part_a = copy.deepcopy(paper.part_a)
        for sec in part_a.get("sections") or []:
            if isinstance(sec.get("questions"), list) and _apply_patch(
                sec["questions"], qid, updates
            ):
                found = True
        if found:
            data["part_a"] = part_a

    # part_b (teacher)
    if isinstance(paper.part_b, list):
        part_b = copy.deepcopy(paper.part_b)
        if _apply_patch(part_b, qid, updates):
            found = True
            data["part_b"] = part_b

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {qid} not found in paper {paper_id}",
        )

    return repository.update_paper(session, paper, data)


# ------------------------------------------------------------
# Finalize — POST /exams/papers/{id}/finalize
# ------------------------------------------------------------


def _all_questions(paper: PaperDraft) -> list:
    """part_a + part_b ke saare questions ek list mein (finalize ke liye)."""
    questions: list = []
    if isinstance(paper.part_a, list):
        questions.extend(paper.part_a)
    elif isinstance(paper.part_a, dict):
        for sec in paper.part_a.get("sections") or []:
            questions.extend(sec.get("questions") or [])
    if isinstance(paper.part_b, list):
        questions.extend(paper.part_b)
    return questions


def finalize_paper(
    session: Session, paper_id: int, note: str | None = None
) -> PaperDraft:
    """HARD GATE: marks contract se approve hokar paper final.

    1. paper mila? (404)
    2. questions ka sum == total_marks? (409 agar fail)
    3. sab OK → status=approved (finalize → publish/export ready)
    """
    paper = _get_paper_or_404(session, paper_id)
    questions = _all_questions(paper)

    planned = sum(int(q.get("marks", 0)) for q in questions)
    if planned != paper.total_marks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Marks Contract fail on finalize: questions total {planned} "
                f"!= paper total_marks {paper.total_marks}"
            ),
        )

    if paper.status == PaperStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper already approved",
        )

    logger.info("finalize paper=%s (note=%s)", paper_id, note)
    return repository.update_paper(session, paper, {"status": PaperStatus.approved})
