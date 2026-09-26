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
    SourceCreate,
    SourceRead,
    SourceUploadRead,
)

router = APIRouter()


# ------------------------------------------------------------
# Content Library / sources (blueprint §2.9) — RAG ka entry point
# ------------------------------------------------------------


@router.get("/sources", response_model=list[SourceRead])
def list_sources(
    class_name: str | None = None,
    subject: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Content Library list (teacher scoped; class/subject se filter).

    ⚠️ Ye route **missing thi** jabki frontend `getContentLibrary()` ise call
    karta tha → 404 → library hamesha khaali dikhti thi.
    """
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
    """Source add karo (text/URL/bank/library) → ingest background mein.

    Ingest hamesha **background** kyun? PDF parse + embeddings seconds se minute
    tak le sakte hain; HTTP request ko us waqt tak rokna bura UX (aur proxy
    timeout) hai. Status `GET /exams/sources/{id}` se poll karo:
    `pending → ingesting → ready | failed`.

    ⭐ Same content dobara bheja gaya to **wahi source reuse** hota hai
    (`content_hash` dedup) — naya row nahi banta aur embeddings dobara nahi
    bantee. Response mein `deduplicated=true` dekh kar frontend purana `id`
    use kare.
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
    # Versioning (Phase 3.1): is upload ne kis purane source ko replace kiya.
    # Diya gaya to purane source ke chunks vector DB se delete ho jaate hain,
    # taaki stale content retrieval mein na aaye.
    replaceSourceId: str = Form(""),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.create")),
):
    """File upload (PDF/image) → disk par save → ingest background mein.

    `chapters` comma-separated string leta hai ("Microorganisms, Coal") — kyunki
    multipart form mein list bhejna awkward hota hai aur frontend ke paas already
    comma-joined text hota hai.

    Size limit `UPLOAD_MAX_MB` se aata hai — bade files ko **pehle hi** rok dete
    hain (warna disk aur ingest dono par bekaar pressure).

    `replaceSourceId` (optional) — re-upload/version flow: purane source ke
    vectors delete hote hain (warna purana, galat content retrieve ho sakta tha).
    """
    content = await file.read()
    max_bytes = int(settings.UPLOAD_MAX_MB) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File {len(content) // (1024 * 1024)}MB hai — "
                f"limit {settings.UPLOAD_MAX_MB}MB"
            ),
        )

    # ---- Dedup: file ke **bytes** ka hash ----------------------------------
    # Isse same PDF/image dobara upload hone par naya row + dobara embedding
    # nahi hoti (Phase 3.1). Hash yahin (bytes ke saath) nikalna zaroori hai —
    # baad mein sirf disk path bachta hai, bytes nahi.
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
            "Ye file pehle se indexed hai — wahi source use kiya gaya (dobara "
            "embed nahi kiya)"
            if reused
            else "Upload ho gaya — ingestion background mein chal rahi hai"
        ),
    )


@router.get("/sources/{source_id}", response_model=SourceRead)
def get_source(
    source_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """Ek source ka status (ingest progress + chunk count + error)."""
    return service.source_read(service.get_source(session, source_id))


@router.post("/sources/{source_id}/ingest", response_model=SourceRead)
def reingest_source(
    source_id: int,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Dobara ingest (source fail hua tha, ya embedding model badla).

    ⚠️ Model badla ho to collection ka dimension bhi badal jaata hai — us case
    mein error message hi guide karta hai ki collection delete karke re-ingest
    karna hai (warna dim mismatch).
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
    """Source + uske vector chunks hatao."""
    return service.delete_source(session, source_id)


@router.get("/rag/status")
def rag_status(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.read")),
):
    """RAG diagnostics — mode (server/local), embedding provider, chunk count.

    Production debugging ke liye sasta endpoint: "RAG kaam kyun nahi kar raha?"
    ka jawab 1 second mein — Qdrant down? collection khaali? provider kaun sa?
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


@router.patch("/papers/{paper_id}", response_model=PaperSavedRead)
def update_paper(
    paper_id: int,
    paper_in: PaperDraftCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("exams.update")),
):
    """Existing draft update (upsert — idempotent).

    ⚠️ Ye route **missing thi** aur frontend `api.patch("/exams/papers/{id}")`
    call karta hai (har dobara save par) → 405 Method Not Allowed. Isliye
    "Step 1 → 2 → 3 → wapas Step 1 → Save" karne par draft save hi fail hota tha.
    Validation wahi hai jo POST par lagti hai (Marks Contract + coverage cap),
    kyunki dono ek hi base schema (`PaperConfigBase`) se aate hain.
    """
    paper = service.save_draft(
        session, paper_in, paper_id=paper_id, created_by=current_user.id
    )
    return PaperSavedRead(paperId=paper.id, status=paper.status)


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
    """**Stateless** generate — poora config body mein, blueprint DB mein save NAHI.

    Kaam kaise karta hai:
      1. Body mein poora config (Basics + Source + Blueprint + Coverage + part_b)
      2. Server-side Marks Contract + coverage cap validation (422/409)
      3. Job banta hai (`paper_id=None`) → 201 turant, AI kaam background mein
      4. `GET /exams/jobs/{job_id}` = progress, `GET /exams/jobs/{job_id}/result`
         = questions + quality + coverage report
      5. Jab teacher bole "save karo" → `POST /exams/papers` (upsert) — wahi payload

    Kyun alag endpoint (POST /papers/generate ke bajaye)? Kyunki wahan paper record
    hona zaroori hai (plan DB se padhta hai). Yahan plan **request se** aata hai,
    isliye teacher ka blueprint kabhi database mein nahi jaata.

    `force` jaisa flag yahan nahi chahiye: stateless job kisi paper se juda nahi,
    isliye duplicate-run ka conflict khud-ba-khud nahi banta.
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
    """Stateless generate ka output — questions + summary + quality + coverage.

    Draft flow mein UI `GET /exams/papers/{id}` se `part_a` padhta hai; stateless
    flow mein paper hi nahi hai, isliye ye endpoint job ke `result_snapshot` ko
    kholta hai. (Job abhi `running` ho to khaali list + `status` aata hai.)
    """
    return service.get_job_result(session, job_id)


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
