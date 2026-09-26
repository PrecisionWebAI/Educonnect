# ============================================================
# rag/retriever.py — "paper banane ke liye kaun sa content chahiye?" (blueprint §2.4).
#
# ------------------------------------------------------------
# ⭐ Yahi wo jagah hai jahan RAG asli fayda deta hai
# ------------------------------------------------------------
# Bina RAG: prompt mein poora chapter (ya kuch bhi nahi) jaata → model apni
#           "general knowledge" se likhta hai (syllabus se bahar ja sakta hai).
# RAG ke saath: hum **poochh** banate hain (class + subject + chapter + topic),
#           Qdrant se sirf wahi chunks laate hain jo is chapter ke hain, aur
#           prompt ka `<source>` block ban jaata hai — page number ke saath.
#
# 📌 Interface wahi rakha gaya hai jo pehle tha: `(sources, excerpts)`. Isliye
#    `prompts.py` aur `generator.py` mein ek line bhi nahi badli — "interface
#    pehle, implementation baad" ka promise aaj poora hua.
#
# ⚠️ Failure policy: RAG fail ho (Qdrant band, embeddings down) to generation
# **rukni nahi chahiye** — sirf warning ke saath purane behaviour (paste-text) par
# chale jaana chahiye. AI ka kaam best-effort hota hai, hard dependency nahi.
# ============================================================

import logging
from typing import Any

from app.core.config import settings
from app.domains.exams.rag import store
from app.domains.exams.rag.embeddings import embed_texts

logger = logging.getLogger("eduverse.exams.rag.retriever")


def _plan_chapters(plan: dict[str, Any] | None) -> list[str]:
    """Coverage plan aur slot plan se chapters (order preserve, dupe-free).

    Coverage plan pehle kyun? Kyunki wahi teacher ka **final intent** hai
    ("Ch 2 ke 5 marks"). `paper.chapters` basic list hai; coverage zyada specific.
    """
    out: list[str] = []
    coverage = (plan or {}).get("coverage") or {}
    for c in coverage.get("chapters") or []:
        name = str(c.get("chapter") or "").strip()
        if name and name not in out:
            out.append(name)
    if out:
        return out
    for slot in (plan or {}).get("slots") or []:
        name = str(slot.get("chapter") or "").strip()
        if name and name not in out:
            out.append(name)
    return out


def _paper_chapters(paper: Any, plan: dict[str, Any] | None = None) -> list[str]:
    """Chapters: plan se, warna `paper.chapters` se (empty-safe)."""
    from_plan = _plan_chapters(plan)
    if from_plan:
        return from_plan
    return [
        str(c).strip()
        for c in (getattr(paper, "chapters", None) or [])
        if str(c).strip()
    ]


def build_queries(paper: Any, plan: dict[str, Any] | None = None) -> list[str]:
    """Paper ke context se search queries banao (chapter-wise).

    Ek query **per chapter** — kyunki ek hi badi query se sirf ek chapter ka
    content aata hai aur baaki chapters gayab ho jaate hain (retrieval laalach).
    Per-chapter query se coverage natural ho jaati hai.
    """
    class_name = getattr(paper, "class_name", "") or ""
    subject = getattr(paper, "subject", "") or ""
    exam_type = getattr(paper, "exam_type", "") or ""
    chapters = _paper_chapters(paper, plan)

    base = " ".join(
        x for x in (f"class {class_name}" if class_name else "", subject) if x
    )
    if not chapters:
        return [f"{base} {exam_type} important concepts definitions".strip()]

    queries: list[str] = []
    for chapter in chapters:
        topics = _topics_for(plan, chapter)
        topic_bit = f" {' '.join(topics)}" if topics else ""
        queries.append(
            f"{base} {chapter}{topic_bit} key concepts definitions examples".strip()
        )
    return queries


def _topics_for(plan: dict[str, Any] | None, chapter: str) -> list[str]:
    """Us chapter ke topics (coverage plan se) — query ko sharp karne ke liye."""
    for c in ((plan or {}).get("coverage") or {}).get("chapters", []):
        if str(c.get("chapter")) == chapter:
            return [
                str(t.get("topic")) for t in (c.get("topics") or []) if t.get("topic")
            ]
    return []


