# ============================================================
# rag/ingest.py — source ka content → vector DB (blueprint §2.4, M2).
#
# ------------------------------------------------------------
# Poora pipeline ek jagah (aur iska "interface" hi asli contract hai)
# ------------------------------------------------------------
#     source (frontend SourceItem)
#        │  extract_source()   → pages (PDF pypdf, URL html-strip, text as-is)
#        ▼
#     chunks                 chunk_pages()  → ~800 char chunks + page number
#        │
#        ▼  embed_texts()     → vectors (dummy/ollama/hf — provider swappable)
#     Qdrant upsert          → payload ke saath (chapter/page/source_id)
#
# Iske baad generation ke waqt `retriever.py` yahin se **relevanT** chunks laata hai.
#
# ⚠️ Ye file DB ki row **nahi** banati (wo `exams/service.py` ka kaam hai — layer
# discipline). Yahan sirf "content → vectors" ka kaam hota hai.
# ============================================================

import logging
import uuid
from typing import Any

from app.core.config import settings
from app.domains.exams.rag import store
from app.domains.exams.rag.chunking import chunk_pages, tag_chapters
from app.domains.exams.rag.embeddings import embed_texts, embedding_dim
from app.domains.exams.rag.extract import SourceExtractionError, extract_source

logger = logging.getLogger("eduverse.exams.rag.ingest")

# Deterministic UUID namespace — point id banane ke liye (neeche explain kiya hai)
_POINT_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _chunk_uid(source_id: int | str, index: int) -> str:
    """Readable chunk id ("src12-c3") — payload mein jaata hai (debugging ke liye).

    Qdrant ko ye **id** ke roop mein nahi de sakte (wo uint/UUID maangta hai),
    isliye point id alag banate hain (`_point_id`).
    """
    return f"src{source_id}-c{index}"


def _point_id(chunk_uid: str) -> str:
    """Deterministic **UUID5** point id — Qdrant ka requirement + idempotency.

    ⚠️ Ye bug test ne pakda: Qdrant sirf unsigned integer ya UUID id leta hai
    ("src12-c3" reject ho jaata hai). UUID5 use karte hain (na random, na counter) —
    kyunki same chunk dobara ingest hone par **wahi id** banti hai, isliye
    duplicate points nahi bante, purana update ho jaata hai.
    """
    return str(uuid.uuid5(_POINT_NAMESPACE, chunk_uid))


