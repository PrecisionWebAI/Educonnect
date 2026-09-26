"""B1 regression tests — "Generate tab chalna chahiye" ke wo bugs jo use rok rahe the.

Ye tests **DB ke bina** chalte hain (pure functions + fake LLM), kyunki:
  · config/orchestration validation pure logic hai (Pydantic validators)
  · planner/summary/coverage pure functions hain (koi SQL nahi)
  · LLM inject kiya ja sakta hai (`generate_paper_questions(llm=...)`)

Har test ka naam hi batata hai kaun sa production bug pakda gaya tha — jab
kabhi fail ho, turant pata chal jaye ki kya wapas toota hai.
"""

import pytest
from pydantic import ValidationError

from app.domains.exams.llm.generator import GeneratedQuestion, QuestionSet
from app.domains.exams.llm.services import (
    build_ctx,
    config_to_source,
    coverage_report,
    generate_paper_questions,
    plan_for_paper,
    repair_incomplete,
)
from app.domains.exams.schemas import (
    GenerationConfigRequest,
    GenerationRequest,
    PaperDraftCreate,
)

# ------------------------------------------------------------
# Test fixtures — frontend ke asli payload se banaye gaye (draftBody ka shape)
# ------------------------------------------------------------

BASE_CONFIG = {
    "title": "Unit Test 1 — Science",
    "total_marks": 10,
    "duration_minutes": 45,
    "class_name": "8",
    "subject": "Science",
    "exam_type": "Unit Test",
    "language": "English",
    "chapters": ["Microorganisms"],
    "blueprint": [{"type": "MCQ", "count": 10, "marksEach": 1}],
    "coverage_mode": "marks",
    "coverage_plan": {
        "mode": "marks",
        "chapters": [
            {
                "chapter": "Microorganisms",
                "targetMarks": 10,
                "auto": False,
                "topics": [],
            }
        ],
        "totalAllocated": 10,
    },
    "part_b": [],
    "sources": [
        {
            "id": "s1",
            "sourceType": "D",
            "label": "My notes",
            "textExcerpt": "Bacteria are single-celled organisms.",
        }
    ],
    "instructions": ["Use simple English."],
    "scope": {"includeTopics": ["Bacteria"]},
    "constraints": {"noDuplicates": True},
}


class _FakeLLM:
    """LangChain chat model ka minimal stub (sirf `generate_section` ke liye kaafi)."""

    def __init__(self, text: str = "Repaired question?") -> None:
        self.text = text
        self.calls = 0

    def with_structured_output(self, _schema: object) -> _FakeLLM:
        return self

    def invoke(self, _messages: object) -> QuestionSet:
        self.calls += 1
        return QuestionSet(
            questions=[
                GeneratedQuestion(
                    text=self.text,
                    answer="Expected answer.",
                    options=["A) one", "B) two", "C) three", "D) four"],
                    marking_scheme="1 mark for correct option",
                )
            ]
        )


# ------------------------------------------------------------
# Bug 3 — context fields chup-chaap drop ho rahe the (Pydantic extra="ignore")
# ------------------------------------------------------------


def test_paper_config_keeps_frontend_context_fields() -> None:
    payload = PaperDraftCreate(**BASE_CONFIG)
    data = payload.model_dump()

    # Ye 6 fields pehle gayab ho jaate the — isliye LLM ko class/chapter ka
    # pata hi nahi hota tha aur generic question banata tha.
    assert data["class_name"] == "8"
    assert data["subject"] == "Science"
    assert data["chapters"] == ["Microorganisms"]
    assert data["sources"][0]["textExcerpt"].startswith("Bacteria")
    assert data["instructions"] == ["Use simple English."]
    assert data["scope"] == {"includeTopics": ["Bacteria"]}
    assert data["constraints"] == {"noDuplicates": True}


# ------------------------------------------------------------
# Bug 1 + 2 — frontend ka {paper_id, force} 422/AttributeError de raha tha
# ------------------------------------------------------------


def test_generation_request_accepts_frontend_body() -> None:
    request = GenerationRequest(paper_id=7, force=True)

    assert request.paper_id == 7
    assert request.force is True  # pehle ye field hi nahi thi → AttributeError (500)
    assert request.total_marks is None  # pehle required thi → 422
    assert request.blueprint is None


def test_generation_request_still_checks_override_marks_contract() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            paper_id=1,
            total_marks=20,
            blueprint=[{"type": "MCQ", "count": 5, "marksEach": 1}],  # 5 != 20
        )


# ------------------------------------------------------------
# Server-side rules (Marks Contract + coverage cap) — dono endpoints par same
# ------------------------------------------------------------


def test_marks_contract_validator_rejects_mismatch() -> None:
    bad = {**BASE_CONFIG, "total_marks": 12}  # blueprint total 10 != 12
    with pytest.raises(ValidationError):
        GenerationConfigRequest(**bad)
    with pytest.raises(ValidationError):
        PaperDraftCreate(**bad)