def _search_safe(
    collection: str,
    *,
    vector: list[float],
    filters: dict[str, Any],
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Search with error tolerance — RAG ki wajah se poori job fail nahi honi chahiye."""
    try:
        return store.search(collection, vector=vector, filters=filters, limit=limit)
    except store.VectorStoreError as exc:
        warnings.append(f"Retrieval fail: {exc}")
        return []


def _selected_source_ids(paper: Any) -> list[int]:
    """Paper ke chune hue sources ke **backend ids** (jo ints bane).

    Frontend `SourceStep` har source ko backend par save karta hai aur uski
    `sourceId` (ExamSource.id) item ke saath rakhta hai. Qdrant payload mein
    wahi `source_id` hai — isliye hum retrieval ko **sirf un hi sources** par
    filter kar sakte hain ("teacher ne jo select kiya, wahi padho").

    ⚠️ Purane/offline sources ki id `"src-res123"` jaisi string hoti hai → int
    nahi banti, isliye chup-chaap skip ho jaati hai (us case mein metadata
    filter wala purana behaviour chalta rehta hai).
    """
    ids: list[int] = []
    for raw in getattr(paper, "sources", None) or []:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("kind") or "knowledge").lower() == "pattern":
            continue  # "pattern only" sources ka content retrieve nahi karna
        for key in ("sourceId", "source_id", "sourceIds", "libraryEntryId"):
            value = raw.get(key)
            if value in (None, ""):
                continue
            # Multi-file upload = ek item, kai source ids (`sourceIds` list).
            candidates = value if isinstance(value, (list, tuple, set)) else [value]
            for candidate in candidates:
                try:
                    sid = int(candidate)
                except TypeError, ValueError:
                    continue
                if sid not in ids:
                    ids.append(sid)
    return ids


def _filter_attempts(
    base_filters: dict[str, Any],
    *,
    chapter: str,
    selected_ids: list[int],
) -> list[tuple[dict[str, Any], str | None]]:
    """Filter attempts **precision → recall** ke kram mein.

    Kyun kram zaroori hai: strictest filter (source + chapter) khaali aa sakta
    hai — jaise chapter tag us chunk par na laga ho. Tab hum ek-ek layer dheela
    karte hain aur **warning** likh dete hain, taaki teacher ko pata chale ki
    result kis filter se aaya (chup-chaap galat context nahi).
    """
    attempts: list[tuple[dict[str, Any], str | None]] = []
    if selected_ids:
        if chapter:
            attempts.append(
                (
                    {**base_filters, "source_id": selected_ids, "chapters": [chapter]},
                    None,
                )
            )
            attempts.append(
                (
                    {**base_filters, "source_id": selected_ids},
                    "Chapter filter se kuch nahi mila (in sources mein) — "
                    "chapter filter hata kar dekha",
                )
            )
        else:
            attempts.append(({**base_filters, "source_id": selected_ids}, None))
    if chapter:
        attempts.append(
            (
                {**base_filters, "chapters": [chapter]},
                "Selected sources se kuch nahi mila (indexing pending/fail?) — "
                "baaki library content se fallback kiya",
            )
        )
    attempts.append(
        (
            base_filters,
            "Chapter filter se kuch nahi mila — poore class/subject par search kiya",
        )
    )
    return attempts


def context_pack(
    paper: Any,
    *,
    plan: dict[str, Any] | None = None,
    school_id: int | str | None = None,
) -> dict[str, Any]:
    """Retrieval → prompt-ready context: `{sources, excerpts, hits, used_rag, warnings}`.

    `excerpts` ki shape wahi hai jo `build_source_block()` expect karta hai:
        "[NCERT Science · p.14] <chunk text>"
    Isliye prompt mein label + page number apne aap dikhte hain (traceability §2.3.4).
    """
    warnings: list[str] = []
    empty: dict[str, Any] = {
        "sources": [],
        "excerpts": [],
        "hits": [],
        "used_rag": False,
        "warnings": warnings,
    }

    if not settings.RAG_ENABLED:
        warnings.append("RAG_ENABLED=false — retrieval skip kiya")
        return empty

    queries = build_queries(paper, plan)
    if not queries:
        warnings.append("Koi chapter/query nahi — retrieval skip kiya")
        return empty

    tenant = store.tenant_id(school_id)
    collection = store.collection_name(tenant, "chunks")
    try:
        if not store.collection_stats(collection).get("exists"):
            warnings.append(
                f"Vector collection '{collection}' nahi mili — pehle sources ingest "
                "karo (POST /exams/sources ya /exams/sources/upload)"
            )
            return empty
    except store.VectorStoreError as exc:
        warnings.append(f"Vector store unavailable: {exc}")
        return empty

    try:
        vectors = embed_texts(queries)
    except Exception as exc:  # embeddings provider down
        warnings.append(f"Embeddings fail: {type(exc).__name__}: {exc}")
        return empty

    base_filters: dict[str, Any] = {"school_id": tenant}
    class_name = getattr(paper, "class_name", "") or ""
    subject = getattr(paper, "subject", "") or ""
    if class_name:
        base_filters["class_name"] = class_name
    if subject:
        base_filters["subject"] = subject

    # ---- selected sources (frontend ne jo bheje) ----
    # Yehi "sirf ye chapter/notes padho" wala contract hai: agar teacher ne
    # sources chune hain to retrieval unhi par filter hoti hai (blueprint
    # §1.2.1 G: library se select kiya hua content).
    selected_ids = _selected_source_ids(paper)
    if selected_ids:
        logger.info("retrieval filtered to %s selected source_id(s)", len(selected_ids))

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_query_limit = max(2, settings.RETRIEVAL_TOP_K // max(1, len(queries)))
    chapters = _paper_chapters(paper, plan) or [""] * len(queries)

    for query, vector, chapter in zip(queries, vectors, chapters, strict=False):
        found: list[dict[str, Any]] = []
        # Strictest se shuru (source + chapter) → phir recall badhate hain.
        for filters, warning in _filter_attempts(
            base_filters, chapter=chapter, selected_ids=selected_ids
        ):
            found = _search_safe(
                collection,
                vector=vector,
                filters=filters,
                limit=per_query_limit,
                warnings=warnings,
            )
            if found:
                if warning:
                    warnings.append(f"'{chapter or '-'}': {warning}")
                break

        for hit in found:
            uid = str((hit.get("payload") or {}).get("chunk_uid") or "")
            if uid and uid in seen:
                continue
            if uid:
                seen.add(uid)
            hit["query"] = query
            hit["chapter"] = chapter
            hits.append(hit)

    hits.sort(key=lambda h: h.get("score") or 0.0, reverse=True)
    hits = hits[: settings.RETRIEVAL_TOP_K]

    sources: list[dict[str, Any]] = []
    excerpts: list[str] = []
    for hit in hits:
        payload = hit.get("payload") or {}
        label = str(payload.get("source_label") or "source")
        page = payload.get("page")
        page_bit = f" · p.{page}" if page else ""
        hit_chapters = payload.get("chapters") or []
        chapter_bit = (
            f" [{'/'.join(str(c) for c in hit_chapters)}]" if hit_chapters else ""
        )
        body = " ".join(str(payload.get("text") or "").split())
        excerpts.append(f"[{label}{page_bit}{chapter_bit}] {body[:600]}")
        sources.append(
            {
                "id": payload.get("source_id"),
                "label": label,
                "sourceType": payload.get("source_code") or "RAG",
                "chapters": hit_chapters,
                "pages": str(page) if page else "",
                "kind": payload.get("usage") or "knowledge",
                "url": payload.get("url"),
                "sourceRef": f"{label}#p{page}" if page else label,
                "score": round(float(hit.get("score") or 0.0), 4),
                # ---- traceability (blueprint §2.3.4 / §2.4) ----
                # Har excerpt ka jawab: kis source_id, kis chunk, kis content
                # hash se aaya (audit + "ye question kis source se bana" ke liye).
                "sourceId": payload.get("source_id"),
                "chunkUid": payload.get("chunk_uid"),
                "contentHash": payload.get("content_hash"),
            }
        )

    logger.info(
        "retrieval: %s queries → %s hits (collection=%s, sources=%s)",
        len(queries),
        len(hits),
        collection,
        len(selected_ids) if selected_ids else "all",
    )
    return {
        "sources": sources,
        "excerpts": excerpts,
        "hits": hits,
        "used_rag": bool(hits),
        "warnings": warnings,
        # Diagnostics: kitne selected sources par filter laga tha (UI/summary
        # mein dikhata hai — "0 hits kyun aaye" ka jawab).
        "selected_source_ids": selected_ids,
    }
