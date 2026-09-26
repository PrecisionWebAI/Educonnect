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

from .models import (
    ExamSource,
    GenerationJob,
    GenerationJobStatus,
    PaperDraft,
    QuestionUsageLog,
)

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
    paper_id: int | None,
    blueprint_snapshot: dict[str, Any] | None = None,
    coverage_snapshot: dict[str, Any] | None = None,
    config_snapshot: dict[str, Any] | None = None,
    trace_id: str | None = None,
    graph_state: dict[str, Any] | None = None,
) -> GenerationJob:
    """Generate request aate hi job banao (status=queued).

    Snapshots: job start karne ke waqt ki paper config freeze.
    Baad mein draft badle to bhi job ko pata hai kis plan pe generate karna hai.

    `graph_state` (File 17) — job ka **kaam kya hai** woh yahan likha jaata hai:
        {"kind": "paper"}               → poora paper generate karo (draft se)
        {"kind": "config"}              → **stateless**: config_snapshot se generate,
                                          DB mein koi draft nahi banta
        {"kind": "question", "qid": "q3"} → sirf ek question dobara banao
    Alag table/column banane se behtar: same polling endpoint, same lifecycle,
    aur LangGraph ka checkpoint bhi isi column mein jayega.

    `paper_id=None` (nullable) = stateless job. Draft flow mein pehle jaisa hi
    paper_id aata hai, isliye purana behaviour bilkul nahi badalta.
    """
    job = GenerationJob(
        paper_id=paper_id,
        blueprint_snapshot=blueprint_snapshot or {},
        coverage_snapshot=coverage_snapshot or {},
        config_snapshot=config_snapshot or {},
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
    result_snapshot: dict[str, Any] | None = None,
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

    `result_snapshot` (stateless generate) — generated questions + summary.
    Draft flow mein ye khaali rehta hai (questions `paperdraft.part_a` mein).

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
    if result_snapshot is not None:
        job.result_snapshot = result_snapshot
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


# ------------------------------------------------------------
# CONTENT LIBRARY — ExamSource (blueprint §1.2.1)
# ------------------------------------------------------------


def create_source(session: Session, data: dict[str, Any]) -> ExamSource:
    """Naya source row (status=pending → ingest background mein chalti hai)."""
    source = ExamSource(**data)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def update_source(
    session: Session, source: ExamSource, data: dict[str, Any]
) -> ExamSource:
    """Source ke sirf diye hue fields badlo (partial update — `setattr` loop)."""
    for key, value in data.items():
        setattr(source, key, value)
    source.updated_at = datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def get_source_by_id(session: Session, source_id: int) -> ExamSource | None:
    """Primary key se source (None = nahi mila → service 404 banayegi)."""
    return session.get(ExamSource, source_id)


def find_source_by_hash(
    session: Session, content_hash: str, *, created_by: int | None = None
) -> ExamSource | None:
    """Same content wala source (dedup) — nahi mila to None.

    ⚠️ `created_by` bhi match karte hain: do teachers ki same NCERT PDF ek hi row
    nahi honi chahiye (warna ek teacher delete karega aur doosre ka source gayab).
    Isliye dedup **per teacher** hoti hai.

    Latest row chunte hain (`updated_at desc`) — re-upload se banaye gaye naye
    version ko prefer karne ke liye.
    """
    if not content_hash:
        return None
    stmt = (
        select(ExamSource)
        .where(ExamSource.content_hash == content_hash)
        .order_by(ExamSource.updated_at.desc())  # type: ignore[union-attr]
        .limit(1)
    )
    if created_by is not None:
        stmt = stmt.where(ExamSource.created_by == created_by)
    return session.exec(stmt).first()


def list_sources(
    session: Session,
    *,
    created_by: int | None = None,
    class_name: str | None = None,
    subject: str | None = None,
    limit: int = 50,
) -> list[ExamSource]:
    """Content Library list — filters optional (class/subject/teacher)."""
    stmt = select(ExamSource).order_by(ExamSource.updated_at.desc()).limit(limit)
    if created_by is not None:
        stmt = stmt.where(ExamSource.created_by == created_by)
    if class_name:
        stmt = stmt.where(ExamSource.class_name == class_name)
    if subject:
        stmt = stmt.where(ExamSource.subject == subject)
    return list(session.exec(stmt).all())


def delete_source(session: Session, source: ExamSource) -> None:
    """Source row delete (service pehle vector chunks hataata hai)."""
    session.delete(source)
    session.commit()


# ------------------------------------------------------------
# ANTI-REPEAT — QuestionUsageLog (blueprint §1.2.1 / §2.3.5)
# ------------------------------------------------------------


def record_question_usage(session: Session, rows: list[dict[str, Any]]) -> int:
    """Questions ko usage ledger mein likho ("ye question use ho chuka hai").

    Duplicate rows skip karte hain: same fingerprint ka record pehle se ho to
    dobara likhne ka koi faayda nahi (ledger "kab use hua" batata hai, "kitni
    baar dikha" nahi).
    """
    if not rows:
        return 0

    fingerprints = [
        str(r.get("fingerprint") or "") for r in rows if r.get("fingerprint")
    ]
    existing: set[str] = set()
    if fingerprints:
        stmt = select(QuestionUsageLog.fingerprint).where(
            QuestionUsageLog.fingerprint.in_(fingerprints)
        )
        existing = set(session.exec(stmt).all())

    created = 0
    for row in rows:
        fingerprint = str(row.get("fingerprint") or "")
        if not fingerprint or fingerprint in existing:
            continue
        session.add(QuestionUsageLog(**row))
        existing.add(fingerprint)
        created += 1

    if created:
        session.commit()
    return created


def recent_question_texts(
    session: Session,
    *,
    class_name: str | None = None,
    subject: str | None = None,
    limit: int = 60,
) -> list[str]:
    """Pehle use ho chuke question texts (naye se purane) — prompt ke "avoid" block ke liye.

    Yahi wo list hai jo `build_avoid_block()` ko jaati hai: "in sawaalon ko
    dobara mat likho". Isliye cross-paper repetition rukti hai (Unit Test 1 ke
    questions Half-Yearly mein wapas nahi aate).
    """
    stmt = (
        select(QuestionUsageLog).order_by(QuestionUsageLog.used_at.desc()).limit(limit)
    )
    if class_name:
        stmt = stmt.where(QuestionUsageLog.class_name == class_name)
    if subject:
        stmt = stmt.where(QuestionUsageLog.subject == subject)
    return [row.text for row in session.exec(stmt).all() if row.text]