def test_coverage_cap_validator_marks_and_percent_modes() -> None:
    over = {
        **BASE_CONFIG,
        "coverage_plan": {
            "mode": "marks",
            "chapters": [
                {"chapter": "Microorganisms", "targetMarks": 8, "topics": []},
                {"chapter": "Coal & Petroleum", "targetMarks": 8, "topics": []},
            ],
            "totalAllocated": 16,  # cap 10 → reject
        },
    }
    with pytest.raises(ValidationError):
        GenerationConfigRequest(**over)
    percent_ok = {
        **BASE_CONFIG,
        "coverage_mode": "percent",
        "coverage_plan": {
            "mode": "percent",
            "chapters": [
                {"chapter": "Microorganisms", "targetMarks": 100, "topics": []}
            ],
            "totalAllocated": 100,
        },
    }
    assert GenerationConfigRequest(**percent_ok).coverage_mode.value == "percent"


# ------------------------------------------------------------
# Stateless (Option A) — config se "paper jaisa" object, pipeline wahi
# ------------------------------------------------------------


def test_config_to_source_feeds_prompt_context() -> None:
    ctx = build_ctx(config_to_source(BASE_CONFIG))

    assert ctx["class_name"] == "8"
    assert ctx["subject"] == "Science"
    assert ctx["chapters"] == ["Microorganisms"]
    assert ctx["exam_type"] == "Unit Test"
    assert ctx["instructions"] == ["Use simple English."]
    assert ctx["total_marks"] == 10
    # Difficulty/Bloom mix .env se aata hai (deterministic rotation ka input)
    assert len(ctx["difficulty_mix"]) == 3
    assert len(ctx["bloom_mix"]) == 4


def test_plan_respects_ai_budget_after_teacher_questions() -> None:
    # Teacher ke 2 custom questions = 4 marks → AI budget 6 (total 10)
    cfg = {
        **BASE_CONFIG,
        "part_b": [
            {"type": "Short", "text": "Q1?", "marks": 2},
            {"type": "Short", "text": "Q2?", "marks": 2},
        ],
    }
    paper = config_to_source(cfg)
    plan = plan_for_paper(paper)

    assert plan["ai_budget"] == 6
    assert plan["final_marks"] == 6  # slots budget par trim/ fill hote hain
    assert plan["balanced"] is True
    assert len(plan["slots"]) == 6


def test_zero_ai_budget_returns_clear_note_not_silent_empty() -> None:
    # Teacher ne poora 10 marks khud le liye → AI ke liye 0 bacha.
    # Pehle ye chup-chaap "0 questions, done" deta tha.
    cfg = {
        **BASE_CONFIG,
        "part_b": [{"type": "Long", "text": "Big question?", "marks": 10}],
    }
    result = generate_paper_questions(config_to_source(cfg))

    assert result["questions"] == []
    assert "0 marks bache" in result["summary"]["note"]
    assert result["summary"]["repaired_count"] == 0


# ------------------------------------------------------------
# Coverage audit (server-side) + bounded repair
# ------------------------------------------------------------


def test_coverage_report_marks_mode_flags_shortfall() -> None:
    plan = {
        "mode": "marks",
        "chapters": [{"chapter": "Microorganisms", "targetMarks": 6}],
    }

    ok_rows = coverage_report(
        plan,
        [
            {"chapter": "Microorganisms", "marks": 4},
            {"chapter": "Microorganisms", "marks": 2},
        ],
    )
    short_rows = coverage_report(plan, [{"chapter": "Microorganisms", "marks": 3}])

    assert ok_rows[0]["ok"] is True and ok_rows[0]["got"] == 6
    assert short_rows[0]["ok"] is False and short_rows[0]["got"] == 3


def test_coverage_report_auto_mode_is_a_single_informational_row() -> None:
    rows = coverage_report(
        {"mode": "auto", "chapters": []}, [{"marks": 4}, {"marks": 6}]
    )

    assert len(rows) == 1
    assert rows[0]["chapter"].startswith("Auto")
    assert rows[0]["got"] == 10


def test_repair_incomplete_fills_blank_preserving_marks_contract() -> None:
    llm = _FakeLLM(text="Which organism turns milk into curd?")
    questions = [
        {
            "id": "q1",
            "type": "Short",
            "marks": 4,  # slot se aaya marks — repair ke baad bhi wahi rehna chahiye
            "difficulty": "Medium",
            "bloom": "Understand",
            "chapter": "Microorganisms",
            "topic": "",
            "text": "",  # batch fail hone par aisa hi hota hai
            "answer": "",
            "incomplete": True,
        },
        {
            "id": "q2",
            "type": "Short",
            "marks": 2,
            "chapter": "Microorganisms",
            "text": "Q2?",
        },
    ]

    repaired, repaired_ids = repair_incomplete(
        questions=questions,
        ctx=build_ctx(config_to_source(BASE_CONFIG)),
        sources=BASE_CONFIG["sources"],
        excerpts=["[My notes] Bacteria are single-celled organisms."],
        constraints=BASE_CONFIG["constraints"],
        instructions=BASE_CONFIG["instructions"],
        llm=llm,
        passes=1,
    )

    assert repaired_ids == ["q1"]
    assert repaired[0]["text"] == "Which organism turns milk into curd?"
    assert repaired[0]["incomplete"] is False
    assert repaired[0]["repaired"] is True
    assert repaired[0]["marks"] == 4  # Marks Contract safe
    assert sum(q["marks"] for q in repaired) == 6  # total nahi badla
    assert repaired[1]["text"] == "Q2?"  # healthy question ko chhua nahi gaya
    assert llm.calls == 1  # ek hi chhota call — poora paper dobara nahi bana
