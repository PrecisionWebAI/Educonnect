# ============================================================
# Exam/Paper service — BUSINESS LOGIC (blueprint §2.9).
#
# Policy (production):
#   · router patli (HTTP + validation), repo dumb (SQL),
#     SERVICE = dimaag: rules, checks, gates, errors yahin.
#   · Har "mila nahi" → HTTPException(404). Har rule-tod → 4xx.
#
# ------------------------------------------------------------
# ⭐ File 17: BACKGROUND GENERATION RUNNER (is file ka naya hissa)
# ------------------------------------------------------------
# Aaj ke naap se: 2 MCQ = 115s, judge = 70s. Poora 30-mark paper ≈ 15-25 min.
# Isliye HTTP request mein generate karna **namumkin** hai. Flow:
#
#   POST /papers/generate   → job banao (status=queued) → 201 TURANT
#                              + background task schedule (BackgroundTasks)
#   (background) run_generation()  → running → progress → done/failed
#   GET  /papers/{id}/job   → frontend poll kare (progress bar + result)
#
# BackgroundTasks vs ARQ (Phase 3):
#   · BackgroundTasks = process ke andar hi chalta hai. Simple, zero setup.
#     Kami: server restart pe job kho jata hai, aur ek worker process hi hai.
#   · ARQ (Redis) = alag worker process, retry, restart-safe. Wahi `run_generation`
#     wahan bhi chalega — sirf caller badlega. Isliye runner ko **DB-driven**
#     rakha hai (job_id se sab kuch padhta hai), HTTP/queue se anjaan.
# ============================================================

import copy
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.db import engine
from app.domains.exams.llm import services as llm_services
from app.domains.exams.llm.base import is_llm_available
from app.domains.exams.llm.generator import generate_section

from . import repository
from .models import GenerationJob, GenerationJobStatus, PaperDraft, PaperStatus
from .schemas import (
    GenerationRequest,
    JobRead,
    PaperDraftCreate,
    QuestionIn,
    QuestionPatch,
)

logger = logging.getLogger("eduverse.exams.service")

