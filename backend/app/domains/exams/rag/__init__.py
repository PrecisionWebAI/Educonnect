# ============================================================
# exams/rag — Retrieval Augmented Generation (blueprint §2.4, M2).
#
# Layer ka kaam: "teacher ka source content" ko **dhoondhne layak** banana, aur
# generation ke waqt uska **relevanT hissa** prompt mein bhejna.
#
#   extract  → source se text (PDF/URL/text; image = M4 vision)
#   chunk    → text ko ~800 char tukdon mein (page number ke saath)
#   embed    → chunk/text ka vector (dummy | ollama | hf)
#   store    → Qdrant (server mode ya local persistent dev mode)
#   ingest   → upar ke saare steps ek saath (per source)
#   retriever→ query banao + search + prompt-ready context pack
#   usage    → "ye question pehle aa chuka hai" (anti-repeat fingerprint)
#
# ⚠️ Yahan koi DB/HTTP ka kaam nahi hota (wo `exams/service.py` karta hai) —
# bilkul `llm/` layer ki tarah: sirf AI/data ka kaam.
# ============================================================

from app.domains.exams.rag import store
from app.domains.exams.rag.chunking import chunk_pages, chunk_text
from app.domains.exams.rag.embeddings import embed_text, embed_texts, embedding_dim
from app.domains.exams.rag.extract import extract_source, strip_html
from app.domains.exams.rag.ingest import ingest_source, remove_source
from app.domains.exams.rag.retriever import build_queries, context_pack
from app.domains.exams.rag.usage import fingerprint, is_duplicate, normalise

__all__ = [
    "build_queries",
    "chunk_pages",
    "chunk_text",
    "context_pack",
    "embed_text",
    "embed_texts",
    "embedding_dim",
    "extract_source",
    "fingerprint",
    "ingest_source",
    "is_duplicate",
    "normalise",
    "remove_source",
    "store",
    "strip_html",
]
