# ============================================================
# Exam/Paper repository — DB layer (blueprint §2.9).
#
# Policy (production):
#   · router → service → repository → DB
#   · Repository = SIRF SQL — koi business logic, koi HTTPException
#     nahi. "Mila nahi" → None return; service decide karegi (404).
#   · Har function ek hi kaam karta hai + docstring.
# ============================================================

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from .models import GenerationJob, GenerationJobStatus, PaperDraft

# ------------------------------------------------------------
# PAPER queries — upsert pattern (idempotency)
# ------------------------------------------------------------


def get_paper_by_id(session: Session, paper_id: int) -> PaperDraft | None:
    """Primary key se paper. None = nahi mila (service 404 banayega)."""
    return session.get(PaperDraft, paper_id)


def create_paper(
    session: Session,
    data: dict[str, Any],
    created_by: int | None = None,
) -> PaperDraft:
    """Naya PaperDraft create karke commit karo.

    `data` = validated schema ka `model_dump()` (service se aata hai).
    `session.add` → commit → refresh (id + defaults wapas aate hain).
    """
    paper = PaperDraft(**data, created_by=created_by)
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


def update_paper(
    session: Session,
    paper: PaperDraft,
    data: dict[str, Any],
) -> PaperDraft:
    """Existing paper ke sirf diye hue fields badlo (partial update).

    `setattr` loop = generic — naye columns aane par repository
    change nahi karni padti.
    """
    for key, value in data.items():
        setattr(paper, key, value)
    paper.updated_at = datetime.utcnow()
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


def upsert_paper(
    session: Session,
    data: dict[str, Any],
    paper_id: int | None,
    created_by: int | None = None,
) -> PaperDraft:
    """THE idempotency pattern: paper hai → update, nahi → create.

    Same request 2 baar aaye → 2 rows nahi banti (frontend refresh
    ho jaye to bhi data duplicate nahi hota). Production ka Rule.
    """
    if paper_id is not None:
        paper = get_paper_by_id(session, paper_id)
        if paper is not None:
            return update_paper(session, paper, data)
    return create_paper(session, data, created_by)


def list_papers(
    session: Session,
    created_by: int | None = None,
    limit: int = 50,
) -> list[PaperDraft]:
    """Recent papers — optional: sirf kisi teacher ke.

    `select(Table)` + `where` + `order_by` + `limit` = SQLAlchemy/SQLModel
    ka standard query pattern. `session.exec(stmt).all()` run karta hai.
    """
    stmt = select(PaperDraft).order_by(PaperDraft.updated_at.desc()).limit(limit)
    if created_by is not None:
        stmt = stmt.where(PaperDraft.created_by == created_by)
    return list(session.exec(stmt).all())


# ------------------------------------------------------------
# GENERATION JOB (async polling ka record)
# ------------------------------------------------------------


def create_generation_job(
    session: Session,
    paper_id: int,
    blueprint_snapshot: dict[str, Any] | None = None,
    coverage_snapshot: dict[str, Any] | None = None,
    trace_id: str | None = None,
    graph_state: dict[str, Any] | None = None,
) -> GenerationJob:
    """Generate request aate hi job banao (status=queued).

    Snapshots: job start karne ke waqt ki paper config freeze.
    Baad mein draft badle to bhi job ko pata hai kis plan pe generate karna hai.

    `graph_state` (File 17) — job ka **kaam kya hai** woh yahan likha jaata hai:
        {"kind": "paper"}              → poora paper generate karo (default)
        {"kind": "question", "qid": "q3"} → sirf ek question dobara banao
    Alag table/column banane se behtar: same polling endpoint, same lifecycle,
    aur Phase 3 mein LangGraph ka checkpoint bhi isi column mein jayega.
    """
    job = GenerationJob(
        paper_id=paper_id,
        blueprint_snapshot=blueprint_snapshot or {},
        coverage_snapshot=coverage_snapshot or {},
        trace_id=trace_id,
        graph_state=graph_state or {},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_generation_job(session: Session, job_id: int) -> GenerationJob | None:
    """Job id se job. None = nahi mila."""
    return session.get(GenerationJob, job_id)


def get_latest_job_by_paper(session: Session, paper_id: int) -> GenerationJob | None:
    """Paper ka sabse naya job — frontend polling isi ko dekhti hai.

    `order_by(created_at.desc()).limit(1)` = "sabse latest".
    """
    stmt = (
        select(GenerationJob)
        .where(GenerationJob.paper_id == paper_id)
        .order_by(GenerationJob.created_at.desc())
        .limit(1)
    )
    return session.exec(stmt).first()


def update_job_status(
    session: Session,
    job: GenerationJob,
    status: GenerationJobStatus | None = None,
    stage: str | None = None,
    error: str | None = None,
    graph_state: dict[str, Any] | None = None,
    extra_stages: dict[str, Any] | None = None,
    model_info: dict[str, Any] | None = None,
) -> GenerationJob:
    """Job ka progress update karo.

    `stage` = "retrieving" → "generating" → "validating" → "done"
    (`stages` dict mein current + history save hoti hai).
    `error` + `status=failed` = AI fail hone par frontend ko batana.

    `extra_stages` (File 17 mein add hua) — `stages` mein **merge** hone wale
    extra keys, jaise `{"pct": 40, "batch": "MCQ 1-8"}`. Ye isliye chahiye
    kyunki `stage` sirf `current` text set karta hai; frontend ko progress
    percentage aur batch label bhi chahiye (progress bar + "Writing MCQ 1-8...").

    `model_info` (File 17) — "kis paper ko kis model ne banaya" (blueprint
    §2.3.4 traceability). Job ke saath save hota hai, taaki 6 mahine baad bhi
    audit ho sake.

    ⚠️ JSONB note: hum **naya dict** banate hain aur assign karte hain (in-place
    mutate nahi) — warna SQLAlchemy change detect hi nahi karta (File 6 ka
    gotcha). Yahan `merged` fresh object hai, isliye UPDATE pakka chalti hai.
    """
    if status is not None:
        job.status = status
    if stage is not None or extra_stages:
        merged: dict[str, Any] = {**(job.stages or {})}
        if stage is not None:
            merged["current"] = stage
        if extra_stages:
            merged.update(extra_stages)
        job.stages = merged
    if error is not None:
        job.error = error
    if graph_state is not None:
        job.graph_state = graph_state
    if model_info is not None:
        job.model_info = model_info
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
