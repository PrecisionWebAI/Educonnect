# ============================================================
# rag/chunking.py — lambe text ko chhote "chunks" mein toda (blueprint §2.4).
#
# ------------------------------------------------------------
# Chunking kya hai, aur bina iske kya hota hai?
# ------------------------------------------------------------
# Embedding model ki "context window" chhoti hoti hai, aur poora chapter ek vector
# mein daalne se **detail kho jaati hai** (average ban jaata hai). Isliye:
#     chapter (50,000 chars) → 60-80 chunks (800 chars) → 60-80 vectors
# Retrieval phir **relevanT chunk** laata hai, poora chapter nahi. Yahi RAG ki
# asli taaqat hai — prompt mein sirf kaam ka hissa jaata hai.
#
# ⚠️ Overlap kyun? Sentence boundary theek beech mein kat sakti hai
# ("...plants make food using" | "sunlight, water and CO2"). 100-char overlap se
# dono chunks mein thoda context bacha rehta hai — answer adhoora nahi rehta.
# ============================================================

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.rag.chunking")

_SPACE_RE = re.compile(r"[ \t]+")


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """Text → chunks (boundary-aware + overlap ke saath).

    Cut karne ka order (jo pehle mile, wahi use karte hain):
        1. paragraph break ("\\n\\n")  — sabse saaf
        2. sentence end (". ")
        3. space                       — last resort
    Aur agar koi boundary `chunk_size` ke aadhe se pehle milti hai to usse
    **ignore** karte hain — warna chunks bahut chhote-chhote ban jaate hain
    (search mein useless, aur ingest slow).
    """
    size = int(chunk_size or settings.CHUNK_SIZE)
    ov = int(overlap if overlap is not None else settings.CHUNK_OVERLAP)
    clean = _SPACE_RE.sub(" ", (text or "").replace("\r\n", "\n")).strip()
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]

    chunks: list[str] = []
    start = 0
    total = len(clean)
    while start < total:
        end = min(start + size, total)
        if end < total:
            window = clean[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind(" "))
            if cut > size // 2:
                end = start + cut + 1

        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= total:
            break
        # Overlap ke liye peeche jaao, par aage badhna zaroori (infinite loop nahi)
        start = max(end - ov, start + 1)

    return chunks


def chunk_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`[{page, text}]` → `[{text, page, chunk_index, chars}]`.

    Page number kyun rakhte hain? Isse prompt mein `[NCERT p.14]` likh sakte hain
    — blueprint §2.3.4 ki "source traceability": teacher ko dikh sake ki question
    kis page se aaya, aur answer verify ho sake.
    """
    out: list[dict[str, Any]] = []
    index = 0
    for page in pages or []:
        number = int(page.get("page") or 0)
        for piece in chunk_text(str(page.get("text") or "")):
            out.append(
                {
                    "text": piece,
                    "page": number,
                    "chunk_index": index,
                    "chars": len(piece),
                }
            )
            index += 1
    return out


def tag_chapters(text: str, chapters: list[str]) -> list[str]:
    """Chunk ke andar kaun se chapter ka zikr hai (heuristic tagging).

    Retrieval filter ke liye kaam aata hai: agar page 14 par "Microorganisms"
    likha hai to us chunk ko usi chapter se jod dete hain. Exact science nahi —
    par **filter ka fallback** yahi hota hai jab source par chapter labels nahi
    (jo common hai: PDF ke andar chapter names hote hain, metadata mein nahi).
    """
    lowered = (text or "").lower()
    return [c for c in chapters or [] if c and c.lower() in lowered]


__all__ = ["chunk_pages", "chunk_text", "tag_chapters"]
