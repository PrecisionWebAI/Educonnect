"""Phase 3.1 regression tests — persistent source indexing.

Ye tests **offline** chalte hain (dummy embeddings + local Qdrant), aur un cheezon
ko lock karte hain jo asli production problems thi:

  1. **Dedup** — same content ke liye `content_hash` stable hai (case/whitespace se
     farq nahi padta), file ke liye byte-hash.
  2. **Traceability** — har vector ke payload mein `source_id` + `chunk_hash` +
     `content_hash` jaate hain ("ye vector kis content ka tha").
  3. **Source-filtered retrieval** — teacher ne jo sources chune hain, retrieval
     sirf unhi par hoti hai (aur kuch na mile to **warning** ke saath fallback).
  4. **Idempotency** — same source dobara ingest karne par duplicate points nahi
     bante (UUID5 point id) — embeddings ek hi baar banti hain.
  5. **OCR honesty** — image ka text na nikal paye to saaf warning (chup-chaap
     khaali index nahi) — aur `sourceIds` list bhi validate hoti hai.
"""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.domains.exams.llm.services import config_to_source
from app.domains.exams.rag import ocr, store
from app.domains.exams.rag.embeddings import embed_text
from app.domains.exams.rag.extract import extract_source
from app.domains.exams.rag.hashing import (
    chunk_hash,
    content_hash,
    file_hash,
    normalise_text,
)
from app.domains.exams.rag.ingest import ingest_source
from app.domains.exams.rag.retriever import context_pack

# ------------------------------------------------------------
# Hashing — dedup ka asli key
# ------------------------------------------------------------


def test_content_hash_ignores_case_and_whitespace() -> None:
    """Same notes "alag" spelling se save hon to dedup kaam kare."""
    assert normalise_text("  Micro  Organisms\n\nCh 2 ") == "micro organisms ch 2"
    assert content_hash("D", "Notes  about   Curd") == content_hash(
        "d", "notes about curd"
    )
    # ...par alag content alag hash deta hai (warna dedup galat source reuse karta)
    assert content_hash("D", "notes about curd") != content_hash(
        "D", "notes about yeast"
    )


def test_file_hash_is_byte_exact() -> None:
    """Upload ka hash bytes par — ek byte ka farq naya source banata hai."""
    assert file_hash(b"PDF-BYTES") == file_hash(b"PDF-BYTES")
    assert file_hash(b"PDF-BYTES") != file_hash(b"pdf-bytes")


def test_chunk_hash_is_content_bound() -> None:
    """Chunk-level traceability: same text → same hash, badla text → naya hash."""
    assert chunk_hash("Curd is made by Lactobacillus") == chunk_hash(
        "curd   is made by LACTOBACILLUS"
    )
    assert chunk_hash("Curd is made by Lactobacillus") != chunk_hash(
        "Bread rises because of Yeast"
    )


# ------------------------------------------------------------
# Vector store + ingest + retrieval (local Qdrant, dummy embeddings)
# ------------------------------------------------------------


@pytest.fixture()
def local_vector_store(tmp_path, monkeypatch):
    """Qdrant ko temp folder par point karo (local persistent mode) + cache clear."""
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
        store.get_client().close()
    except Exception:  # pragma: no cover - cleanup best effort
        pass
    store.get_client.cache_clear()


_NOTES = (
    "Microorganisms are tiny living organisms. Yeast is a fungus used in making "
    "bread. Bacteria called Lactobacillus convert milk into curd."
)
_OTHER = (
    "Coal is a fossil fuel formed from dead plants. Petroleum is refined into "
    "petrol and diesel. Coal and petroleum are exhaustible resources."
)


def _paper(sources: list[dict] | None = None, chapters: list[str] | None = None):
    return config_to_source(
        {
            "title": "Unit Test",
            "total_marks": 10,
            "class_name": "8",
            "subject": "Science",
            "chapters": chapters or ["Microorganisms"],
            "blueprint": [{"type": "MCQ", "count": 10, "marksEach": 1}],
            "sources": sources or [],
        }
    )


