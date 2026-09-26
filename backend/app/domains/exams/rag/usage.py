# ============================================================
# rag/usage.py — anti-repeat: "ye question pehle aa chuka hai" (blueprint §1.2.1).
#
# ------------------------------------------------------------
# Problem
# ------------------------------------------------------------
# Teacher ne Unit Test 1 mein "Which organism converts milk into curd?" pucha.
# Ab Half-Yearly banate waqt wahi question dobara aa jaye — ye **bura lagta hai**
# (aur blueprint ka explicit promise hai: "reuse is content-aware, same topics,
# NEW questions every time").
#
# ------------------------------------------------------------
# Solution: fingerprint + lookback (dono yahin, pure functions)
# ------------------------------------------------------------
#   · `normalise()`  — text ko compare-layak banata hai (case/punctuation/numbers)
#   · `fingerprint()`— us normalised text ka chhota hash (DB index ke liye)
#   · `is_duplicate()`— naya question pehle ke kisi question se milta hai?
#
# ⚠️ Yahi **pure logic** hai — DB ka kaam nahi. Persistence (kis paper mein kab
# use hua) `exams/repository.py` + `questionusagelog` table karta hai. Isi wajah
# se ye functions bina DB ke test ho jaate hain.
# ============================================================

import hashlib
import re

_WORD_RE = re.compile(r"[a-z0-9]+")


def normalise(text: str) -> str:
    """Compare-ready text: lowercase + sirf alphanumeric words.

    Numbers bhi rakhte hain (kuch questions ka jawab number hota hai), par
    punctuation/space ka farq mita dete hain — taaki "What is photosynthesis?"
    aur "What is photosynthesis" **same** maane jayein.
    """
    return " ".join(_WORD_RE.findall((text or "").lower()))


def fingerprint(text: str) -> str:
    """Normalised text ka sha1 (16 chars) — DB index/unique key ke liye.

    Poora text store bhi karte hain (insani debugging ke liye), par duplicate
    check **fingerprint** par hota hai — chhota, fast, aur index-friendly.
    """
    return hashlib.sha1(normalise(text).encode("utf-8")).hexdigest()[:16]


def _tokens(text: str) -> set[str]:
    """Chhote shabd (is/of/ka/the) hata kar token set — near-duplicate detection."""
    return {t for t in normalise(text).split() if len(t) > 3}


def is_duplicate(
    candidate: str, existing: list[str], *, threshold: float = 0.85
) -> bool:
    """Naya question pehle ke kisi se **near-duplicate** hai?

    Do level:
      1. exact fingerprint match        → pakka duplicate
      2. Jaccard token overlap ≥ 0.85   → same question thoda badla hua
                                            ("...converts milk into curd?" vs
                                             "...helps in making curd?")
    Ye check deterministic hai (LLM nahi) — isliye free + instant, aur
    prompt ke "already used" block ke saath **double safety** deta hai.
    """
    if not candidate.strip():
        return False

    target = fingerprint(candidate)
    candidate_tokens = _tokens(candidate)

    for text in existing or []:
        if fingerprint(text) == target:
            return True
        other = _tokens(text)
        if not other or not candidate_tokens:
            continue
        overlap = len(candidate_tokens & other) / len(candidate_tokens | other)
        if overlap >= threshold:
            return True
    return False


__all__ = ["fingerprint", "is_duplicate", "normalise"]
