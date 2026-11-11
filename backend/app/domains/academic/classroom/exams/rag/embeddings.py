# ============================================================
# rag/embeddings.py — text → vector (blueprint §2.4).
#
# Ek hi kaam: text ki list lo, vectors ki list do. Kaun sa model? Woh `.env`
# decide karta hai (`EMBEDDING_PROVIDER`), code nahi — bilkul waise hi jaise
# LLM layer mein `LLM_MODEL` karta hai.
#
# ------------------------------------------------------------
# ⭐ Teen providers, aur teeno ki zaroorat kyun hai
# ------------------------------------------------------------
#   "dummy"  — deterministic HASHING embeddings (default):
#              · internet/API key/Ollama — kuch bhi nahi chahiye
#              · poora RAG pipeline (chunk → embed → store → search → prompt)
#                aaj hi chal jaata hai, aur tests **offline** pass hote hain
#              · quality: sirf lexical (shabd match), semantic nahi — isliye
#                sirf dev/test/demo ke liye. Production mein neeche wale chuno.
#   "ollama" — local embeddings (`nomic-embed-text`): offline + free + **semantic**
#   "hf"     — HuggingFace Inference API (token chahiye)
#
# ------------------------------------------------------------
# ⚠️ Encoding note (chhota par bada)
# ------------------------------------------------------------
# `dummy` provider hash se vector banata hai. Sirf hash ke bytes ko float mein
# badal dena aasan hai, par phir "same words = same direction" wala fayda chala
# jaata hai aur search random junk deta hai (dev mein "RAG toota lagta hai",
# jabki asli model ke saath theek chalega). Isliye hum **token-level hashing +
# L2 normalise** karte hain — milte-julte text ke vectors paas aate hain.
# ============================================================

import hashlib
import json
import logging
import math
import re
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.rag.embeddings")

_WORD_RE = re.compile(r"[a-z0-9]+")

# Chhota in-process cache: same text dobara embed na ho (ingest aur query dono
# mein same chapter ke naam aate hain). Simple dict + size cap = LRU-jaisa.
_CACHE: dict[tuple[str, str, int, str], list[float]] = {}
_CACHE_LIMIT = 4096


class EmbeddingsUnavailable(RuntimeError):
    """Provider tak nahi pahunch paye — caller ko saaf message dena chahiye."""


# ------------------------------------------------------------
# Provider info (job ke `model_info` mein jaata hai — traceability §2.7)
# ------------------------------------------------------------


def provider_info() -> dict[str, Any]:
    """Kaun sa embedding model chal raha hai (audit/debug ke liye)."""
    return {
        "provider": (settings.EMBEDDING_PROVIDER or "dummy").strip().lower(),
        "model": settings.EMBEDDING_MODEL,
        "dimensions": settings.EMBEDDING_DIMENSIONS,
    }


def embedding_dim() -> int:
    """Vector ki length — collection banate waqt isi ki zaroorat padti hai."""
    return int(settings.EMBEDDING_DIMENSIONS)


# ------------------------------------------------------------
# dummy — deterministic hashing (offline, koi API nahi)
# ------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (punctuation/space se azaad)."""
    return _WORD_RE.findall((text or "").lower())


def _embed_dummy_one(text: str, dim: int) -> list[float]:
    """Token-hashing embedding: deterministic, offline, L2-normalised.

    Kaam:
      · har token ko sha256 se ek index par map karo (dim ke andar)
      · us index par weight jodo (lamba token = zyada weight)
      · aakhir mein L2 normalise (cosine == dot product)
    """
    vec = [0.0] * dim
    tokens = _tokens(text)
    if not tokens:
        return vec

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        weight = 1.0 + math.log1p(len(token))
        # sign bhi hash se — collision par ek doosre ko cancel bhi kar sakte hain
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


