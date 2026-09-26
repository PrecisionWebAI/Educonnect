# ============================================================
# rag/store.py — Qdrant (vector DB) ka patla wrapper (blueprint §2.4).
#
# ------------------------------------------------------------
# ⭐ Ek hi client, do mode — aur yahi production mein azaad karta hai
# ------------------------------------------------------------
#   QDRANT_URL set   → **server mode** (production: docker/service Qdrant)
#   QDRANT_URL khaali → **local persistent mode** (`QdrantClient(path=...)`)
#
# Dono mein API **bilkul same** hai (create_collection / upsert / query_points).
# Isliye:
#   · aaj developer ko kuch setup nahi karna padta (bina internet bhi chalta hai)
#   · aur production mein sirf `.env` badalna hai — code nahi
# Yahi "config badlo, code nahi" wala rule hai jo is project mein har layer mein
# dikhta hai (LLM provider, embeddings provider, ab vector store).
#
# ------------------------------------------------------------
# Collection naming — multi-tenant isolation
# ------------------------------------------------------------
#   edu_school_{school_id}_chunks     → source text chunks (retrieval)
#   edu_school_{school_id}_questions  → question fingerprints (anti-repeat)
#   edu_school_{school_id}_images     → image captions (M4, blueprint §2.6)
# Ek school ka data doosre school ke search mein **kabhi** nahi aata — collection
# alag hone se ye DB-level par guaranteed hai (application filter par bharosa
# nahi karna padta).
# ============================================================

import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.rag.store")

COLLECTION_KINDS = ("chunks", "questions", "images")


class VectorStoreError(RuntimeError):
    """Qdrant se baat nahi ho payi — caller ko saaf message dena chahiye."""


def store_info() -> dict[str, Any]:
    """Kaunsa mode chal raha hai (job/model_info + debug ke liye)."""
    url = (settings.QDRANT_URL or "").strip()
    return {
        "mode": "server" if url else "local",
        "url": url or None,
        "path": None if url else settings.QDRANT_LOCAL_PATH,
        "prefix": settings.VECTOR_COLLECTION_PREFIX,
    }


def tenant_id(school_id: int | str | None = None) -> str:
    """Tenant (school) id — teacher ka data alag rakhne ka key.

    Abhi single-school hai (`VECTOR_TENANT` config), par **interface ab se hi
    tenant-aware** hai: JWT se school id aane lage to bas yahan pass kar dena.
    """
    if school_id not in (None, "", 0):
        return str(school_id)
    return str(settings.VECTOR_TENANT or "default")


def collection_name(school_id: int | str | None, kind: str = "chunks") -> str:
    """Tenant-safe collection name. Unknown school → config ka default bucket."""
    if kind not in COLLECTION_KINDS:
        raise VectorStoreError(f"Unknown collection kind '{kind}' ({COLLECTION_KINDS})")
    return f"{settings.VECTOR_COLLECTION_PREFIX}{tenant_id(school_id)}_{kind}"


@lru_cache(maxsize=1)
def get_client():
    """Qdrant client (cached — connection reuse, warna har call pe naya).

    ⚠️ `local` mode single-process hota hai. Isliye production mein (multi-worker:
    uvicorn/gunicorn + ARQ worker) **QDRANT_URL set karna zaroori hai** — warna
    har worker ka apna alag store ban jayega. Ye ek asli production trap hai.
    """
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:  # pragma: no cover - dependency pyproject mein hai
        raise VectorStoreError(
            "qdrant-client install nahi hai — `uv add qdrant-client` chalao"
        ) from exc

    url = (settings.QDRANT_URL or "").strip()
    if url:
        logger.info("Qdrant server mode: %s", url)
        return QdrantClient(
            url=url, api_key=settings.QDRANT_API_KEY or None, timeout=30
        )

    logger.warning(
        "QDRANT_URL set nahi hai → Qdrant **local** mode (path=%s). Ye dev/test ke "
        "liye hai; production mein QDRANT_URL do (warna har worker ka apna store).",
        settings.QDRANT_LOCAL_PATH,
    )
    return QdrantClient(path=settings.QDRANT_LOCAL_PATH)


def ensure_collection(name: str, dim: int) -> None:
    """Collection banane ki guarantee (idempotent) + vector size check.

    Dimension mismatch par **saaf error** dena zaroori hai: ye tab hota hai jab
    embedding model badla (384 → 768) par purana collection pada hai. Warna Qdrant
    baad mein confusing error dega (upsert ke waqt).
    """
    from qdrant_client import models

    client = get_client()
    try:
        existing = client.collection_exists(name)
    except Exception as exc:
        raise VectorStoreError(f"Qdrant se connection fail: {exc}") from exc

    if not existing:
        client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=int(dim), distance=models.Distance.COSINE
            ),
        )
        logger.info("collection banaya: %s (dim=%s)", name, dim)
        return

    try:
        info = client.get_collection(name)
        size = info.config.params.vectors.size  # type: ignore[union-attr]
    except Exception as exc:  # pragma: no cover
        raise VectorStoreError(f"collection info fail ({name}): {exc}") from exc

    if int(size) != int(dim):
        raise VectorStoreError(
            f"Collection '{name}' ka vector size {size} hai, par embedding model "
            f"{dim} deta hai. Do options: (a) EMBEDDING_DIMENSIONS/MODEL wapas "
            f"pehle jaisa karo, ya (b) collection delete karke dobara ingest karo "
            f"(re-embed zaroori hai)."
        )


