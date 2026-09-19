# ============================================================
# Exam/Paper router — HTTP endpoints (blueprint §2.9).
#
# Router = PATLI layer: HTTP + validation + permissions.
# Logic service mein hai, DB repository mein — yahan sirf wiring.
#
# main.py isse prefix="/exams" ke saath mount karta hai,
# isliye endpoints /exams/papers*, /exams/questions/* lagenge.
#
# ------------------------------------------------------------
# ⭐ File 18: BackgroundTasks — slow AI kaam ko request se ALAG karo
# ------------------------------------------------------------
# Aaj ka naap: 2 MCQ = 115s, 1 question regenerate ≈ 60-120s, poora paper
# ≈ 15-25 min. Isliye HTTP request mein generate karna namumkin hai.
#
# Pattern (production ka standard "async job + polling"):
#
#   1. client POST karta hai
#   2. hum **job record** banate hain (status=queued) → 201 TURANT return
#   3. background task ko schedule karte hain (response bhejne ke BAAD chalta hai)
#   4. client `GET .../job` se **poll** karta hai (progress + result)
#
# ️ BackgroundTasks ki asli shart: task ko **apna DB session** banana padta
#    hai. Request ka session response ke saath band ho jata hai (dependency ka
#    `finally`), aur band session se query = `ResourceClosedError`.
#    Isi liye service mein `run_generation_in_background(job_id)` hai —
#    woh sirf `job_id` leta hai aur khud `Session(engine)` kholta hai.
#
# Kyun BackgroundTasks (ARQ nahi, abhi)?
#   · zero setup — Redis/worker process ki zaroorat nahi
#   · kami: server restart pe job kho jata hai (Phase 3 mein ARQ isi runner ko
#     call karega — `run_generation(session, job_id)` wahi rahega, sirf caller
#     badlega. Isliye aaj ka code kal bekaar nahi jayega.)
# ============================================================

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import repository, service
from .schemas import (
    CustomQuestionCreate,
    FinalizeRequest,
    GenerationRequest,
    JobRead,
    MarksSuggestionRead,
    MarksSuggestionRequest,
    PaperDraftCreate,
    PaperDraftRead,
    PaperSavedRead,
    QuestionPatch,
)

router = APIRouter()


# ------------------------------------------------------------
# Papers CRUD
# ------------------------------------------------------------


@router.get("/papers", response_model=list[PaperDraftRead])
def list_papers(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Teacher ke apne papers (recent 50).

    `created_by` = current_user.id → resource scoping: teacher sirf
    apne papers dekhega (school isolation ka pehla level).
    """
    return repository.list_papers(session, created_by=current_user.id)


@router.post(
    "/papers",
    response_model=PaperSavedRead,
    status_code=status.HTTP_201_CREATED,
)
def create_or_update_paper(
    paper_in: PaperDraftCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Draft save (create/update — upsert repository kar raha hai)."""
    paper = service.save_draft(session, paper_in, created_by=current_user.id)
    return PaperSavedRead(paperId=paper.id, status=paper.status)


@router.get("/papers/{paper_id}", response_model=PaperDraftRead)
def get_paper(
    paper_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Ek paper ka full record (part_a/part_b/summary)."""
    return service.get_paper(session, paper_id)


# ------------------------------------------------------------
# Generation (Phase 3 tak: job record; Phase 2: asli AI generate)
# ------------------------------------------------------------


@router.post(
    "/papers/generate",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_paper(
    generate_in: GenerationRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Generation enqueue karo → 201 TURANT, kaam background mein.

    Phase 2: body mein sirf `paper_id` bhejo — plan server paper record se
    padhta hai (Marks Contract DB par check hota hai, request par nahi).

    ⚠️ Yahan `run_generation` **direct nahi** bulate — woh 15-25 min block karta.
    Hum sirf job record banate hain aur background task schedule karte hain.
    Response mein job ka `id` + `trace_id` jaata hai, jisse client poll kare.
    """
    job = service.enqueue_generation(session, generate_in.paper_id, generate_in)

    # Response bhejne ke BAAD chalta hai (FastAPI ka guarantee) — isliye client
    # turant 201 paata hai, aur AI kaam alag chalta rehta hai.
    background.add_task(service.run_generation_in_background, job.id)
    return service.job_read(job)


@router.get("/papers/{paper_id}/job", response_model=JobRead)
def get_generation_job(
    paper_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Polling: paper ka latest generation job (frontend isi ko poll karega)."""
    return service.get_job_status(session, paper_id)


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job_by_id(
    job_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Polling: **specific** job by id.

    `GET /papers/{id}/job` "latest" deta hai — par question regenerate karte waqt
    hamein **usi job ka** status chahiye (jo humne abhi banaya), warna do parallel
    jobs mein confusion ho jata hai ("kis job ka result dekh raha hoon?").
    Isliye ye alag route hai.
    """
    job = repository.get_generation_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    return service.job_read(job)


# ------------------------------------------------------------
# Questions — teacher ka custom + patch (lock/edit/regenerate)
# ------------------------------------------------------------


@router.post(
    "/questions/custom",
    response_model=PaperDraftRead,
    status_code=status.HTTP_201_CREATED,
)
def add_custom_question(
    body: CustomQuestionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Teacher ka khud ka question part_b mein jodo."""
    return service.add_custom_question(session, body.paper_id, body.question)


@router.patch("/papers/{paper_id}/questions/{qid}", response_model=PaperDraftRead)
def patch_question(
    paper_id: int,
    qid: str,
    patch_in: QuestionPatch,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Question lock / edit / marks change (rebalance) / **regenerate**.

    ⚠️ `regenerate: true` = **side effect** — service ek job banata hai (actual
    AI kaam background mein, kyunki ek question ≈ 60-120s leta hai). Job ka id
    service ne bana diya hota hai; usse chalane ka kaam yahan hota hai:

        patch_in.regenerate → background.add_task(run_generation_in_background, job.id)

    Job id `repository.get_latest_job_by_paper()` se nikaal rahe hain, kyunki
    service ka primary return value paper hai (purana contract nahi toda) —
    aur regenerate ke waqt latest job bas wahi hai jo service ne abhi banaya.
    """
    paper = service.patch_question(session, paper_id, qid, patch_in)

    if patch_in.regenerate:
        latest = repository.get_latest_job_by_paper(session, paper_id)
        if latest is not None:
            background.add_task(service.run_generation_in_background, latest.id)

    return paper


@router.post(
    "/questions/recommend-marks",
    response_model=MarksSuggestionRead,
)
def recommend_marks(
    body: MarksSuggestionRequest,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Custom question ke liye suggested marks (+ kyun).

    Frontend "Add my question" form kholte waqt ye bulata hai. Default **rules
    only** (instant, free, deterministic) — `use_llm=true` bhejo to judge model
    se second opinion bhi (slow, par ±1 marks ke andar clamp).
    """
    return service.suggest_question_marks(
        body.type, body.difficulty, body.text, use_llm=body.use_llm
    )


# ------------------------------------------------------------
# Finalize — hard gate
# ------------------------------------------------------------


@router.post("/papers/{paper_id}/finalize", response_model=PaperDraftRead)
def finalize_paper(
    paper_id: int,
    body: FinalizeRequest | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.publish")),
):
    """Marks Contract pass → status=approved. Fail → 409."""
    note = body.note if body else None
    return service.finalize_paper(session, paper_id, note=note)
