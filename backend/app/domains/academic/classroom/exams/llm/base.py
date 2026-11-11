# ============================================================
# llm/base.py — LLM client ka FACTORY + health check (blueprint §2.4).
#
# Yahan sirf ek kaam: "mujhe ek chat model do" — aur woh model kaun sa hai
# (Ollama ka Qwen / OpenAI / koi bhi OpenAI-compatible gateway) ye .env decide
# karta hai, code nahi.
#
# Kyun factory? Production mein model badalna ek din ka kaam hona chahiye:
#     LLM_MODEL=qwen2.5:latest   →  LLM_MODEL=gpt-4o-mini
#     sirf .env badla, koi .py file nahi. Isi ko "model-agnostic" kehte hain.
#
# 3 concepts jo yaad rakho:
#   1. `lru_cache`   — client ko baar-baar naya nahi banate (HTTP connection
#                      pool reuse hota hai; warna har call pe TLS handshake).
#   2. Timeout       — local model ka pehla token slow aata hai (model RAM mein
#                      load hota hai) → 180s default. Cloud pe 30-60s kaafi.
#   3. `is_llm_available` — generate karne se PEHLE check. Ollama band hai to
#                      teacher ko seedha saaf message mile, 5 min wait ke baad
#                      timeout ka error nahi.
# ============================================================

import json
import logging
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger("eduverse.exams.llm.base")


# ------------------------------------------------------------
# Errors — service layer inhe pakad kar job ko `failed` karti hai
# ------------------------------------------------------------


class LLMNotConfigured(RuntimeError):
    """Provider/galat config — pehli call pe saaf pata chalna chahiye."""


class LLMUnavailable(RuntimeError):
    """Provider tak pahunch nahi rahe (Ollama band, network block, model missing)."""


# ------------------------------------------------------------
# Health check — Ollama ka /api/tags
# ------------------------------------------------------------


def _provider_root() -> str:
    """`http://localhost:11434/v1` → `http://localhost:11434` (health check ke liye).

    OpenAI-compatible base_url hamesha `/v1` pe khatam hota hai; Ollama ka native
    management API (jahan model list milti hai) root pe hota hai.
    """
    url = (settings.LLM_BASE_URL or "").rstrip("/")
    return url[: -len("/v1")] if url.endswith("/v1") else url


def is_llm_available(timeout: float = 5.0) -> tuple[bool, str]:
    """Provider zinda hai? + ek insaani-readable reason.

    Return: `(True, "qwen2.5:latest ready")` ya `(False, "... kyun nahi")`.
    Ye function **kabhi exception nahi phenkta** — health check ka kaam
    "batao" hai, "todo" nahi.
    """
    provider = (settings.LLM_PROVIDER or "").strip().lower()

    if provider == "ollama":
        root = _provider_root()
        try:
            with urllib.request.urlopen(f"{root}/api/tags", timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            return False, (
                f"Ollama not reachable at {root} ({exc}). "
                "Is `ollama serve` chal raha hai?"
            )
        except json.JSONDecodeError:
            return False, f"Ollama at {root} ne invalid JSON diya"

        names = [m.get("name", "") for m in payload.get("models", [])]
        if settings.LLM_MODEL not in names:
            return False, (
                f"Model '{settings.LLM_MODEL}' not installed. Available: "
                f"{', '.join(names) or 'none'} — `ollama pull {settings.LLM_MODEL}`"
            )
        return True, f"{settings.LLM_MODEL} ready ({len(names)} model(s) installed)"

    if provider == "openai":
        if not settings.LLM_API_KEY or settings.LLM_API_KEY == "ollama":
            return False, "OpenAI ke liye LLM_API_KEY set karo (abhi placeholder hai)"
        return True, f"{settings.LLM_MODEL} (OpenAI) — key present"

    return False, f"Unknown LLM_PROVIDER='{settings.LLM_PROVIDER}'"


# ------------------------------------------------------------
# Factory — ek chat model banao
# ------------------------------------------------------------


def build_llm(
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> BaseChatModel:
    """Naya LLM client banao (fresh — cache ke bina).

    Kab use karo: jab alag temperature chahiye (judge ke liye 0.1, generator ke
    liye 0.3) ya test mein explicit model.
    """
    provider = (settings.LLM_PROVIDER or "").strip().lower()
    resolved_model = model or settings.LLM_MODEL
    resolved_temp = settings.LLM_TEMPERATURE if temperature is None else temperature

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "temperature": resolved_temp,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
        "max_retries": settings.LLM_MAX_RETRIES,
    }

    if provider == "ollama":
        if not settings.LLM_BASE_URL:
            raise LLMNotConfigured("LLM_PROVIDER=ollama ke liye LLM_BASE_URL chahiye")
        kwargs["base_url"] = settings.LLM_BASE_URL
        kwargs["api_key"] = settings.LLM_API_KEY or "ollama"

    elif provider == "openai":
        # Fail-fast: Ollama ka URL chhod kar provider openai kar diya ho to
        # confusing error ke bajaye seedha batao.
        if "11434" in (settings.LLM_BASE_URL or ""):
            raise LLMNotConfigured(
                "LLM_PROVIDER=openai hai par LLM_BASE_URL Ollama ka hai "
                f"({settings.LLM_BASE_URL}). OpenAI ke liye ise khaali rakho "
                "(SDK default use hoga) ya apna gateway URL do."
            )
        if settings.LLM_BASE_URL:
            kwargs["base_url"] = settings.LLM_BASE_URL
        kwargs["api_key"] = settings.LLM_API_KEY

    else:
        raise LLMNotConfigured(
            f"Unknown LLM_PROVIDER='{settings.LLM_PROVIDER}' (supported: ollama, openai)"
        )

    logger.debug(
        "building llm provider=%s model=%s temp=%s max_tokens=%s timeout=%ss",
        provider,
        resolved_model,
        resolved_temp,
        kwargs["max_tokens"],
        kwargs["timeout"],
    )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Default client (cached) — generation ke liye.

    `lru_cache` = pehli call pe banta hai, phir wahi object wapas milta hai.
    Isse HTTP connection pool reuse hota hai (local model pe ye seconds bachaata hai).
    """
    return build_llm()


@lru_cache(maxsize=1)
def get_judge_llm() -> BaseChatModel:
    """Quality-check (judge) ke liye client — **temperature 0.1**.

    Judge ko creative nahi hona chahiye: usse sirf "sahi/galat" batana hai.
    Isliye generator (0.3) se alag client, alag cache slot.
    """
    return build_llm(temperature=settings.LLM_JUDGE_TEMPERATURE)


def get_model_info() -> dict[str, Any]:
    """Job ke `model_info` column ke liye — traceability (blueprint §2.7).

    Production mein ye bahut kaam aata hai: "is paper ko kis model ne banaya
    tha?" — 6 mahine baad quality issue aaye to jawab yahin milega.
    """
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "judge_temperature": settings.LLM_JUDGE_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        "base_url": settings.LLM_BASE_URL,
    }