def _build_filter(filters: dict[str, Any] | None):
    """Simple dict → Qdrant Filter (`must` conditions).

    Support: scalar (exact match) aur list (kisi ek se match = OR).
    Isse hum chapter/topic/class/subject/source par filter kar sakte hain —
    yahi RAG ko "sirf isi chapter se" banane ka tareeka hai (blueprint §1.3).
    """
    from qdrant_client import models

    if not filters:
        return None

    conditions = []
    for key, value in filters.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (list, tuple, set)):
            values = [v for v in value if v not in (None, "")]
            if not values:
                continue
            conditions.append(
                models.FieldCondition(key=key, match=models.MatchAny(any=list(values)))
            )
        else:
            conditions.append(
                models.FieldCondition(key=key, match=models.MatchValue(value=value))
            )

    return models.Filter(must=conditions) if conditions else None


def upsert_chunks(
    name: str,
    *,
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
    ids: list[str] | None = None,
) -> int:
    """Vectors + payload Qdrant mein likho (idempotent — same id = update).

    Idempotency ka faayda: same source dobara ingest ho (teacher ne dobara save
    kiya) to duplicate points nahi bante — purane points update ho jaate hain.
    """
    from qdrant_client import models

    if not vectors:
        return 0
    if len(vectors) != len(payloads):
        raise VectorStoreError(
            f"vectors ({len(vectors)}) aur payloads ({len(payloads)}) barabar nahi"
        )

    client = get_client()
    point_ids: list[Any] = ids or [
        p.get("chunk_uid") or i for i, p in enumerate(payloads)
    ]
    points = [
        models.PointStruct(id=pid, vector=vector, payload=payload)
        for pid, vector, payload in zip(point_ids, vectors, payloads, strict=False)
    ]
    try:
        client.upsert(collection_name=name, points=points, wait=True)
    except Exception as exc:
        raise VectorStoreError(f"Qdrant upsert fail ({name}): {exc}") from exc
    return len(points)


def search(
    name: str,
    *,
    vector: list[float],
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """Similarity search → `[{score, payload}]` (score ke hisaab se sorted).

    `query_points` (naya API) use karte hain, purana `search()` deprecated hai —
    production mein deprecation warnings se bachna aur naye features (hybrid,
    group-by) ke liye tayyar rehna.
    """
    client = get_client()
    top_k = int(limit or settings.RETRIEVAL_TOP_K)
    threshold = settings.RETRIEVAL_MIN_SCORE if min_score is None else min_score

    try:
        response = client.query_points(
            collection_name=name,
            query=vector,
            query_filter=_build_filter(filters),
            limit=top_k,
            score_threshold=threshold if threshold else None,
            with_payload=True,
        )
    except Exception as exc:
        raise VectorStoreError(f"Qdrant search fail ({name}): {exc}") from exc

    return [
        {"score": float(point.score), "payload": dict(point.payload or {})}
        for point in (response.points or [])
    ]


def delete_by_source(name: str, source_id: int | str) -> None:
    """Ek source ke saare chunks hatao (re-ingest ya delete ke waqt)."""
    from qdrant_client import models

    client = get_client()
    try:
        if not client.collection_exists(name):
            return
        client.delete(
            collection_name=name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_id", match=models.MatchValue(value=source_id)
                        )
                    ]
                )
            ),
            wait=True,
        )
    except Exception as exc:
        raise VectorStoreError(f"Qdrant delete fail ({name}): {exc}") from exc


def collection_stats(name: str) -> dict[str, Any]:
    """Chunk count (diagnostics — sources API mein dikhate hain)."""
    client = get_client()
    try:
        if not client.collection_exists(name):
            return {"exists": False, "points": 0}
        info = client.get_collection(name)
        return {"exists": True, "points": int(info.points_count or 0)}
    except Exception as exc:
        raise VectorStoreError(f"collection stats fail ({name}): {exc}") from exc


def is_available() -> bool:
    """Store zinda hai? (RAG ko gracefully skip karne ke liye — crash nahi)."""
    try:
        get_client()
        return True
    except Exception as exc:
        logger.warning("vector store available nahi: %s", exc)
        return False


__all__ = [
    "COLLECTION_KINDS",
    "VectorStoreError",
    "collection_name",
    "collection_stats",
    "delete_by_source",
    "ensure_collection",
    "get_client",
    "is_available",
    "search",
    "store_info",
    "tenant_id",
    "upsert_chunks",
]
