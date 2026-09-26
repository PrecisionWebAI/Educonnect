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
import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.domains.exams.llm import services as llm_services
from app.domains.exams.llm.base import is_llm_available
from app.domains.exams.llm.generator import generate_section

from . import repository
from .models import (
    ExamSource,
    GenerationJob,
    GenerationJobStatus,
    PaperDraft,
    PaperStatus,
    SourceType,
)
from .schemas import (
    GenerationConfigRequest,
    GenerationRequest,
    JobRead,
    JobResultRead,
    PaperDraftCreate,
    QuestionIn,
    QuestionPatch,
    SourceCreate,
    SourceRead,
)

logger = logging.getLogger("eduverse.exams.service")

# Job ka "kind" — ek hi lifecycle (queued→running→done), teen kaam.
# `graph_state` mein rehta hai (naya column nahi banaya = migration bachi).
KIND_PAPER = "paper"  # saved draft se poora paper
KIND_CONFIG = "config"  # **stateless** (config_snapshot se, DB mein draft nahi)
KIND_QUESTION = "question"  # sirf ek question dobara


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

    # --- Gate 4: AI ke liye marks bache hi nahi? ---
    # Agar teacher ke custom questions (part_b) ne poora total_marks kha liya to
    # AI ko 0 marks bachte hain. Pehle ye case chup-chaap "0 questions wala done
    # job" deta tha — teacher ko samajh hi nahi aata tha ki kya hua (yahi wo
    # diagnosis tha: "AI budget = 0"). Ab saaf 409 + asli wajah.
    teacher_marks = _part_b_marks(paper)
    if total_marks - teacher_marks <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"AI ke liye 0 marks bache: custom questions (part_b) = {teacher_marks} "
                f"marks, total = {total_marks}. Custom questions ke marks kam karo ya "
                "total_marks badhao — phir generate karo."
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


# ------------------------------------------------------------
# Stateless generate — POST /exams/generate  (blueprint DB mein save NAHI hota)
# ------------------------------------------------------------


