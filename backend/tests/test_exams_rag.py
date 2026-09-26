"""B2 regression tests — RAG (chunking, embeddings, vector store, retrieval).

Sab kuch **offline** chalta hai:
  · embeddings → `dummy` provider (hashing, koi API nahi)
  · vector DB  → Qdrant ka **local persistent** mode (ek temp folder)
Isliye CI mein bhi ye tests bina network chalti hain, aur pipeline (extract →
chunk → embed → upsert → search → prompt-ready excerpts) poora verify hota hai.
"""

import pytest

from app.core.config import settings
from app.domains.exams.llm.services import config_to_source
from app.domains.exams.rag import store
from app.domains.exams.rag.chunking import chunk_pages, chunk_text, tag_chapters
from app.domains.exams.rag.embeddings import embed_text, embed_texts, embedding_dim
from app.domains.exams.rag.extract import extract_source, strip_html
from app.domains.exams.rag.ingest import ingest_source
from app.domains.exams.rag.retriever import build_queries, context_pack
from app.domains.exams.rag.usage import fingerprint, is_duplicate, normalise

# ------------------------------------------------------------
# Chunking — page-aware + overlap (page number prompt traceability ke liye)
# ------------------------------------------------------------


def test_chunk_text_respects_size_and_overlap() -> None:
    text = " ".join(f"Sentence number {i} about microorganisms." for i in range(60))

    chunks = chunk_text(text, chunk_size=200, overlap=40)

    assert len(chunks) > 1
    assert all(len(c) <= 220 for c in chunks)  # size + boundary tolerance
    # Overlap: lagbhag har chunk ka shuruaati hissa pichhle chunk mein bhi milta hai
    assert any(chunks[0][-20:] in chunks[1] for _ in [0])


def test_chunk_pages_keeps_page_numbers() -> None:
    pages = [
        {"page": 1, "text": "A" * 500},
        {"page": 2, "text": "B" * 500},
    ]

    chunks = chunk_pages(pages)

    assert {c["page"] for c in chunks} == {1, 2}
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_tag_chapters_matches_names_inside_text() -> None:
    tagged = tag_chapters(
        "This page explains Microorganisms and how curd is formed.",
        ["Microorganisms", "Coal & Petroleum"],
    )

    assert tagged == ["Microorganisms"]


# ------------------------------------------------------------
# Embeddings — deterministic + dimension-safe (dummy provider)
# ------------------------------------------------------------


def test_dummy_embeddings_are_deterministic_and_normalised() -> None:
    vector_a = embed_text("Microorganisms convert milk into curd")
    vector_b = embed_text("Microorganisms convert milk into curd")

    assert vector_a == vector_b  # deterministic (test/dev ka bharosa)
    assert len(vector_a) == embedding_dim()
    norm = sum(v * v for v in vector_a)
    assert norm == pytest.approx(1.0, abs=1e-6)  # L2 normalised — cosine == dot


def test_embed_texts_keeps_batch_order() -> None:
    texts = ["alpha microorganisms", "beta photosynthesis", "gamma curd"]
    vectors = embed_texts(texts)

    assert len(vectors) == 3
    assert vectors[0] != vectors[1] != vectors[2]


# ------------------------------------------------------------
# Extract — HTML strip + source-type mapping (A..G)
# ------------------------------------------------------------


def test_strip_html_removes_tags_and_scripts() -> None:
    html = (
        "<html><head><style>p{color:red}</style></head>"
        "<body><h1>Microorganisms</h1><p>Yeast makes bread rise.</p>"
        "<script>alert('x')</script></body></html>"
    )

    text = strip_html(html)

    assert "Microorganisms" in text
    assert "Yeast makes bread rise." in text
    assert "alert" not in text
    assert "color:red" not in text


def test_extract_source_maps_frontend_codes() -> None:
    paste = extract_source({"sourceType": "D", "textExcerpt": "Notes about curd."})
    bank = extract_source({"sourceType": "E", "bankRef": "qb-1"})

    assert paste["kind"] == "text"
    assert paste["pages"][0]["text"] == "Notes about curd."
    assert bank["kind"] == "bank"  # structured source → text ingest nahi
    assert bank["warnings"]


# ------------------------------------------------------------
# Vector store + ingest + retrieval — poora round-trip (local Qdrant)
# ------------------------------------------------------------