def test_ingest_payload_keeps_source_and_chunk_traceability(local_vector_store) -> None:
    """Har point ka jawab: kis source ka, kis chunk ka, kis content hash ka."""
    digest = content_hash("text", _NOTES)
    result = ingest_source(
        {"sourceType": "D", "label": "My Science notes", "textExcerpt": _NOTES},
        source_id=301,
        class_name="8",
        subject="Science",
        board="CBSE",
        chapters=["Microorganisms"],
        label="My Science notes",
        content_hash=digest,
        subject_id=7,
        class_id=3,
    )

    assert result["ok"] is True, result
    collection = store.collection_name(None, "chunks")
    found = store.search(
        collection,
        vector=embed_text("curd lactobacillus microorganisms"),
        filters={"source_id": 301},
        limit=5,
        min_score=-1.0,  # dummy embeddings — score ka bharosa nahi, filter ka hai
    )

    assert found, "ingest ke baad source_id filter se points milne chahiye"
    payload = found[0]["payload"]
    assert payload["source_id"] == 301
    assert payload["content_hash"] == digest
    assert payload["chunk_hash"]
    assert payload["chunk_uid"].startswith("src301-c")
    assert payload["subject_id"] == 7
    assert payload["classroom_id"] == 3
    assert payload["chapters"] == ["Microorganisms"]


# ------------------------------------------------------------
# Source-filtered retrieval — "teacher ne jo chuna, wahi padho"
# ------------------------------------------------------------


def _ingest_text(source_id: int, label: str, text: str, chapters: list[str]):
    """Chhota helper: paste-text (Type D) source ingest karo."""
    return ingest_source(
        {"sourceType": "D", "label": label, "textExcerpt": text},
        source_id=source_id,
        class_name="8",
        subject="Science",
        board="CBSE",
        chapters=chapters,
        label=label,
        content_hash=content_hash("text", text),
    )


def test_retrieval_stays_inside_selected_sources(local_vector_store) -> None:
    """Do sources indexed, par teacher ne **ek** chuna → doosre ka content na aaye.

    Yahi guarantee hai: library mein 100 PDF ho sakti hain, retrieval sirf
    **chuni hui** sources par chalti hai (blueprint §1.2.1 G).
    """
    _ingest_text(401, "Science notes", _NOTES, ["Microorganisms"])
    _ingest_text(402, "Coal notes", _OTHER, ["Microorganisms"])

    paper = _paper(
        sources=[{"sourceType": "D", "sourceId": 401, "label": "Science notes"}],
        chapters=["Microorganisms"],
    )
    pack = context_pack(paper)

    assert pack["used_rag"] is True, pack["warnings"]
    assert pack["hits"], "selected source se chunks milne chahiye"
    assert pack["selected_source_ids"] == [401]

    text = "\n".join(pack["excerpts"])
    assert "Lactobacillus" in text, "chuna hua source retrieval mein aaya"
    assert "Petroleum" not in text, "na chuna hua source leak nahi hona chahiye"


def test_multi_file_source_ids_list_is_honoured(local_vector_store) -> None:
    """Ek item par kai files (`sourceIds` list) → saare ids filter mein aayein."""
    _ingest_text(411, "Notes A", _NOTES, ["Microorganisms"])
    _ingest_text(412, "Notes B", _OTHER, ["Microorganisms"])

    paper = _paper(
        sources=[{"sourceType": "B", "sourceIds": [411, 412], "label": "2 images"}],
        chapters=["Microorganisms"],
    )
    pack = context_pack(paper)

    assert set(pack["selected_source_ids"]) == {411, 412}
    text = "\n".join(pack["excerpts"])
    assert "Lactobacillus" in text, "pehla id ka content aana chahiye"
    assert "Petroleum" in text, "`sourceIds` list ka doosra id bhi honour hona chahiye"