# Job ka "kind" — ek hi lifecycle (queued→running→done), do kaam.
# `graph_state` mein rehta hai (naya column nahi banaya = migration bachi).
KIND_PAPER = "paper"
KIND_QUESTION = "question"


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

    **Phase 2 design:** plan **paper record se** padha jata hai (DB = source of
    truth). `GenerationRequest` ke fields sirf optional override hain.

    Yahan 3 gate lagte hain (production ke hard rules):
      1. blueprint maujood hona chahiye (bina plan generate nahi)
      2. Marks Contract: blueprint total == total_marks (409 warna)
      3. Pehle se queued/running job → 409 (duplicate run nahi; `force` se bypass)

    Snapshots = job start par config freeze, taaki baad mein paper badle to
    bhi is job ka apna plan rahe.
    """
    paper = _get_paper_or_404(session, paper_id)

    blueprint = (
        [b.model_dump() for b in request.blueprint]
        if request.blueprint is not None
        else paper.blueprint
    )
    coverage = (
        request.coverage_plan.model_dump()
        if request.coverage_plan is not None
        else paper.coverage_plan
    )
    total_marks = (
        request.total_marks if request.total_marks is not None else paper.total_marks
    )

    # --- Gate 1: plan hona chahiye ---
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper has no blueprint — save the blueprint before generating",
        )

    # --- Gate 2: Marks Contract (server-side, DB values par) ---
    planned = sum(
        int(s.get("count", 0)) * int(s.get("marksEach", 0))
        for s in blueprint
        if isinstance(s, dict)
    )
    if planned != total_marks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Marks Contract fail: blueprint total {planned} "
                f"!= total_marks {total_marks}"
            ),
        )

    # --- Gate 3: duplicate run se bacho ---
    if not request.force:
        latest = repository.get_latest_job_by_paper(session, paper.id)
        if latest is not None and latest.status in (
            GenerationJobStatus.queued,
            GenerationJobStatus.running,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Generation already {latest.status} for paper {paper.id} "
                    f"(job {latest.id}) — wait or pass force=true"
                ),
            )

    job = repository.create_generation_job(
        session,
        paper_id=paper.id,
        blueprint_snapshot={"blueprint": blueprint, "total_marks": total_marks},
        coverage_snapshot=coverage if isinstance(coverage, dict) else {},
        trace_id=new_trace_id(),
        # `kind="paper"` explicitly — runner `graph_state.kind` dekhta hai.
        # (Default bhi "paper" hai, par explicit likhna debugging mein saaf hai:
        # logs/polling mein "ye job kis baare mein tha" turant dikhta hai.)
        graph_state={"kind": KIND_PAPER},
    )
    logger.info(
        "generation queued paper=%s job=%s plan=%s marks, budget=%s marks",
        paper_id,
        job.id,
        planned,
        total_marks - _part_b_marks(paper),
    )
    return job


def _part_b_marks(paper: PaperDraft) -> int:
    """Teacher ke custom questions ka total marks (`part_b` se).

    AI ka budget = total_marks - part_b_marks (Marks Contract ka doosra hissa).

    **File 17:** logic ab `llm.services.part_b_marks()` mein hai — pehle ye
    code do jagah tha (service + llm layer), aur dono jagah "list ya dict?"
    ka wahi sawaal tha. Ek hi jagah rakhna = ek hi din ek jagah fix karna.
    """
    return llm_services.part_b_marks(paper)


def job_read(job: GenerationJob) -> JobRead:
    """GenerationJob → JobRead (polling response).

    `result` DB mein alag column nahi hai — `stages["result"]` se expose hota
    hai (isse ek migration bacha). Frontend ko sirf itna chahiye:
    {question_count, marks_total, ai_budget, trimmed}.
    """
    return JobRead(
        **job.model_dump(),
        result=(job.stages or {}).get("result", {}),
    )


def get_job_status(session: Session, paper_id: int) -> JobRead:
    """Polling: paper ka latest job (result summary ke saath). Job nahi → 404."""
    job = repository.get_latest_job_by_paper(session, paper_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No generation job for paper {paper_id} yet",
        )
    return job_read(job)


# ------------------------------------------------------------
# Recommend marks — question type/difficulty/length se
# ------------------------------------------------------------
# Base map ki ek hi copy ab `llm/services.py` mein hai (File 16). File 17 mein
# service usi ko **delegate** karta hai — pehle yahi map do jagah tha, jo
# classic "drift" ka rasta hai (ek jagah badla, doosri jagah bhool gaye).


def recommend_marks(
    qtype: str, difficulty: str = "Medium", text_length: int = 0
) -> int:
    """Production-style recommendation rule (deterministic, testable).

    Marks **AI se nahi** aate — rule-based hamesha predictable, kyunki marks
    Marks Contract ka hissa hai. Ab logic `llm.services.suggest_marks()` mein
    hai (rules-only path), aur ye function sirf wrapper hai:
    → purane callers (aur tests) ka behaviour bilkul same rehta hai.
    """
    result = llm_services.suggest_marks(
        {"type": qtype, "difficulty": difficulty},
        text_length=text_length,
    )
    return int(result["marks"])


def suggest_question_marks(
    qtype: str,
    difficulty: str = "Medium",
    text: str = "",
    use_llm: bool = False,
) -> dict[str, Any]:
    """Marks suggestion **+ kyun** (reasons ke saath) — API endpoint ke liye.

    `recommend_marks` sirf number deta hai (purane callers ke liye). Ye function
    poora payload deta hai taaki UI teacher ko **wajah** dikha sake:
        marks 2 | base 1 | reasons ["base for Short = 2", "Hard difficulty +1"]
    Trust ke liye reason zaroori hai — "server ne 2 bola" se teacher convince
    nahi hota, "Short + Hard = 2" se hota hai.
    """
    return llm_services.suggest_marks(
        {"type": qtype, "difficulty": difficulty, "text": text},
        use_llm=use_llm,
    )


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
    """Question lock/edit/rebalance. `regenerate: true` = AI se dobara banao.

    **File 17:** `regenerate=true` ab **job banata hai** (side effect), aur
    actual regeneration background mein hoti hai (ek question ≈ 60-120s — HTTP
    request itni der nahi ruk sakti). Job banane ka kaam `enqueue_regeneration()`
    karta hai, jo pehle validate karta hai (404/409) — isliye hum use **updates
    se pehle** bulate hain: agar question locked hai to 409 mile, aur paper
    mein aadha-adhoora change na ho.

    Router (File 18) is side effect ko dekh kar background task schedule karta
    hai (`patch_in.regenerate` true hone par). Return type `PaperDraft` hi rakha
    hai — purane callers (frontend, tests) ka contract nahi toota.

    JSONB GOTCHA (yahan solving ki):
      SQLAlchemy JSON columns ko STRUCTURE se compare karta hai —
      isliye stored list ko IN-PLACE mutate karke wahi object wapas
      assign karne par UPDATE chalti hi nahi (committed snapshot bhi
      wahi mutated object hai).
      FIX: pehle deepcopy (fresh object), copy pe mutate karo,
      phir assign karo — ab committed se structure alag = dirty ✓
    """
    # --- regenerate: pehle job banao (validation bhi isi mein hai) ---
    if patch.regenerate:
        enqueue_regeneration(session, paper_id, qid)

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


# ============================================================
# FILE 17 — BACKGROUND GENERATION RUNNER
# ============================================================
#
# 4 functions, aur har ek ka ek hi kaam:
#   enqueue_regeneration()          → ek question dobara banane ka job banao
#   run_generation()                → ASLI KAAM (status machine + error handling)
#   run_generation_in_background()  → FastAPI BackgroundTasks ka entry (apna session)
#   _run_paper_generation() / _run_question_regeneration()
#                                   → do "kaam" (kind) ke implementations
#
#  Rule: runner **DB-driven** hai — sirf `job_id` se shuru hota hai aur job
#    record se sab padhta hai (paper, plan, kind, qid). Isliye Phase 3 mein
#    ARQ/Redis pe shift karne par **ye code nahi badlega**, sirf caller badlega.
# ============================================================


def _now_iso() -> str:
    """Timezone-aware ISO timestamp — logs/JSON mein ambiguity nahi.

    `datetime.utcnow()` (models mein hai) naive hota hai, isliye `Z`/offset ke
    bina store hone par "kis timezone mein tha?" ka sawaal baad mein khada hota
    hai. JSON columns mein hum ye aware version likhte hain.
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def _part_a_questions(paper: PaperDraft) -> list[dict]:
    """`part_a` ko flat list of questions mein badlo (do shapes handle).

    Do shapes exist karti hain (aur dono ko support karna padega):
        list  → [{id, text, ...}, ...]                     ← canonical (File 17+)
        dict  → {"sections": [{"questions": [...]}]}        ← purana/AI-sections
    Runner hamesha **flat list** likhta hai (ek canonical shape), par padhte
    waqt dono handle karta hai — backward compatibility bina migration ke.
    """
    part_a = paper.part_a

    if isinstance(part_a, list):
        return [q for q in part_a if isinstance(q, dict)]

    if isinstance(part_a, dict):
        questions: list[dict] = []
        for section in part_a.get("sections") or []:
            if isinstance(section, dict):
                questions.extend(
                    q for q in (section.get("questions") or []) if isinstance(q, dict)
                )
        return questions

    return []


