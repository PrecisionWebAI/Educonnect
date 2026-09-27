# ============================================================
# Exam/Paper router — HTTP endpoints (blueprint §2.9).
#
# The router is a THIN layer: HTTP + validation + permissions.
# Business logic lives in `service`, DB access in `repository`.
# main.py mounts it with prefix="/exams".
#
# ------------------------------------------------------------
# Slow AI work runs as a background job, never inside the request:
#   1. the client POSTs
#   2. a job record is created (status=queued) and returned immediately
#   3. the task is scheduled and runs after the response is sent
#   4. the client polls `GET .../job` for progress and the result
#
# A background task must open its own DB session: the request session is
# closed as soon as the response returns, and querying it raises
# `ResourceClosedError`. That is why `run_generation_in_background(job_id)`
# takes only the job id and opens `Session(engine)` itself.
#
# BackgroundTasks was chosen over ARQ for zero setup (no Redis/worker). The
# trade-off is that a server restart loses in-flight jobs; ARQ can later call
# the same `run_generation(session, job_id)` entry point.
# ============================================================

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import repository, service
from .schemas import (
    CustomQuestionCreate,
    FinalizeRequest,
    GenerationConfigRequest,
    GenerationRequest,
    JobRead,
    JobResultRead,
    MarksSuggestionRead,
    MarksSuggestionRequest,
    PaperDraftCreate,
    PaperDraftRead,
    PaperSavedRead,
    QuestionPatch,
    QuestionRegenerateRequest,
    QuestionRegenerateResult,
    QuestionTakeoverRequest,
    SourceCreate,
    SourceRead,
    SourceUploadRead,
)

router = APIRouter()


# ------------------------------------------------------------
# Content Library / sources (blueprint §2.9) — the RAG entry point
# ------------------------------------------------------------