def ingest_source(
    source: dict[str, Any],
    *,
    school_id: int | str | None = None,
    source_id: int | str | None = None,
    class_name: str = "",
    subject: str = "",
    board: str = "",
    chapters: list[str] | None = None,
    label: str | None = None,
    content_hash: str | None = None,
    subject_id: int | None = None,
    class_id: int | None = None,
) -> dict[str, Any]:
    """Ek source ko poora index karo. **Kabhi raise nahi karta** — result batata hai.

    Kyun raise nahi? Kyunki ingestion **background** chalti hai aur teacher ko
    per-source status chahiye ("ye PDF fail hui, baaki ho gayi"). Exception phenkne
    se poori list ka status gum ho jaata. Isliye return: `{ok, chunks, warnings, error}`.

    `content_hash` — source ke content ka sha256 (service se aata hai). Payload
    mein jaata hai, taaki "ye vector kis content se bana" ka jawab DB ke bahar bhi
    mil jaye (traceability) aur content-level dedup possible ho.
    """
    warnings: list[str] = []
    result: dict[str, Any] = {
        "ok": False,
        "kind": None,
        "chunks": 0,
        "pages": 0,
        "collection": None,
        "warnings": warnings,
        "error": None,
    }

    if not settings.RAG_ENABLED:
        warnings.append("RAG_ENABLED=false hai — ingest skip kiya")
        return result

    try:
        extraction = extract_source(source)
    except SourceExtractionError as exc:
        result["error"] = str(exc)
        logger.warning("ingest extract fail (source=%s): %s", source_id, exc)
        return result

    warnings.extend(extraction.get("warnings") or [])
    result["kind"] = extraction.get("kind")
    pages = extraction.get("pages") or []
    result["pages"] = len(pages)

    if not pages:
        warnings.append(
            "Is source se koi text nahi mila — retrieval mein kuch add nahi hua"
        )
        result["ok"] = True  # fail nahi (image/bank jaise sources ka normal case)
        return result

    chunks = chunk_pages(pages)
    if not chunks:
        result["ok"] = True
        warnings.append("Chunking se kuch nahi bana (text bahut chhota?)")
        return result

    tenant = store.tenant_id(school_id)
    try:
        collection = store.collection_name(tenant, "chunks")
        store.ensure_collection(collection, embedding_dim())
        # Filter fields (source_id / chapters / class_name…) par index — warna
        # retrieval poore collection ko scan karta hai (§2.4.2).
        store.ensure_payload_indexes(collection)
    except store.VectorStoreError as exc:
        result["error"] = str(exc)
        return result

    payloads = _build_payloads(
        chunks=chunks,
        source=source,
        source_id=source_id,
        tenant=tenant,
        class_name=class_name,
        subject=subject,
        board=board,
        chapters=chapters,
        label=label,
        kind=extraction.get("kind"),
        url=extraction.get("url"),
        content_hash=content_hash,
        subject_id=subject_id,
        class_id=class_id,
    )

    try:
        vectors = embed_texts([p["text"] for p in payloads])
        upserted = store.upsert_chunks(
            collection,
            vectors=vectors,
            payloads=payloads,
            # Qdrant ko UUID chahiye (readable chunk_uid payload mein rehta hai)
            ids=[_point_id(p["chunk_uid"]) for p in payloads],
        )
    except Exception as exc:  # embeddings + store dono ka saaf message
        result["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("ingest fail (source=%s): %s", source_id, result["error"])
        return result

    result["ok"] = True
    result["chunks"] = upserted
    result["collection"] = collection
    logger.info(
        "ingest ok: source=%s | kind=%s | pages=%s | chunks=%s | collection=%s",
        source_id,
        extraction.get("kind"),
        len(pages),
        upserted,
        collection,
    )
    return result


def _build_payloads(
    *,
    chunks: list[dict[str, Any]],
    source: dict[str, Any],
    source_id: int | str | None,
    tenant: int | str | None,
    class_name: str,
    subject: str,
    board: str,
    chapters: list[str] | None,
    label: str | None,
    kind: str | None,
    url: str | None,
    content_hash: str | None = None,
    subject_id: int | None = None,
    class_id: int | None = None,
) -> list[dict[str, Any]]:
    """Chunk → Qdrant payload (filter + traceability ke liye).

    Payload mein jaan-boojh kar **dono** cheezein hain:
      · FILTER fields (school_id, class_name, subject, chapters, **source_id**)
        → retrieval yahin se "sirf Class 8 Science, sirf Microorganisms, aur
        sirf ye chune hue sources" decide karta hai
      · DISPLAY fields (source_label, page, url) → prompt mein `[NCERT p.14]`
        likhne ke liye (blueprint §2.3.4 source traceability)
      · TRACEABILITY fields (`content_hash`, `chunk_hash`, `chunk_uid`) → har
        vector ka jawab: "ye kis source ka, kis chunk ka, kis content ka tha" —
        aur same content dobara index hone par pehchaan (dedup).

    ⚠️ `chunk_uid` + `_point_id()` (UUID5) ki wajah se same source dobara ingest
    hone par **duplicate points nahi bante** — purane update ho jaate hain.
    """
    from app.domains.exams.rag.hashing import chunk_hash

    source_label = label or source.get("label") or source.get("fileName") or "source"
    known_chapters = list(chapters or source.get("chapters") or [])
    payloads: list[dict[str, Any]] = []
    for chunk in chunks:
        # Chunk ke andar chapter ka naam mile to tag karo — isse "sirf Ch 2 se
        # question" wala filter PDF par bhi kaam karta hai (jahan metadata mein
        # chapter nahi hota, naam sirf page ke text mein hota hai).
        chunk_chapters = tag_chapters(chunk["text"], known_chapters) or known_chapters
        payloads.append(
            {
                "chunk_uid": _chunk_uid(source_id, chunk["chunk_index"]),
                "chunk_hash": chunk_hash(chunk["text"]),
                "content_hash": content_hash or source.get("contentHash"),
                "text": chunk["text"],
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
                "chars": chunk["chars"],
                "source_id": source_id,
                "source_label": source_label,
                "source_code": str(source.get("sourceType") or ""),
                "source_kind": kind,
                "url": url,
                "school_id": store.tenant_id(tenant),
                "class_name": class_name,
                "subject": subject,
                "board": board,
                "chapters": chunk_chapters,
                "usage": str(source.get("kind") or "knowledge"),
                # IDs (jab available hon) — blueprint §1.2.1 ka "chapter_id /
                # subject_id" metadata, taaki mapping endpoints aane par filter
                # IDs par bhi ho sake.
                "subject_id": subject_id,
                "classroom_id": class_id,
            }
        )
    return payloads


def remove_source(
    *, school_id: int | str | None = None, source_id: int | str | None = None
) -> dict[str, Any]:
    """Source ke chunks vector DB se hatao (delete/refresh ke waqt)."""
    try:
        collection = store.collection_name(school_id, "chunks")
        store.delete_by_source(collection, source_id)
        return {"ok": True, "collection": collection}
    except store.VectorStoreError as exc:
        logger.warning("source remove fail (source=%s): %s", source_id, exc)
        return {"ok": False, "error": str(exc)}


__all__ = ["ingest_source", "remove_source"]