def _make_progress_writer(session: Session, job: GenerationJob):
    """`progress(stage, pct, extra)` callback banao jo job ke `stages` mein likhta hai.

    ⚠️ THROTTLE kyun? Poora paper 15-25 min leta hai aur generator har batch pe
    progress bhejta hai. Agar hum har call pe DB commit karein:
      · har commit = ek UPDATE + fsync (Postgres) → saikdon bekaar writes
      · aur frontend utni hi baar poll karta hai jitni baar hum likhte hain
    Isliye: **stage badla** ya **pct 5% se zyada badla** — tabhi likho.
    Ye chhota sa guard production mein DB load aadha kar deta hai.
    """
    last: dict[str, Any] = {"stage": None, "pct": -100}

    def write(stage: str, pct: int = 0, extra: dict | None = None) -> None:
        pct = int(pct or 0)
        same_stage = stage == last["stage"]
        if same_stage and abs(pct - last["pct"]) < 5:
            return

        last["stage"], last["pct"] = stage, pct

        merged: dict[str, Any] = {"pct": pct}
        if extra:
            merged.update(extra)
        # `extra` mein kabhi `stage` key aati hai (generator bhejta hai) —
        # usse `current` overwrite karna confusion degi, isliye hata dete hain.
        merged.pop("stage", None)

        repository.update_job_status(session, job, stage=stage, extra_stages=merged)

    return write


def _fail_job(session: Session, job: GenerationJob, reason: str) -> GenerationJob:
    """Job ko failed mark karo + error message save karo + log.

    `status=failed` + `error` = frontend ko saaf wajah dikhti hai
    ("Ollama not reachable") — na ki sirf "something went wrong".
    """
    logger.error("job %s failed (paper=%s): %s", job.id, job.paper_id, reason)
    return repository.update_job_status(
        session,
        job,
        status=GenerationJobStatus.failed,
        stage="failed",
        error=reason[:2000],  # column overflow se bachao (Text limit ki fikr nahi)
        extra_stages={"failedAt": _now_iso()},
    )