@router.get("/sources", response_model=list[SourceRead])
def list_sources(
    class_name: str | None = None,
    subject: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Content Library list, scoped to the teacher and filtered by class/subject."""
    sources = service.list_sources(
        session,
        created_by=current_user.id,
        class_name=class_name,
        subject=subject,
    )
    return [service.source_read(s) for s in sources]


@router.post("/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Add a source (text/URL/bank/library); ingestion runs in the background.

    Parsing and embedding take seconds to minutes, so the request never waits.
    Poll `GET /exams/sources/{id}` for status:
    `pending -> ingesting -> ready | failed`.

    Re-sending identical content reuses the existing source (`content_hash`
    dedup): no new row and no re-embedding. The frontend should reuse the old
    `id` when the response reports `deduplicated=true`.
    """
    source, reused = service.upsert_source(session, payload, created_by=current_user.id)
    if not reused:
        background.add_task(service.run_source_ingest_in_background, source.id)
    return service.source_read(source, deduplicated=reused)


@router.post(
    "/sources/upload",
    response_model=SourceUploadRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    sourceType: str = Form("A"),
    class_name: str = Form(""),
    subject: str = Form(""),
    board: str = Form(""),
    chapters: str = Form(""),
    teacherName: str = Form(""),
    # Versioning (Phase 3.1): the older source this upload replaces. When set,
    # that source's chunks are deleted from the vector DB so stale content can
    # never be retrieved.
    replaceSourceId: str = Form(""),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Upload a file (PDF/image) -> save to disk -> ingest in the background.

    `chapters` arrives as a comma-separated string ("Microorganisms, Coal")
    because sending a list through a multipart form is awkward and the frontend
    already holds comma-joined text.

    The size limit comes from `UPLOAD_MAX_MB`, so oversized files are rejected
    before they ever reach the disk.

    `replaceSourceId` (optional) supports the re-upload/version flow by deleting
    the replaced source's vectors, so stale content cannot be retrieved.
    """
    content = await file.read()
    max_bytes = int(settings.UPLOAD_MAX_MB) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File is {len(content) // (1024 * 1024)}MB, "
                f"but the limit is {settings.UPLOAD_MAX_MB}MB"
            ),
        )

    # ---- Dedup: hash the file **bytes** ------------------------------------
    # Re-uploading the same PDF/image creates no new row and no re-embedding
    # (Phase 3.1). The hash must be taken here while the bytes are in hand;
    # only the disk path survives later.
    replaced_id = None
    if replaceSourceId not in (None, "", 0):
        try:
            replaced_id = int(replaceSourceId)
        except TypeError, ValueError:
            replaced_id = None

    storage_key = service.save_upload(file.filename or "upload.bin", content)
    chapter_list = [c.strip() for c in (chapters or "").split(",") if c.strip()]

    payload = SourceCreate(
        title=title or (file.filename or "Uploaded source"),
        sourceType=sourceType,
        label=title or (file.filename or "Uploaded source"),
        fileName=storage_key,
        class_name=class_name,
        subject=subject,
        board=board,
        chapters=chapter_list,
        teacherName=teacherName,
        replacesId=replaced_id,
    )
    source, reused = service.upsert_source(
        session,
        payload,
        created_by=current_user.id,
        storage_key=storage_key,
        file_bytes=content,
    )
    if not reused:
        background.add_task(service.run_source_ingest_in_background, source.id)
    return SourceUploadRead(
        sourceId=source.id,
        storageKey=storage_key,
        status=source.status,
        deduplicated=reused,
        message=(
            "This file was already indexed, so the existing source was reused "
            "(no re-embedding)"
            if reused
            else "Upload complete — ingestion is running in the background"
        ),
    )


@router.get("/sources/{source_id}", response_model=SourceRead)
def get_source(
    source_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Status of one source (ingest progress, chunk count, error)."""
    return service.source_read(service.get_source(session, source_id))


@router.post("/sources/{source_id}/ingest", response_model=SourceRead)
def reingest_source(
    source_id: int,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Re-run ingestion (after a failure, or because the embedding model changed).

    Changing the model also changes the collection dimension; in that case the
    error message tells the operator to delete the collection and re-ingest.
    """
    source = service.get_source(session, source_id)
    background.add_task(service.run_source_ingest_in_background, source.id)
    return service.source_read(source)


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.delete")),
):
    """Delete the source and its vector chunks."""
    return service.delete_source(session, source_id)


@router.get("/rag/status")
def rag_status(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """RAG diagnostics — mode (server/local), embedding provider, chunk count.

    A cheap production debugging endpoint that answers "why is RAG not working?"
    in about a second: is Qdrant down, is the collection empty, which provider
    is active?
    """
    from app.domains.exams.rag import store as rag_store
    from app.domains.exams.rag.embeddings import provider_info

    collection = rag_store.collection_name(None, "chunks")
    try:
        stats = rag_store.collection_stats(collection)
    except rag_store.VectorStoreError as exc:
        stats = {"exists": False, "points": 0, "error": str(exc)}

    return {
        "enabled": settings.RAG_ENABLED,
        "store": rag_store.store_info(),
        "embedding": provider_info(),
        "collection": collection,
        "collectionStats": stats,
    }


# ------------------------------------------------------------
# Papers CRUD
# ------------------------------------------------------------


@router.get("/papers", response_model=list[PaperDraftRead])
def list_papers(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """The teacher's own papers (most recent 50).

    `created_by` is scoped to `current_user.id`, so a teacher only sees their
    own papers — the first level of school isolation.
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
    """Save a draft (create or update — the repository upserts)."""
    paper = service.save_draft(session, paper_in, created_by=current_user.id)
    return PaperSavedRead(paperId=paper.id, status=paper.status)


@router.get("/papers/{paper_id}", response_model=PaperDraftRead)
def get_paper(
    paper_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """The full paper record (part_a / part_b / summary)."""
    return service.get_paper(session, paper_id)


@router.patch("/papers/{paper_id}", response_model=PaperSavedRead)
def update_paper(
    paper_id: int,
    paper_in: PaperDraftCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Update an existing draft (upsert — idempotent).

    Validation matches POST (Marks Contract + coverage cap), since both share
    the same `PaperConfigBase` schema.
    """
    paper = service.save_draft(
        session, paper_in, paper_id=paper_id, created_by=current_user.id
    )
    return PaperSavedRead(paperId=paper.id, status=paper.status)


# ------------------------------------------------------------
# Generation (Phase 3: job record; Phase 2: real AI generate)
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
    """Enqueue generation: returns 201 at once, the work runs in the background.

    Phase 2: send only `paper_id` — the plan is read from the paper record, so
    the Marks Contract is checked against the DB rather than the request.
    """
    job = service.enqueue_generation(session, generate_in.paper_id, generate_in)

    # Runs AFTER the response is sent (guaranteed by FastAPI), so the client
    # gets 201 immediately while the AI work continues separately.
    background.add_task(service.run_generation_in_background, job.id)
    return service.job_read(job)


@router.post(
    "/generate",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_from_config(
    config_in: GenerationConfigRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """**Stateless** generate — the full config is in the body, nothing is saved.

    How it works:
      1. The body carries the whole config (Basics + Source + Blueprint + Coverage + part_b)
      2. Server-side Marks Contract + coverage cap validation (422/409)
      3. A job is created with `paper_id=None` -> 201 at once, AI work in background
      4. `GET /exams/jobs/{job_id}` = progress,
         `GET /exams/jobs/{job_id}/result` = questions + quality + coverage report
      5. When the teacher saves -> `POST /exams/papers` (upsert), same payload

    Why a separate endpoint instead of POST /papers/generate? That route needs a
    paper record because it reads the plan from the DB. Here the plan arrives in
    the request, so the teacher's blueprint is never persisted.

    No `force` flag is needed: a stateless job belongs to no paper, so a
    duplicate-run conflict cannot occur.
    """
    job = service.enqueue_config_generation(session, config_in)
    background.add_task(service.run_generation_in_background, job.id)
    return service.job_read(job)


@router.get("/jobs/{job_id}/result", response_model=JobResultRead)
def get_job_result(
    job_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Stateless generate output — questions + summary + quality + coverage.

    In the draft flow the UI reads `part_a` from `GET /exams/papers/{id}`. There
    is no paper in the stateless flow, so this endpoint exposes the job's
    `result_snapshot` instead. While the job is `running` it returns an empty
    list plus the `status`.
    """
    return service.get_job_result(session, job_id)


@router.get("/papers/{paper_id}/job", response_model=JobRead)
def get_generation_job(
    paper_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Polling: the paper's latest generation job (what the frontend polls)."""
    return service.get_job_status(session, paper_id)


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job_by_id(
    job_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Polling: a **specific** job by id.

    `GET /papers/{id}/job` returns the *latest* job, but regenerating a question
    needs the status of the job just created; otherwise two parallel jobs become
    ambiguous. Hence this separate route.
    """
    job = repository.get_generation_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    return service.job_read(job)


# ------------------------------------------------------------
# Questions — the teacher's custom ones plus patch (lock/edit/regenerate)
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
    """Add the teacher's own question to part_b."""
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
    """Lock / edit / change marks (rebalance) / **regenerate** a question.

    `regenerate: true` has a side effect: the service creates a job and the real
    AI work runs in the background, since one question takes ~60-120s. The job id
    comes from `repository.get_latest_job_by_paper()`, because the service's
    primary return value is the paper and the latest job is the one it just made.
    """
    paper = service.patch_question(session, paper_id, qid, patch_in)

    if patch_in.regenerate:
        latest = repository.get_latest_job_by_paper(session, paper_id)
        if latest is not None:
            background.add_task(service.run_generation_in_background, latest.id)

    return paper


@router.post(
    "/papers/{paper_id}/questions/regenerate",
    response_model=QuestionRegenerateResult,
)
def regenerate_questions(
    paper_id: int,
    body: QuestionRegenerateRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Regenerate **only the questions you name** — one job for all of them.

    The teacher unlocks the questions they want changed, then regenerates them
    in one action. Nothing else in the paper moves, and because each job reuses
    the old question's slot (type / marks / chapter), the Marks Contract cannot
    break.

    The server keeps only the ids that exist in `part_a` **and are unlocked**.
    Anything else comes back in `skipped_locked` / `skipped_unknown`, so the UI
    can say "2 regenerated, 1 was still locked" instead of silently doing less
    than asked. 409 only if *none* of the ids can be regenerated.

    Slow AI work (60-120s per question) runs in the background: this returns the
    `job_id` immediately, and the client polls `GET /exams/jobs/{job_id}`.
    """
    job, queued, skipped_locked, skipped_unknown = service.enqueue_bulk_regeneration(
        session, paper_id, body.question_ids
    )
    background.add_task(service.run_generation_in_background, job.id)

    return QuestionRegenerateResult(
        job_id=job.id,
        queued=queued,
        skipped_locked=skipped_locked,
        skipped_unknown=skipped_unknown,
    )


@router.post("/papers/{paper_id}/questions/{qid}/takeover", response_model=PaperDraftRead)
def takeover_question(
    paper_id: int,
    qid: str,
    body: QuestionTakeoverRequest,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Replace an AI question with the teacher's own version ("Write my own").

    This is the second half of the review flow: once a question is **unlocked**,
    the teacher either asks the AI for a fresh version (the `regenerate` route
    above) or writes it themselves.

    Taking over moves the question from `part_a` to `part_b` and sets
    `origin="teacher"`, so from here on the UI renders it as a Custom question
    and the AI never touches it again. Marks are preserved from the original
    slot unless the teacher explicitly sends a `mark` — that keeps the paper's
    total (and therefore the Marks Contract) intact.

    404 if the question is unknown, 409 with `{code: "question_locked"}` if it
    is still locked.
    """
    return service.takeover_question(session, paper_id, qid, body)


@router.post(
    "/questions/recommend-marks",
    response_model=MarksSuggestionRead,
)
def recommend_marks(
    body: MarksSuggestionRequest,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """Suggested marks for a custom question, with the reasoning.

    Called when the frontend opens the "Add my question" form. Default is
    **rules only** (instant, free, deterministic); send `use_llm=true` for a
    second opinion from the judge model (slow, clamped to +/-1 mark).
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
    """Marks Contract passes -> status=approved. Fails -> 409."""
    note = body.note if body else None
    return service.finalize_paper(session, paper_id, note=note)
