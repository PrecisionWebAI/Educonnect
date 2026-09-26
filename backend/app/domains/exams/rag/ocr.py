# ============================================================
# rag/ocr.py — image source ka text (blueprint §2.6, M4 ka pehla step).
#
# ------------------------------------------------------------
# Kyun alag file? (aur kyun default OFF hai)
# ------------------------------------------------------------
# Image (Type B) ka koi text layer nahi hota — pixels hote hain. Retrieval ke
# liye usse text banana padta hai, warna `extract_source()` sirf warning deta
# hai aur us source ka content AI ke paas pahunchta hi nahi.
#
# OCR ek **extra system dependency** hai (tesseract binary + uska python
# wrapper, ya ek vision model). Isliye provider pluggable hai aur default
# `none` hai — jis machine par OCR install nahi, wahan pipeline phir bhi chalti
# hai (chup-chaap khaali nahi hoti, saaf warning milti hai).
#
#   OCR_PROVIDER="none"      → kuch nahi (warning: "OCR off hai")
#   OCR_PROVIDER="tesseract" → pytesseract + Pillow (local, free, offline)
#   OCR_PROVIDER="vision"    → vision-capable LLM (jaise Ollama qwen2.5-vl)
#
# ⚠️ Kabhi raise nahi karta: `(text, warnings)` return karta hai. Ingest
# background mein chalti hai, isliye ek image ka OCR fail hona poore source
# ko fail nahi karna chahiye.
# ============================================================

import base64
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.rag.ocr")

# Image extensions jo hum OCR kar sakte hain (upload flow images leta hai).
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif")


def provider() -> str:
    """Effective provider — `OCR_ENABLED=false` ho to hamesha `"none"`."""
    if not settings.OCR_ENABLED:
        return "none"
    return (settings.OCR_PROVIDER or "none").strip().lower()


def is_enabled() -> bool:
    """OCR chalu hai? (extract.py isse warning vs. real extraction decide karta hai)"""
    return provider() != "none"


def _trim(text: str) -> str:
    limit = int(settings.OCR_MAX_CHARS)
    cleaned = "\n".join(line.strip() for line in str(text or "").splitlines())
    cleaned = cleaned.strip()
    return cleaned[:limit] if len(cleaned) > limit else cleaned


# ------------------------------------------------------------
# Provider 1 — tesseract (local, offline)
# ------------------------------------------------------------


def _ocr_with_tesseract(path: Path) -> tuple[str, list[str]]:
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return "", [
            "OCR provider 'tesseract' chuna hai par `pytesseract`/`Pillow` "
            "install nahi hai — `uv add pytesseract pillow` chalao (aur system "
            "tesseract binary bhi install karo)."
        ]

    try:
        with Image.open(path) as img:
            text = pytesseract.image_to_string(img, lang=settings.OCR_LANGUAGE)
    except Exception as exc:  # tesseract binary missing / kharab image
        return "", [f"OCR (tesseract) fail: {type(exc).__name__}: {exc}"]

    return _trim(text), []


# ------------------------------------------------------------
# Provider 2 — vision LLM (multimodal)
# ------------------------------------------------------------


def _ocr_with_vision(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from langchain_core.messages import HumanMessage
    except ImportError:  # pragma: no cover - dependency pyproject mein hai
        return "", ["langchain-core install nahi hai — vision OCR skip"]

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return "", [f"OCR (vision) fail: image padhi nahi ja saki ({exc})"]

    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    prompt = (
        "Extract ALL readable text from this image (OCR). Also describe any "
        "diagram/table briefly, line by line. Return plain text only."
    )
    try:
        # Import yahan: LLM layer optional hai, OCR ke bina bhi graph chalta hai.
        from app.domains.exams.llm.base import get_llm

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        )
        response = get_llm().invoke([message])
    except Exception as exc:
        return "", [
            f"OCR (vision) fail: {type(exc).__name__}: {exc} — kya model vision "
            "support karta hai?"
        ]

    content: Any = getattr(response, "content", response)
    if isinstance(content, list):  # structured content blocks
        content = " ".join(
            str(part.get("text") if isinstance(part, dict) else part)
            for part in content
        )
    text = _trim(str(content or ""))
    if not text:
        warnings.append("Vision model ne is image se koi text nahi nikala")
    return text, warnings


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------


def ocr_image(path: Path) -> tuple[str, list[str]]:
    """Image file → `(text, warnings)`. **Kabhi raise nahi karta.**

    `path` wo file hai jo upload flow ne `UPLOAD_DIR` mein rakhi hai.
    """
    selected = provider()
    if selected == "none":
        return "", [
            "OCR off hai (OCR_ENABLED=false) — is image ka content retrieval "
            "mein nahi jaayega. Chalu karne ke liye `.env` mein OCR_ENABLED=true "
            "+ OCR_PROVIDER=tesseract (ya vision) set karo."
        ]
    if not path.exists():
        return "", [f"OCR skip: image file nahi mili ({path.name})"]

    logger.info("OCR (%s) shuru: %s", selected, path.name)
    if selected == "tesseract":
        return _ocr_with_tesseract(path)
    if selected == "vision":
        return _ocr_with_vision(path)
    return "", [f"Unknown OCR provider '{selected}' — OCR skip kiya"]


__all__ = ["IMAGE_SUFFIXES", "is_enabled", "ocr_image", "provider"]