# ------------------------------------------------------------
# KAAM 1 — poora paper generate (kind="paper")
# ------------------------------------------------------------


def _run_paper_generation(
    session: Session, job: GenerationJob, paper: PaperDraft
) -> dict[str, Any]:
    """Paper ke saare questions AI se banao aur `part_a` mein save karo.

    Plan **job ke snapshot se** aata hai (blueprint_snapshot / coverage_snapshot)
    — nahi ki live paper se. Kyun? Job queue mein pada tha, tab plan X tha; ab
    teacher ne plan badal diya ho sakta hai. Snapshot ki wajah se job wahi
    generate karega jo usse kaha gaya tha (reproducible + audit-able).
    """
    snapshot = job.blueprint_snapshot or {}
    blueprint = snapshot.get("blueprint")
    coverage = job.coverage_snapshot or None

    result = llm_services.generate_paper_questions(
        paper,
        blueprint=blueprint,
        coverage=coverage,
        progress=_make_progress_writer(session, job),
    )

    questions: list[dict] = result["questions"]
    summary: dict = result["summary"]

    # part_a likho + status ko in_review karo (AI draft ready = teacher review).
    # `draft` par hi badalte hain — approved paper ko wapas in_review karna
    # teacher ke approved decision ko ulta kar dena hoga, jo galat hai.
    updates: dict[str, Any] = {"part_a": questions}
    if paper.status == PaperStatus.draft:
        updates["status"] = PaperStatus.in_review

    repository.update_paper(session, paper, updates)

    logger.info(
        "job %s: paper=%s generated %s/%s questions (%s marks, budget %s)",
        job.id,
        paper.id,
        summary.get("question_count"),
        summary.get("expected_count"),
        summary.get("marks_total"),
        summary.get("ai_budget"),
    )

    return {
        "purpose": KIND_PAPER,
        "result": summary,
        # ⚠️ `llm_services.get_model_info()` dobara call **nahi** karte.
        # Test ne ye pakda: dobara call karne se woh metadata milta hai jo
        # "abhi ka default client" batata hai — ho sakta hai wo client alag ho
        # us client se jisne ASLI kaam kiya (tests mein fake, production mein
        # provider switch). Jo result ke saath aaya, wahi sach hai.
        "model_info": result.get("model_info") or llm_services.get_model_info(),
    }


# ------------------------------------------------------------
# KAAM 2 — sirf ek question dobara banao (kind="question")
# ------------------------------------------------------------