# ------------------------------------------------------------
# ollama — local embeddings (offline + free + semantic)
# ------------------------------------------------------------


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    """Ollama ka `/api/embed` — wahi server jo LLM chala raha hai.

    Ollama sirf chat nahi, embeddings bhi deta hai (`ollama pull nomic-embed-text`
    ya `bge-m3`). Isse RAG bilkul offline ho jaata hai — koi API key nahi.
    """
    base = (settings.LLM_BASE_URL or "http://localhost:11434/v1").rstrip("/")
    root = base[: -len("/v1")] if base.endswith("/v1") else base
    payload = json.dumps({"model": settings.EMBEDDING_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        f"{root}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise EmbeddingsUnavailable(f"Ollama embeddings fail: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EmbeddingsUnavailable(
            "Ollama ne embeddings ka invalid JSON diya"
        ) from exc

    vectors = data.get("embeddings") or []
    if len(vectors) != len(texts):
        raise EmbeddingsUnavailable(
            f"Ollama ne {len(vectors)} vectors diye, {len(texts)} chahiye the"
        )
    return [list(map(float, v)) for v in vectors]


# ------------------------------------------------------------
# hf — HuggingFace Inference API
# ------------------------------------------------------------


def _hf_embed(texts: list[str]) -> list[list[float]]:
    """HF Inference API (feature-extraction). Token `.env` se."""
    if not settings.HUGGINGFACE_API_KEY:
        raise EmbeddingsUnavailable(
            "EMBEDDING_PROVIDER=hf ke liye HUGGINGFACE_API_KEY chahiye"
        )
    url = (
        "https://api-inference.huggingface.co/pipeline/feature-extraction/"
        f"{settings.EMBEDDING_MODEL}"
    )
    payload = json.dumps(
        {"inputs": texts, "options": {"wait_for_model": True}}
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise EmbeddingsUnavailable(f"HF embeddings fail: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EmbeddingsUnavailable("HF ne embeddings ka invalid JSON diya") from exc

    if not isinstance(data, list):
        raise EmbeddingsUnavailable(f"HF ka unexpected output: {str(data)[:200]}")

    # HF do shape deta hai: [[...]] (pooled) ya [ [ [..] ] ] (token-level).
    # Dono ko "ek vector per text" mein normalise karte hain.
    out: list[list[float]] = []
    for item in data:
        if item and isinstance(item[0], list):
            dim = len(item[0])
            pooled = [sum(row[i] for row in item) / dim for i in range(dim)]
            out.append(pooled)
        else:
            out.append(list(map(float, item)))
    return out


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------


def _cache_key(text: str) -> tuple[str, str, int, str]:
    return (
        (settings.EMBEDDING_PROVIDER or "dummy").strip().lower(),
        settings.EMBEDDING_MODEL,
        embedding_dim(),
        text,
    )


def embed_texts(texts: list[str], *, use_cache: bool = True) -> list[list[float]]:
    """Texts → vectors (batch, provider-agnostic, cached).

    Batch kyun? Network/API wale providers mein 1 call = latency; 20 chunks ko
    20 calls mein bhejna 20x slow hai. Isliye `EMBEDDING_BATCH_SIZE` ke hisaab se
    chunk karke bhejte hain.
    """
    if not texts:
        return []

    provider = (settings.EMBEDDING_PROVIDER or "dummy").strip().lower()
    dim = embedding_dim()

    if provider == "dummy":
        # Hashing local hai — na network, na cache ki zaroorat (sasta bhi hai).
        return [_embed_dummy_one(t, dim) for t in texts]

    pending: list[str] = []
    results: dict[int, list[float]] = {}
    if use_cache:
        for i, text in enumerate(texts):
            cached = _CACHE.get(_cache_key(text))
            if cached is not None:
                results[i] = cached
            else:
                pending.append(text)
    else:
        pending = list(texts)

    if pending:
        batch_size = max(1, int(settings.EMBEDDING_BATCH_SIZE))
        fresh: list[list[float]] = []
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            if provider == "ollama":
                fresh.extend(_ollama_embed(batch))
            elif provider == "hf":
                fresh.extend(_hf_embed(batch))
            else:
                raise EmbeddingsUnavailable(
                    f"Unknown EMBEDDING_PROVIDER='{provider}' (dummy | ollama | hf)"
                )

        for text, vector in zip(pending, fresh, strict=False):
            if use_cache:
                if len(_CACHE) >= _CACHE_LIMIT:
                    _CACHE.pop(next(iter(_CACHE)))
                _CACHE[_cache_key(text)] = vector

        # Order restore: pending ki position par wahi vector rakho
        pending_iter = iter(fresh)
        for i in range(len(texts)):
            if i not in results:
                results[i] = next(pending_iter)

    out: list[list[float]] = []
    for i in range(len(texts)):
        vec = results.get(i)
        if vec is None:
            raise EmbeddingsUnavailable("embedding missing (internal ordering bug)")
        if len(vec) != dim:
            # ⚠️ Ye check production mein bahut kaam ka hai: collection ka vector
            # size fix hota hai, aur mismatch = Qdrant "dimension error" (jo
            # ingest ke waqt hi pakda jaana chahiye, search ke waqt nahi).
            raise EmbeddingsUnavailable(
                f"embedding dim mismatch: mila {len(vec)}, chahiye {dim} "
                f"(model={settings.EMBEDDING_MODEL})"
            )
        out.append(vec)
    return out


def embed_text(text: str) -> list[float]:
    """Ek text ka vector (query ke liye convenience wrapper)."""
    return embed_texts([text])[0]


def clear_cache() -> None:
    """Test/diagnostics ke liye — cache khaali."""
    _CACHE.clear()


__all__ = [
    "EmbeddingsUnavailable",
    "clear_cache",
    "embed_text",
    "embed_texts",
    "embedding_dim",
    "provider_info",
]
