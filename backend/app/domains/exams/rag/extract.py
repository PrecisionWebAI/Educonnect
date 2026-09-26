# ============================================================
# rag/extract.py — har source type se **plain text** nikaalo (blueprint §2.4 / §2.6).
#
# ------------------------------------------------------------
# Kyun ye file zaroori hai?
# ------------------------------------------------------------
# Frontend ka `SourceStep` 7 tarah ke sources leta hai (A se G). Unme se kuch ka
# content **machine-readable nahi hota**:
#     A PDF       → bytes (text nahi)  → pypdf se nikalta hai
#     B image     → pixels             → OCR/vision chahiye (Phase M4)
#     C URL       → HTML               → tags hata kar text
#     D text      → ready text         → as-is
#     E bank      → already structured questions (retrieval nahi, seedha use)
#     F camera    → image jaisa hi case
#     G library   → saved source ka reference (uska ingestion pehle ho chuka hota)
#
# Ye file **network/parsing** ka kaam karti hai. Iske aage (chunk → embed → store
# → retrieve) sab pure data hai — ek file, ek zimmedari.
#
# ⚠️ IMAGE (OCR) abhi jaan-boojh kar gap hai: blueprint §2.6 ka vision pipeline M4
# ka kaam hai. Isliye image source par saaf warning dete hain (crash nahi), taaki
# teacher ko pata chale ki iska content abhi retrieval mein nahi aayega.
# ============================================================

import html
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.rag.extract")

_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_RE = re.compile(r"</(p|div|li|h[1-6]|tr|br)\s*>", re.IGNORECASE)
_BLANKS_RE = re.compile(r"\n{3,}")
_SPACES_RE = re.compile(r"[ \t]{2,}")

# Frontend ka `SourceType` = "A".."G" → semantic kind
# ⚠️ Ye mapping jaroori hai: frontend codes bhejta hai, backend semantics padhta hai.
# Bina iske "A" ko koi "pdf" nahi samjhega (aur retrieval filter galat lagega).
SOURCE_KIND_BY_CODE: dict[str, str] = {
    "A": "pdf",
    "B": "image",
    "C": "url",
    "D": "text",
    "E": "bank",
    "F": "image",  # camera photo — image pipeline wala hi case
    "G": "library",  # saved library entry (already ingested)
}


class SourceExtractionError(RuntimeError):
    """Source se text nahi nikal paye — caller ise `status=failed` + error banata hai."""


# ------------------------------------------------------------
# HTML / URL
# ------------------------------------------------------------


def strip_html(raw: str) -> str:
    """HTML → readable text (scripts/styles/tags/entities hata kar).

    BeautifulSoup/readability jaisa smart extraction nahi (wo extra dependency
    maangta hai). Ye **bounded aur predictable** hai: jo HTML aata hai, uska text
    ban jaata hai — simple content pages (NCERT jaisi) ke liye kaafi.
    """
    if not raw:
        return ""
    text = _SCRIPT_RE.sub(" ", raw)
    text = _BLOCK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _SPACES_RE.sub(" ", text)
    return _BLANKS_RE.sub("\n\n", text).strip()


def fetch_url_text(url: str) -> tuple[str, list[str]]:
    """URL → (text, warnings). Bounded fetch (size + timeout), hot-link nahi."""
    warnings: list[str] = []
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SourceExtractionError(
            f"URL scheme support nahi: {parsed.scheme or '(none)'}"
        )

    request = urllib.request.Request(
        url,
        headers={
            # kuch sites bina User-Agent 403 de dete hain
            "User-Agent": "EduConnectBot/1.0 (+paper-builder source ingest)"
        },
    )
    max_bytes = int(settings.URL_FETCH_MAX_KB) * 1024
    charset = "utf-8"
    try:
        with urllib.request.urlopen(
            request, timeout=settings.URL_FETCH_TIMEOUT
        ) as resp:
            raw = resp.read(max_bytes + 1)
            try:
                charset = resp.headers.get_content_charset() or "utf-8"
            except Exception:  # header ke bina bhi chalna chahiye
                charset = "utf-8"
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise SourceExtractionError(f"URL fetch fail: {exc}") from exc

    if len(raw) > max_bytes:
        warnings.append(f"URL content {settings.URL_FETCH_MAX_KB}KB par cut kiya gaya")

    try:
        decoded = raw.decode(charset, errors="replace")
    except LookupError:
        decoded = raw.decode("utf-8", errors="replace")

    return strip_html(decoded), warnings