def _run_question_regeneration(
    session: Session, job: GenerationJob, paper: PaperDraft
) -> dict[str, Any]:
    """Ek AI question ko dobara banao (teacher ne "Regenerate" dabaya).

    **Marks Contract safe kyun hai?** Hum slot **purane question se** banate hain
    — same type, same marks, same chapter/topic. `generate_section` + `_merge_slots`
    marks **slot se** lete hain, model se nahi. Isliye regenerate karne se paper
    ka total marks **kabhi** nahi badalta. Yahi is feature ka poora design hai.

    Locked question kabhi regenerate nahi hota — lock ka matlab hi ye hai ki
    teacher ne us question ko freeze kiya ("iske alawa sab badlo").
    """
    state = job.graph_state or {}
    qid = str(state.get("qid") or "")

    questions = _part_a_questions(paper)
    index = next((i for i, q in enumerate(questions) if q.get("id") == qid), -1)
    if index < 0:
        raise ValueError(f"Question {qid!r} part_a mein nahi mila (paper {paper.id})")

    target = questions[index]
    if target.get("locked"):
        raise ValueError(f"Question {qid} locked hai — pehle unlock karo")

    # Purane question se slot: type/marks/chapter/topic freeze (contract safe)
    qtype = str(target.get("type") or "Short")
    slot: dict[str, Any] = {
        "slot_id": qid,
        "type": qtype,
        "marks": int(target.get("marks") or 1),
        "difficulty": target.get("difficulty") or "Medium",
        "bloom": target.get("bloom") or "Understand",
        "chapter": target.get("chapter") or "",
        "topic": target.get("topic") or "",
        "has_image": bool(target.get("hasImage")),
        "origin": "ai",
    }

    ctx = llm_services.build_ctx(paper)
    sources, excerpts = llm_services.build_sources(paper)

    # Latency naapo — ek question bhi ~60-120s leta hai (File 16 ka naap), aur ye
    # number `result.elapsed` mein frontend ko jaata hai (teacher ko realistic
    # expectation dena: "1 question = 1-2 min").
    t0 = time.time()

    # ⚠️ ANTI-REPEAT: baaki saare questions ko "already used" bhejo, **aur apne
    # purane text ko bhi** — warna model wahi question dobara likh dega.
    used = [
        str(q.get("text") or "")
        for i, q in enumerate(questions)
        if i != index and q.get("text")
    ]
    if target.get("text"):
        used.append(str(target["text"]))

    produced = generate_section(
        qtype=qtype,
        ctx=ctx,
        slots=[slot],
        sources=sources,
        excerpts=excerpts,
        constraints=ctx["constraints"],
        instructions=ctx["instructions"],
        used=used,
    )

    if not produced:
        raise RuntimeError(
            f"regeneration fail: {qid} ke liye model ne koi question nahi diya"
        )

    fresh = produced[0]
    if not str(fresh.get("text") or "").strip():
        raise RuntimeError(f"regeneration ne khaali question diya ({qid})")

    # Sirf CONTENT badalta hai — marks/type/chapter slot se hi aate hain.
    # `regeneratedAt` + `regenerateCount` traceability: teacher ko pata chale ki
    # ye question kitni baar banaya gaya (3+ baar = plan/prompt mein kuch theek
    # karne ki zaroorat hai — ye ek quality signal hai, sirf metadata nahi).
    updated_question = {
        **target,
        "text": fresh["text"],
        "answer": fresh.get("answer") or target.get("answer") or "",
        "options": fresh.get("options") or target.get("options") or [],
        "markingScheme": fresh.get("markingScheme")
        or target.get("markingScheme")
        or "",
        "incomplete": False,
        "regeneratedAt": _now_iso(),
        "regenerateCount": int(target.get("regenerateCount") or 0) + 1,
    }

    # JSONB GOTCHA (File 6): deepcopy → copy pe mutate → assign.
    # Warna SQLAlchemy ko change detect nahi hota aur UPDATE chalti hi nahi.
    new_questions = copy.deepcopy(questions)
    new_questions[index] = updated_question
    repository.update_paper(session, paper, {"part_a": new_questions})

    logger.info("job %s: regenerated %s (paper=%s)", job.id, qid, paper.id)

    return {
        "purpose": KIND_QUESTION,
        "result": {
            "question_id": qid,
            "question_count": 1,
            "marks_total": int(updated_question.get("marks") or 0),
            "regenerate_count": updated_question["regenerateCount"],
            "chapter": updated_question.get("chapter") or "",
            "elapsed": round(time.time() - t0, 1),
        },
        "model_info": llm_services.get_model_info(),
    }


# ------------------------------------------------------------
# STATE MACHINE — run_generation (asli kaam, error handling ke saath)
# ------------------------------------------------------------


def run_generation(session: Session, job_id: int) -> GenerationJob:
    """Job ko chalao: queued → running → done/failed.

    **Ye function "dumb" jaan-boojh kar hai:** ise sirf `job_id` milta hai, aur
    baaki sab job record se padhta hai. Kyun?

      · Phase 3 mein ARQ/Redis worker bhi bas `job_id` bhejega → **same code**
      · Crash ke baad dobara chalao → wahi job dobara (idempotent-ish)
      · Test karna aasaan: job banake `run_generation(session, job.id)` bula lo

    ️ Pre-flight LLM check: `is_llm_available()` — 15-25 min ka job shuru karne
    se PEHLE. Ollama band hai to teacher ko 1 second mein saaf wajah mile
    ("model not installed"), na ki 3 minute wait ke baad timeout.
    """
    job = repository.get_generation_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    # Already finished? Dobara mat chalao (duplicate runs = duplicate cost).
    if job.status in (GenerationJobStatus.done, GenerationJobStatus.canceled):
        logger.info("job %s already %s — skip", job.id, job.status)
        return job

    paper = _get_paper_or_404(session, job.paper_id)

    repository.update_job_status(
        session,
        job,
        status=GenerationJobStatus.running,
        stage="starting",
        extra_stages={"startedAt": _now_iso(), "pct": 0},
    )

    # --- Pre-flight: model zinda hai? ---
    available, reason = is_llm_available()
    if not available:
        return _fail_job(session, job, f"LLM unavailable: {reason}")

    kind = str((job.graph_state or {}).get("kind") or KIND_PAPER)
    logger.info(
        "job %s running | paper=%s | kind=%s | trace=%s",
        job.id,
        paper.id,
        kind,
        job.trace_id,
    )

    try:
        if kind == KIND_QUESTION:
            outcome = _run_question_regeneration(session, job, paper)
        else:
            outcome = _run_paper_generation(session, job, paper)

    except Exception as exc:
        # ⚠️ Exception ka TYPE bhi likho, sirf message nahi — "ValidationError:
        # Input should be a valid dictionary" jaise messages bina type ke
        # samajh nahi aate. Log mein poora traceback, DB mein chhota message.
        reason = f"{type(exc).__name__}: {exc}"
        logger.exception("job %s crashed (paper=%s)", job.id, paper.id)
        return _fail_job(session, job, reason)

    # --- Done: result + model_info + timestamps save karo ---
    finished = repository.update_job_status(
        session,
        job,
        status=GenerationJobStatus.done,
        stage="completed",
        model_info=outcome.get("model_info") or {},
        extra_stages={
            **outcome,
            "pct": 100,
            "finishedAt": _now_iso(),
        },
    )
    logger.info(
        "job %s done | kind=%s | paper=%s | %s questions",
        job.id,
        kind,
        paper.id,
        (outcome.get("result") or {}).get("question_count", "?"),
    )
    return finished