def enqueue_config_generation(
    session: Session,
    config: GenerationConfigRequest,
) -> GenerationJob:
    """Poore config se generate — **koi draft/blueprint DB mein nahi jaata**.

    Flow (aapki requirement: "blueprint DB mein save mat karo, seedha generate"):
      1. Frontend poora config (Basics + Source + Blueprint + Coverage + part_b)
         `POST /exams/generate` par bhejta hai
      2. Server **server-side** validate karta hai (Marks Contract + coverage cap —
         wahi validators jo draft save par lagte hain, kyunki base class ek hi hai)
      3. Job banta hai `paper_id=None` ke saath, aur poora config
         `config_snapshot` mein freeze hota hai (reproducible + audit-able)
      4. `run_generation()` wahi pipeline chalata hai (plan → prompts → generate →
         repair → judge), par questions `result_snapshot` mein jaate hain
      5. `GET /exams/jobs/{id}/result` se questions milte hain

    Kyun naya pipeline nahi likhna pada? Kyunki AI layer **duck-typed** hai —
    `llm_services.config_to_source()` ek `SimpleNamespace` banata hai, aur usi par
    `build_ctx`/`plan_for_paper`/`generate_all` bilkul waise chalte hain jaise
    DB row par chalte the. Storage alag, dimaag ek hi.
    """
    data = config.model_dump()
    blueprint = data.get("blueprint") or []
    total_marks = int(data.get("total_marks") or 0)
    coverage = data.get("coverage_plan") or {}

    # --- Gate 1: plan hona chahiye ---
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Config mein blueprint nahi hai — pehle Exam Blueprint step complete karo",
        )

    # --- Gate 2: Marks Contract (server-side, config values par) ---
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

    # --- Gate 3: usi draft ke liye pehle se chal raha job? (link diya ho tab) ---
    if config.link_paper_id:
        latest = repository.get_latest_job_by_paper(session, config.link_paper_id)
        if latest is not None and latest.status in (
            GenerationJobStatus.queued,
            GenerationJobStatus.running,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Generation already {latest.status} for paper {config.link_paper_id} "
                    f"(job {latest.id}) — poll karo ya force se naya banao"
                ),
            )

    # --- Gate 4: AI budget (teacher ke custom questions ke baad) ---
    teacher_marks = sum(
        int(q.get("marks") or 0)
        for q in (data.get("part_b") or [])
        if isinstance(q, dict)
    )
    if total_marks - teacher_marks <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"AI ke liye 0 marks bache: custom questions (part_b) = {teacher_marks} "
                f"marks, total = {total_marks}. Custom questions ke marks kam karo ya "
                "total_marks badhao — phir generate karo."
            ),
        )

    job = repository.create_generation_job(
        session,
        paper_id=config.link_paper_id,  # default None — config flow paper nahi likhta
        blueprint_snapshot={"blueprint": blueprint, "total_marks": total_marks},
        coverage_snapshot=coverage if isinstance(coverage, dict) else {},
        config_snapshot=data,
        trace_id=new_trace_id(),
        graph_state={"kind": KIND_CONFIG},
    )
    logger.info(
        "stateless generation queued job=%s | %s marks plan | AI budget=%s | class=%s %s",
        job.id,
        planned,
        total_marks - teacher_marks,
        data.get("class_name"),
        data.get("subject"),
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

    `result` alag column nahi chahiye — `stages["result"]` se expose hota hai
    (isse ek migration bacha). Frontend ko yahi chahiye:
    `{question_count, marks_total, ai_budget, trimmed, coverage, quality, contract}`.

    ⚠️ `result` field `JobRead` schema mein hona **zaroori** hai — warna Pydantic
    `extra="ignore"` ki wajah se yahan se chup-chaap gayab ho jaata (pehle yahi
    ho raha tha, isliye frontend ko `job.result` hamesha null milta tha).
    """
    return JobRead(
        **job.model_dump(),
        result=(job.stages or {}).get("result", {}),
    )


def get_job_result(session: Session, job_id: int) -> JobResultRead:
    """`GET /exams/jobs/{job_id}/result` — stateless generate ka output.

    Draft flow mein questions `paperdraft.part_a` se padhne padte hain, par
    stateless flow mein koi draft hi nahi hota — isliye questions + reports
    `job.result_snapshot` se aate hain. Ye endpoint frontend ke liye "ek hi
    jagah se sab kuch" deta hai (Teacher Review step isi par chalega).
    """
    job = repository.get_generation_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    payload = job.result_snapshot or {}
    return JobResultRead(
        job_id=job.id,
        paper_id=job.paper_id,
        status=job.status,
        questions=payload.get("questions") or [],
        summary=payload.get("summary") or {},
        quality=payload.get("quality") or {},
        coverage=payload.get("coverage") or [],
        error=job.error,
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
# GRAPH RUNNER — LangGraph ko service se jodne wala patla layer
# ------------------------------------------------------------


def _run_generation_graph(
    session: Session,
    job: GenerationJob,
    paper: Any,
    *,
    blueprint: Any,
    coverage_plan: Any,
    kind: str = KIND_PAPER,
) -> dict[str, Any]:
    """`llm/graph.py` ka DAG chalao — progress + checkpoint DB mein likhte hue.

    Teen cheezein yahan **jodti** hain (aur teeno service ki zimmedari hain,
    graph ki nahi):

      1. **progress** → `job.stages` (wahi throttled writer jo pehle tha) —
         frontend polling bar isi se banti hai
      2. **checkpoint** → `job.graph_state` mein `{nodes_done, current_node}` —
         server restart ho jaye to bhi pata chalta hai kahan tak kaam hua tha
         (LangGraph ka checkpoint concept, bina kisi extra service ke)
      3. **anti-repeat list** → pichhle papers ke questions (DB se)
    """
    from app.domains.exams.llm import graph as paper_graph

    progress = _make_progress_writer(session, job)

    def on_event(event: dict[str, Any]) -> None:
        node = str(event.get("node") or "")
        stage = str(event.get("stage") or node)
        pct = int(event.get("pct") or 0)
        extra = {
            k: v
            for k, v in event.items()
            if k not in ("node", "stage", "pct")
            and isinstance(v, (str, int, float, bool))
        }
        progress(stage, pct, {"node": node, **extra})

    def on_checkpoint(node: str, done: list[str], state: dict[str, Any]) -> None:
        # Har node ke baad ek chhota checkpoint (poora state nahi — job row phool
        # na jaye). `nodes_done` se resume/debug dono aasan ho jaate hain.
        try:
            repository.update_job_status(
                session,
                job,
                graph_state={
                    "kind": kind,
                    "current_node": node,
                    "nodes_done": list(done),
                    "planned_slots": len((state.get("plan") or {}).get("slots") or []),
                    "generated": len(state.get("questions") or []),
                    "repair_count": int(state.get("repair_count") or 0),
                },
            )
        except Exception as exc:  # checkpoint fail ho to kaam na ruke
            logger.warning("checkpoint write skip (node=%s): %s", node, exc)

    final_state = paper_graph.run_paper_graph(
        paper=paper,
        blueprint=blueprint,
        coverage_plan=coverage_plan,
        used=recent_used_texts(
            session,
            class_name=getattr(paper, "class_name", "") or "",
            subject=getattr(paper, "subject", "") or "",
        ),
        repair_passes=settings.EXAMS_REPAIR_PASSES,
        use_judge=settings.EXAMS_USE_LLM_JUDGE,
        on_event=on_event,
        on_checkpoint=on_checkpoint,
    )

    return {
        "questions": final_state.get("questions") or [],
        "summary": final_state.get("summary") or {},
        "nodes_done": final_state.get("nodes_done") or [],
        "model_info": llm_services.get_model_info(),
    }


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

    # LangGraph DAG (plan → retrieve → fan-out generate → check → repair → judge
    # → finalize). Progress aur checkpoint callbacks ke through DB mein jaate hain,
    # isliye graph khud DB ko chhoota nahi (layer rule).
    result = _run_generation_graph(
        session,
        job,
        paper,
        blueprint=blueprint,
        coverage_plan=coverage,
        kind=KIND_PAPER,
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

    # Anti-repeat ledger: yahi questions agli baar "already used" list mein aayenge.
    record_question_usage(
        session,
        paper_id=paper.id,
        class_name=getattr(paper, "class_name", "") or "",
        subject=getattr(paper, "subject", "") or "",
        questions=questions,
        created_by=getattr(paper, "created_by", None),
    )

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
# KAAM 1b — stateless generate (kind="config"): questions job mein, paper mein nahi
# ------------------------------------------------------------


def _run_config_generation(
    session: Session, job: GenerationJob, paper: Any
) -> dict[str, Any]:
    """Config se questions banao aur **job ke `result_snapshot` mein** rakho.

    Draft flow (`_run_paper_generation`) se sirf do farq:
      1. `paperdraft` mein kuch bhi save nahi hota (koi draft hi nahi banta) —
         yehi aapki requirement thi ("blueprint DB mein save mat karo")
      2. Questions `job.result_snapshot` mein jaate hain, jisse
         `GET /exams/jobs/{id}/result` padhta hai

    Baaki sab — plan, prompts, batching, bounded repair, quality judge, coverage
    audit — bilkul wahi pipeline. Isliye "behaviour same, storage alag".

    `paper` yahan `SimpleNamespace` hai (config se bana) — type `Any` isliye hai.
    """
    snapshot = job.blueprint_snapshot or {}
    blueprint = snapshot.get("blueprint") or getattr(paper, "blueprint", None)
    coverage = job.coverage_snapshot or getattr(paper, "coverage_plan", None) or {}

    # Wahi DAG, par questions `result_snapshot` mein jaate hain (paper row nahi banti)
    result = _run_generation_graph(
        session,
        job,
        paper,
        blueprint=blueprint,
        coverage_plan=coverage,
        kind=KIND_CONFIG,
    )

    questions: list[dict] = result["questions"]
    summary: dict = result["summary"]

    quality = summary.get("quality") or {}
    coverage_rows = summary.get("coverage") or []
    # Frontend ko saaf pata chale ki ye draft DB mein **nahi** gaya hai:
    summary["saved"] = False
    summary["storage"] = "job"

    repository.update_job_status(
        session,
        job,
        result_snapshot={
            "questions": questions,
            "summary": summary,
            "quality": quality,
            "coverage": coverage_rows,
        },
    )

    # Anti-repeat ledger (paper_id None ho sakta hai — stateless flow). Questions
    # ledger mein jaate hain taaki agla paper inhe repeat na kare.
    record_question_usage(
        session,
        paper_id=job.paper_id,
        class_name=getattr(paper, "class_name", "") or "",
        subject=getattr(paper, "subject", "") or "",
        questions=questions,
        created_by=None,
    )

    logger.info(
        "job %s (stateless): %s/%s questions | %s marks (budget %s) | repaired=%s",
        job.id,
        summary.get("question_count"),
        summary.get("expected_count"),
        summary.get("marks_total"),
        summary.get("ai_budget"),
        summary.get("repaired_count"),
    )

    return {
        "purpose": KIND_CONFIG,
        "result": summary,
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

    # Stateless job (paper_id None) → config se "paper jaisa" object banao.
    # AI layer **duck-typed** hai (`getattr(paper, "class_name", "")`), isliye
    # baaki poora pipeline — plan, prompts, batching, repair, judge — bilkul waise
    # hi chalta hai jaise DB row par chalta tha.
    if job.paper_id is None:
        paper: Any = llm_services.config_to_source(job.config_snapshot or {})
    else:
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
        elif kind == KIND_CONFIG:
            outcome = _run_config_generation(session, job, paper)
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


# ============================================================
# CONTENT LIBRARY + RAG (blueprint §1.2.1, §2.4) — File 21
# ============================================================
# Yahan teen kaam hote hain:
#   1. SOURCE ROW  — teacher ka source DB mein (status=pending)
#   2. INGEST      — extract → chunk → embed → Qdrant (background, per-source status)
#   3. (anti-repeat generation ke baad — neeche `record_question_usage` section)
#
# ⚠️ Layer rule wahi: `rag/*` files sirf content/vector ka kaam karti hain, aur
# DB/HTTP ka kaam yahan (service) hota hai.
# ============================================================

# Frontend ka "A".."G" code → DB ka SourceType enum
SOURCE_CODE_TO_TYPE: dict[str, SourceType] = {
    "A": SourceType.pdf,
    "B": SourceType.image,
    "C": SourceType.url,
    "D": SourceType.text,
    "E": SourceType.bank,
    "F": SourceType.image,  # camera photo
    "G": SourceType.bank,  # saved library entry (content pehle se ingested)
}


def _upload_dir() -> Path:
    """Upload folder (pehli upload par ban jaata hai)."""
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(filename: str, content: bytes) -> str:
    """Uploaded file ko disk par safe naam se likho → `storage_key` return.

    ⚠️ Security: user ka filename seedha use nahi karte (path traversal!).
    Basename lete hain + short content-hash prefix lagate hain, taaki same naam
    wali do files ek doosre ko overwrite na karein.
    """
    safe_name = Path(filename or "upload.bin").name
    digest = hashlib.sha1(content[:4096] + safe_name.encode("utf-8")).hexdigest()[:10]
    storage_key = f"{digest}_{safe_name}"
    (_upload_dir() / storage_key).write_bytes(content)
    return storage_key


def create_source(
    session: Session,
    payload: SourceCreate,
    created_by: int | None = None,
    storage_key: str | None = None,
) -> ExamSource:
    """Source row banao — ingest **background** mein chalegi.

    Sirf row banate hain kyunki PDF parse + embeddings minute le sakte hain
    (HTTP request ke andar karna galat hoga). Teacher ko UI par status dikhta hai:
    `pending → ingesting → ready` (ya `failed` + asli wajah).

    `storage_key` — upload wale flow mein file ka naam (PDF/image); text/URL
    sources ke liye None (unka content metadata/URL se aata hai).
    """
    code = str(payload.sourceType or "D").upper()[:1]
    meta: dict[str, Any] = {
        "source_code": code,
        "label": payload.label or payload.title,
        "url": payload.url,
        "pages": payload.pages,
        "library_entry_id": payload.libraryEntryId,
        "bank_ref": payload.bankRef,
    }
    if payload.textExcerpt:
        # Type-D (paste notes) ka text metadata mein hi rakh dete hain — ingest
        # isi ko extract karega (file ki zaroorat nahi).
        meta["text_excerpt"] = payload.textExcerpt

    data: dict[str, Any] = {
        "title": payload.title,
        "source_type": SOURCE_CODE_TO_TYPE.get(code, SourceType.text),
        "class_name": payload.class_name,
        "subject": payload.subject,
        "board": payload.board,
        "grade_class_id": payload.grade_class_id,
        "subject_id": payload.subject_id,
        "created_by": created_by,
        "chapters": list(payload.chapters or []),
        "tags": list(payload.tags or []),
        "teacher_name": payload.teacherName or "",
        "kind": payload.kind or "knowledge",
        "strictness": payload.strictness or "Strict",
        "storage_key": storage_key,
        "version": payload.version,
        "status": "pending",
        "metadata_json": meta,
    }
    source = repository.create_source(session, data)
    logger.info(
        "source created id=%s type=%s (%s) class=%s subject=%s chapters=%s",
        source.id,
        source.source_type,
        code,
        source.class_name,
        source.subject,
        source.chapters,
    )
    return source


def ingest_source_row(session: Session, source: ExamSource) -> dict[str, Any]:
    """Ek source row ko vector DB mein index karo (status updates ke saath).

    `status=ingesting` → extract + chunk + embed + upsert → `ready` ya `failed`.
    Fail hone par `error` column mein **asli wajah** jaati hai (teacher ko dikhe:
    "PDF mein text layer nahi hai" jaise cases).
    """
    from app.domains.exams.rag import ingest as rag_ingest

    meta = dict(source.metadata_json or {})
    source_payload: dict[str, Any] = {
        "sourceType": meta.get("source_code") or "",
        "label": meta.get("label") or source.title,
        "fileName": source.storage_key,
        "storageKey": source.storage_key,
        "url": meta.get("url"),
        "textExcerpt": meta.get("text_excerpt"),
        "chapters": list(source.chapters or []),
        "kind": source.kind,
    }

    result = rag_ingest.ingest_source(
        source_payload,
        school_id=None,  # single-school abhi → config ka tenant
        source_id=source.id,
        class_name=source.class_name,
        subject=source.subject,
        board=source.board,
        chapters=list(source.chapters or []),
        label=meta.get("label") or source.title,
    )

    warnings = list(result.get("warnings") or [])
    ok = bool(result.get("ok")) and not result.get("error")
    status = "ready" if ok else "failed"

    updates: dict[str, Any] = {
        "status": status,
        "chunk_count": int(result.get("chunks") or 0),
        "error": result.get("error"),
        "metadata_json": {**meta, "ingest": {**result, "warnings": warnings}},
    }
    if result.get("pages"):
        updates["page_count"] = int(result["pages"])

    updated = repository.update_source(session, source, updates)
    logger.info(
        "source ingest %s: id=%s chunks=%s pages=%s warnings=%s error=%s",
        status,
        source.id,
        updates["chunk_count"],
        result.get("pages"),
        len(warnings),
        updates["error"],
    )
    return {
        "source": updated,
        "status": status,
        "chunks": updates["chunk_count"],
        "pages": int(result.get("pages") or 0),
        "collection": result.get("collection"),
        "warnings": warnings,
        "error": updates["error"],
    }


def run_source_ingest_in_background(source_id: int) -> None:
    """FastAPI `BackgroundTasks` entry — **apna session** (generation jaisa hi rule).

    Request ka session response ke saath band ho jaata hai, isliye background
    task ko naya session kholna padta hai — warna `ResourceClosedError`.
    """
    try:
        with Session(engine) as session:
            source = repository.get_source_by_id(session, source_id)
            if source is None:
                logger.warning("ingest: source %s nahi mila", source_id)
                return
            repository.update_source(session, source, {"status": "ingesting"})
            ingest_source_row(session, source)
    except Exception:
        logger.exception("background ingest failed for source %s", source_id)


def list_sources(
    session: Session,
    *,
    created_by: int | None = None,
    class_name: str | None = None,
    subject: str | None = None,
) -> list[ExamSource]:
    """Content Library list (teacher scoped)."""
    return repository.list_sources(
        session, created_by=created_by, class_name=class_name, subject=subject
    )


def get_source(session: Session, source_id: int) -> ExamSource:
    """Source by id — nahi mila to 404."""
    source = repository.get_source_by_id(session, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )
    return source


def delete_source(session: Session, source_id: int) -> dict[str, Any]:
    """Source row + uske vector chunks dono hatao (orphan vectors na chhodo)."""
    from app.domains.exams.rag import ingest as rag_ingest

    source = get_source(session, source_id)
    logical_id = source.id
    removed = rag_ingest.remove_source(school_id=None, source_id=logical_id)
    repository.delete_source(session, source)
    logger.info("source %s deleted (vectors=%s)", logical_id, removed.get("ok"))
    return {"deleted": True, "vectorsRemoved": bool(removed.get("ok"))}


def source_read(source: ExamSource) -> SourceRead:
    """ExamSource row → API contract (`SourceRead`)."""
    meta = source.metadata_json or {}
    return SourceRead(
        id=source.id,
        title=source.title,
        sourceType=str(meta.get("source_code") or "D"),
        kind=source.kind,
        class_name=source.class_name,
        subject=source.subject,
        board=source.board,
        chapters=list(source.chapters or []),
        tags=list(source.tags or []),
        teacher_name=source.teacher_name,
        version=source.version,
        status=source.status,
        chunk_count=source.chunk_count,
        page_count=source.page_count,
        error=source.error,
        url=meta.get("url"),
        createdAt=source.created_at.isoformat() if source.created_at else None,
        updatedAt=source.updated_at.isoformat() if source.updated_at else None,
    )


# ------------------------------------------------------------
# ANTI-REPEAT — usage ledger (blueprint §1.2.1)
# ------------------------------------------------------------


def recent_used_texts(
    session: Session,
    *,
    class_name: str = "",
    subject: str = "",
) -> list[str]:
    """Pehle use ho chuke questions (prompt ke "avoid" block ke liye).

    Cross-paper repetition yahin rukti hai: aaj ke paper ko pichhle papers ke
    sawaal pata hone chahiye (`questionusagelog` table se).
    """
    try:
        return repository.recent_question_texts(
            session,
            class_name=class_name or None,
            subject=subject or None,
            limit=int(settings.ANTI_REPEAT_LOOKBACK),
        )
    except Exception as exc:  # ledger fail ho to generation na ruke
        logger.warning("anti-repeat lookback skip: %s", exc)
        return []


def record_question_usage(
    session: Session,
    *,
    paper_id: int | None,
    class_name: str = "",
    subject: str = "",
    questions: list[dict[str, Any]] | None = None,
    created_by: int | None = None,
) -> int:
    """Generated questions ko ledger mein likho (agli baar repeat na ho)."""
    from app.domains.exams.rag.usage import fingerprint

    rows: list[dict[str, Any]] = []
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        text = str(q.get("text") or "").strip()
        if not text:
            continue
        rows.append(
            {
                "fingerprint": fingerprint(text),
                "text": text,
                "paper_id": paper_id,
                "class_name": class_name or "",
                "subject": subject or "",
                "chapter": str(q.get("chapter") or ""),
                "topic": str(q.get("topic") or ""),
                "qtype": str(q.get("type") or ""),
                "marks": int(q.get("marks") or 0),
                "created_by": created_by,
            }
        )
    created = repository.record_question_usage(session, rows)
    logger.info("usage ledger: %s naye question record hue", created)
    return created