# ------------------------------------------------------------
# PDF
# ------------------------------------------------------------


def extract_pdf_pages(path: Path) -> list[dict[str, Any]]:
    """PDF → `[{page, text}]` (pypdf). Scanned PDF par text khaali aayega.

    ⚠️ Scanned/photo PDF (jismein text layer nahi hoti) → 0 chars. Wo case OCR ka
    hai (vision pipeline, M4). Hum chup nahi rehte — warna teacher ko lagega
    "source upload ho gaya" par retrieval khaali rahega (sabse confusing bug).
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency pyproject mein hai
        raise SourceExtractionError(
            "pypdf install nahi hai — PDF ingest ke liye `uv add pypdf` karo"
        ) from exc

    pages: list[dict[str, Any]] = []
    try:
        reader = PdfReader(str(path))
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # ek page kharab ho to poora ingest na ruke
                logger.warning("pdf page %s extract fail: %s", number, exc)
                text = ""
            pages.append({"page": number, "text": text.strip()})
    except Exception as exc:
        raise SourceExtractionError(
            f"PDF parse fail: {type(exc).__name__}: {exc}"
        ) from exc

    return pages


# ------------------------------------------------------------
# Common entry point
# ------------------------------------------------------------


def resolve_local_path(storage_key: str | None) -> Path | None:
    """`storage_key` → disk path (upload folder ke andar, path-traversal safe).

    ⚠️ Security: user-supplied path seedha kholna = arbitrary file read. Isliye
    **basename** lete hain aur upload dir ke andar hi dhundhte hain.
    """
    if not storage_key:
        return None
    base = Path(settings.UPLOAD_DIR)
    candidate = base / Path(storage_key).name
    return candidate if candidate.exists() else None


def extract_source(source: dict[str, Any]) -> dict[str, Any]:
    """Frontend ka ek SourceItem → `{kind, pages, text, warnings, url}`.

    Saare branches yahin normalise hote hain, taaki ingest/retrieval ko sirf
    `pages` dikhe (har jagah apna-apna parsing nahi).
    """
    code = str(source.get("sourceType") or "D").upper()[:1]
    kind = SOURCE_KIND_BY_CODE.get(code, "text")
    warnings: list[str] = []
    pages: list[dict[str, Any]] = []
    text = ""

    if kind == "text":
        text = str(source.get("textExcerpt") or source.get("text") or "").strip()
        if text:
            pages = [{"page": 0, "text": text}]

    elif kind == "url":
        url = str(source.get("url") or "").strip()
        if not url:
            raise SourceExtractionError("URL source mein `url` khaali hai")
        text, warnings = fetch_url_text(url)
        if text:
            pages = [{"page": 0, "text": text}]

    elif kind == "pdf":
        storage_key = source.get("storageKey") or source.get("fileName")
        path = resolve_local_path(str(storage_key) if storage_key else None)
        if path is None:
            raise SourceExtractionError(
                f"PDF file nahi mili (storageKey={storage_key!r}) — pehle "
                "`POST /exams/sources/upload` se upload karo"
            )
        pages = extract_pdf_pages(path)
        text = "\n\n".join(p["text"] for p in pages if p["text"]).strip()

    elif kind == "image":
        warnings.append(
            "Image source ka text extraction abhi nahi hai (vision/OCR pipeline "
            "Phase M4 mein hai) — is source ka content retrieval mein nahi aayega."
        )

    elif kind in ("bank", "library"):
        # Structured/managed sources: bank items seedha question bank se aate hain,
        # aur library entries ka apna ingestion pehle ho chuka hota hai.
        if source.get("libraryEntryId"):
            warnings.append(
                "Library entry — content pehle se indexed hai, dobara ingest nahi karte"
            )
        else:
            warnings.append("Bank source ka content structured hai (text ingest nahi)")

    else:  # pragma: no cover - naya type aaya to chup na raho
        warnings.append(f"Unknown source kind '{kind}' — content skip kiya")

    if not text and not pages and not warnings:
        warnings.append("Source mein koi text nahi mila")

    return {
        "kind": kind,
        "text": text,
        "pages": pages,
        "warnings": warnings,
        "url": source.get("url"),
    }


__all__ = [
    "SOURCE_KIND_BY_CODE",
    "SourceExtractionError",
    "extract_pdf_pages",
    "extract_source",
    "fetch_url_text",
    "resolve_local_path",
    "strip_html",
]