def run_generation_in_background(job_id: int) -> None:
    """FastAPI `BackgroundTasks` ka entry point — **apna session** kholta hai.

    ⚠️ Kyun naya session? Request ka session request ke saath **band** ho jata hai
    (dependency `finally` mein). Background task uske baad chalta hai — purane
    session se query karna "session closed" error deta hai. Production ka rule:

        request-scoped session ko background mein **kabhi** carry na karo.

    Isliye yahan `Session(engine)` se fresh session (aur context manager se
    band bhi ho jata hai, leak nahi).
    """
    try:
        with Session(engine) as session:
            run_generation(session, job_id)
    except Exception:
        # Background task mein exception phenkna = log mein traceback, par
        # response already ja chuka hota hai. Isliye yahan sirf log karte hain
        # (job ka status pehle hi `failed` ho chuka hoga).
        logger.exception("background generation job %s failed", job_id)


# ------------------------------------------------------------
# Regeneration enqueue — PATCH .../questions/{qid} {regenerate: true}
# ------------------------------------------------------------


def enqueue_regeneration(
    session: Session,
    paper_id: int,
    qid: str,
) -> GenerationJob:
    """Ek question dobara banane ka job banao (status=queued).

    Direct regenerate kyun nahi? Kyunki ek question bhi 60-120s leta hai. HTTP
    request utni der ruk sakti hai, par UX achha nahi hota (browser spinner,
    proxy timeout risk). Same pattern rakhte hain: job banao → poll karo.

    Gates (wahi discipline jo paper generation mein hai):
      1. paper mila? (404)
      2. question part_a mein hai? (404)
      3. locked nahi hai? (409) — lock ka matlab hi "ise na chhedo"
      4. usi question ka pehle se running job? (409)
    """
    paper = _get_paper_or_404(session, paper_id)

    questions = _part_a_questions(paper)
    target = next((q for q in questions if q.get("id") == qid), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {qid} not found in paper {paper_id}",
        )
    if target.get("locked"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Question {qid} is locked — unlock it before regenerating",
        )

    # Duplicate run check: same question ke liye pehle se job chal raha ho to
    # dobara mat bhejo — warna 2 LLM calls (paisa/time barbaad) aur dono results
    # last-write-wins se ek doosre ko overwrite kar denge.
    latest = repository.get_latest_job_by_paper(session, paper.id)
    if latest is not None and latest.status in (
        GenerationJobStatus.queued,
        GenerationJobStatus.running,
    ):
        latest_state = latest.graph_state or {}
        if latest_state.get("kind") == KIND_QUESTION and latest_state.get("qid") == qid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Regeneration already {latest.status} for {qid} "
                    f"(job {latest.id}) — poll the job status"
                ),
            )

    coverage = paper.coverage_plan if isinstance(paper.coverage_plan, dict) else {}
    job = repository.create_generation_job(
        session,
        paper_id=paper.id,
        blueprint_snapshot={
            "blueprint": paper.blueprint,
            "total_marks": paper.total_marks,
        },
        coverage_snapshot=coverage,
        trace_id=new_trace_id(),
        graph_state={"kind": KIND_QUESTION, "qid": qid},
    )
    logger.info("regeneration queued paper=%s qid=%s job=%s", paper.id, qid, job.id)
    return job
