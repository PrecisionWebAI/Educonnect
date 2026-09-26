# ============================================================
# rag/hashing.py — content hashing (dedup + traceability).
#
# ------------------------------------------------------------
# Kyun ek alag module? (aur kya galti isse bachti hai)
# ------------------------------------------------------------
# Yahan **teen** level ke hash banate hain, aur teeno ka kaam alag hai:
#
#   1. `file_hash(bytes)`   — uploaded PDF/image ke **exact bytes** ka sha256.
#                             Same file dobara upload → same hash → purana
#                             source (aur uske vectors) reuse.
#   2. `content_hash(...)`  — text/URL jaise "file-less" sources ke liye
#                             canonical sha256 (type + normalised payload).
#   3. `chunk_hash(text)`   — ek chunk ke text ka sha256 (normalised). Ye
#                             Qdrant payload mein jaata hai, taaki **vector
#                             level** par bhi dedup/traceability ho ("ye vector
#                             kis content ka tha").
#
# ⚠️ Normalisation (case + whitespace) zaroori hai: warna wahi notes jab teacher
# "Microorganisms " aur "microorganisms" ke roop mein save kare to do alag hash
# bante hain aur dedup bekaar ho jaata hai. Isliye hash se pehle text ko
# **casefold + whitespace-collapse** karte hain (file bytes ko nahi — wahan
# byte-for-byte identity hi sahi meaning hai).
# ============================================================

import hashlib

__all__ = ["chunk_hash", "content_hash", "file_hash", "normalise_text"]


def normalise_text(text: str) -> str:
    """Hash ke liye canonical text: lowercase + saare whitespace ek space.

    `"Micro  Organisms\\n\\nCh 2 "` → `"micro organisms ch 2"`.
    """
    return " ".join(str(text or "").split()).casefold()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_hash(data: bytes | bytearray) -> str:
    """Uploaded file ke bytes ka sha256 (exact bytes — koi normalisation nahi)."""
    return _sha256(bytes(data or b""))


def content_hash(*parts: object) -> str:
    """Kuch bhi (type code, text, url, chapters…) → ek stable sha256.

    Parts ko `"|"` se jodte hain aur text parts ko normalise karte hain, taaki
    `("D", "Notes A")` aur `("d", "notes   a")` ka **wahi** hash bane.
    """
    tokens: list[str] = []
    for part in parts:
        if part in (None, ""):
            continue
        if isinstance(part, (list, tuple, set)):
            tokens.extend(normalise_text(str(p)) for p in part if p not in (None, ""))
        else:
            tokens.append(normalise_text(str(part)))
    return _sha256("|".join(tokens).encode("utf-8"))


def chunk_hash(text: str) -> str:
    """Ek chunk ke text ka sha256 (normalised) — Qdrant payload ki traceability."""
    return _sha256(normalise_text(text).encode("utf-8"))
