# ============================================================
# Exam/Paper router — HTTP endpoints (blueprint §2.9).
#
# Router = PATLI layer: HTTP + validation + permissions.
# Logic service mein hai, DB repository mein — yahan sirf wiring.
#
# main.py isse prefix="/exams" ke saath mount karta hai,
# isliye endpoints /exams/papers*, /exams/questions/* lagenge.
# ============================================================

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import repository, service
from .schemas import (
    CustomQuestionCreate,
    FinalizeRequest,
    GenerationRequest,
    JobRead,
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
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Generation enqueue karo — job record status=queued."""
    return service.enqueue_generation(session, generate_in.paper_id, generate_in)


@router.get("/papers/{paper_id}/job", response_model=JobRead)
def get_generation_job(
    paper_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Polling: paper ka latest generation job (frontend isi ko poll karega)."""
    return service.get_job_status(session, paper_id)


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
    patch: QuestionPatch,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Question lock/edit/marks change (rebalance)."""
    return service.patch_question(session, paper_id, qid, patch)


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