# ------------------------------------------------------------
# Idempotency + delete (stale vectors kabhi retrieve na hon)
# ------------------------------------------------------------


def test_reingest_same_source_does_not_duplicate_points(local_vector_store) -> None:
    """Idempotency: same source dobara ingest → wahi points (UUID5), duplicate nahi.

    Isse embeddings dobara paise/time nahi khaati, aur search mein same chunk
    do baar nahi aata (jo prompt ko bekaar bhar deta hai).
    """
    collection = store.collection_name(None, "chunks")

    first = _ingest_text(501, "Notes", _NOTES, ["Microorganisms"])
    assert first["ok"] is True, first
    after_first = store.collection_stats(collection)["points"]
    assert after_first > 0

    second = _ingest_text(501, "Notes", _NOTES, ["Microorganisms"])
    assert second["ok"] is True, second
    after_second = store.collection_stats(collection)["points"]

    assert after_first == after_second, "re-ingest se duplicate points ban gaye"


def test_deleted_source_is_no_longer_retrievable(local_vector_store) -> None:
    """Delete → vectors gone: deleted source ka content kabhi retrieve na ho."""
    collection = store.collection_name(None, "chunks")
    _ingest_text(601, "Notes", _NOTES, ["Microorganisms"])

    def _search() -> list[dict]:
        return store.search(
            collection,
            vector=embed_text("lactobacillus curd"),
            filters={"source_id": 601},
            limit=5,
            min_score=-1.0,  # dummy embeddings — filter ka test hai, score ka nahi
        )

    assert _search(), "delete se pehle points milne chahiye"

    store.delete_by_source(collection, 601)

    assert _search() == [], "deleted source ke vectors ab retrieve nahi hone chahiye"


# ------------------------------------------------------------
# OCR honesty + `sourceIds` validation
# ------------------------------------------------------------


def test_image_without_ocr_reports_warning_not_silence(tmp_path, monkeypatch) -> None:
    """Image ka text na nikal paye to **saaf warning** (chup-chaap khaali index nahi)."""
    monkeypatch.setattr(settings, "OCR_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path), raising=False)

    assert ocr.provider() == "none"
    assert ocr.is_enabled() is False

    # (a) File hi nahi mili (storageKey / upload path galat)
    missing = extract_source(
        {"sourceType": "B", "label": "diagram", "fileName": "nope.png"}
    )
    assert missing["kind"] == "image"
    assert missing["pages"] == []
    assert any("Image file nahi mili" in w for w in missing["warnings"])

    # (b) File maujood hai par OCR off → `ocr_image` warning deta hai, raise nahi
    image = tmp_path / "diagram.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-image")
    text, warnings = ocr.ocr_image(image)
    assert text == ""
    assert warnings and "OCR off" in warnings[0]

    # extract_source bhi crash na kare, aur warning ke bina aage na badhe
    extracted = extract_source(
        {"sourceType": "B", "label": "diagram", "fileName": image.name}
    )
    assert extracted["pages"] == []
    assert extracted["warnings"], "OCR off hone par chup-chaap skip nahi hona chahiye"


def test_paper_source_ids_flattens_source_ids_list() -> None:
    """`sourceIds` (multi-file list) ints mein flatten ho; pattern/local ids skip."""
    from app.domains.exams.service import paper_source_ids

    paper = SimpleNamespace(
        sources=[
            {"kind": "knowledge", "sourceIds": [11, 12]},  # multi-file upload
            {"kind": "pattern", "sourceId": 99},  # pattern-only → retrieve nahi
            {"kind": "knowledge", "sourceId": "src-local-1"},  # offline id → skip
            {"kind": "knowledge", "sourceId": 13, "sourceIds": [12, 14]},  # dedup
        ]
    )

    assert paper_source_ids(paper) == [11, 12, 13, 14]