@pytest.fixture()
def local_vector_store(tmp_path, monkeypatch):
    """Qdrant ko temp folder par point karo (local persistent mode) + cache clear.

    ⚠️ `get_client()` aur `store_info()` cached hain, isliye test ke baad cache
    clear karna zaroori hai — warna doosre test ko pehle wala client mil jaata hai
    (jo temp folder ke saath band ho chuka hota hai).
    """
    monkeypatch.setattr(settings, "QDRANT_URL", "", raising=False)
    monkeypatch.setattr(
        settings, "QDRANT_LOCAL_PATH", str(tmp_path / "qdrant"), raising=False
    )
    monkeypatch.setattr(settings, "RAG_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "dummy", raising=False)
    monkeypatch.setattr(settings, "VECTOR_TENANT", "test", raising=False)
    store.get_client.cache_clear()

    yield

    try:
        client = store.get_client()
        client.close()
    except Exception:  # pragma: no cover - cleanup best effort
        pass
    store.get_client.cache_clear()


def test_ingest_then_retrieve_round_trip(local_vector_store) -> None:
    source = {
        "sourceType": "D",
        "label": "My Science notes",
        "textExcerpt": (
            "Microorganisms are tiny living organisms. Yeast is a fungus used in "
            "making bread. Bacteria called Lactobacillus convert milk into curd. "
            "Protozoa cause diseases like malaria. Algae prepare their own food."
        ),
    }

    result = ingest_source(
        source,
        source_id=101,
        class_name="8",
        subject="Science",
        board="CBSE",
        chapters=["Microorganisms"],
        label="My Science notes",
    )

    assert result["ok"] is True, result
    assert result["chunks"] >= 1
    assert result["collection"] == store.collection_name(None, "chunks")

    paper = config_to_source(
        {
            "title": "Unit Test",
            "total_marks": 10,
            "class_name": "8",
            "subject": "Science",
            "chapters": ["Microorganisms"],
            "blueprint": [{"type": "MCQ", "count": 10, "marksEach": 1}],
        }
    )

    pack = context_pack(paper)

    assert pack["used_rag"] is True
    assert pack["hits"], pack["warnings"]
    # Prompt ke `<source>` block ke liye excerpts label + page ke saath aate hain
    assert any("My Science notes" in e for e in pack["excerpts"])
    assert pack["sources"][0]["sourceType"] == "D"


def test_retrieval_without_ingest_reports_clear_warning(local_vector_store) -> None:
    paper = config_to_source(
        {
            "title": "Unit Test",
            "total_marks": 10,
            "class_name": "9",
            "subject": "Maths",
            "chapters": ["Polynomials"],
            "blueprint": [{"type": "MCQ", "count": 10, "marksEach": 1}],
        }
    )

    pack = context_pack(paper)

    assert pack["used_rag"] is False
    assert pack["excerpts"] == []
    assert any("collection" in w.lower() for w in pack["warnings"])


def test_build_queries_is_chapter_wise() -> None:
    paper = config_to_source(
        {
            "title": "Unit Test",
            "total_marks": 20,
            "class_name": "8",
            "subject": "Science",
            "chapters": ["Microorganisms", "Coal & Petroleum"],
            "blueprint": [{"type": "MCQ", "count": 20, "marksEach": 1}],
        }
    )

    queries = build_queries(paper)

    assert len(queries) == 2  # ek chapter = ek query (coverage ka asli tareeka)
    assert "Microorganisms" in queries[0]
    assert "Coal & Petroleum" in queries[1]
    assert all("class 8" in q.lower() for q in queries)


# ------------------------------------------------------------
# Anti-repeat (usage fingerprint) — pure logic
# ------------------------------------------------------------


def test_fingerprint_ignores_case_and_punctuation() -> None:
    assert fingerprint("What is photosynthesis?") == fingerprint(
        "what is photosynthesis"
    )
    assert normalise("Curd  is  made by Lactobacillus!") == (
        "curd is made by lactobacillus"
    )


def test_is_duplicate_catches_near_duplicates() -> None:
    used = ["Which organism converts milk into curd?"]

    assert is_duplicate("Which organism converts milk into curd?", used) is True
    assert is_duplicate("Which organism converts milk into curd", used) is True
    assert is_duplicate("State Newton's second law of motion.", used) is False
