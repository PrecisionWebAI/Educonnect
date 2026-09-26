"""B3 tests — LangGraph paper-generation DAG (`llm/graph.py`).

Ye tests **LLM aur DB dono ke bina** chalte hain:
  · `generate_section` fake se replace (per-batch output hum control karte hain)
  · `build_sources` fake (RAG/Qdrant ko touch hi nahi karte — woh `test_exams_rag.py`)
  · `run_paper_graph(llm=...)` mein fake judge inject

Har test us ek production behaviour par hai jo pehle "code ke andar chhupa" tha:
fan-out (parallel batches), blueprint order, bounded repair, aur guard (0 budget).
"""

import pytest

from app.domains.exams.llm import graph as paper_graph
from app.domains.exams.llm import services as llm_services
from app.domains.exams.llm.services import (
    QualityIssue,
    QualityReport,
    config_to_source,
)

# 4 MCQ (1 mark) + 2 Short (2 marks) = 8 marks ka chhota paper
TOTAL_MARKS = 8
BLUEPRINT = [
    {"type": "MCQ", "count": 4, "marksEach": 1},
    {"type": "Short", "count": 2, "marksEach": 2},
]
BASE_CONFIG = {
    "title": "Unit Test 1 — Science",
    "total_marks": TOTAL_MARKS,
    "duration_minutes": 45,
    "class_name": "8",
    "subject": "Science",
    "exam_type": "Unit Test",
    "language": "English",
    "chapters": ["Microorganisms"],
    "blueprint": BLUEPRINT,
    "coverage_mode": "marks",
    "coverage_plan": {
        "mode": "marks",
        "chapters": [{"chapter": "Microorganisms", "targetMarks": TOTAL_MARKS}],
    },
    "part_b": [],
    "sources": [],
    "instructions": ["Use simple English."],
    "constraints": {"noDuplicates": True},
}

COVERAGE_PLAN = BASE_CONFIG["coverage_plan"]

# Text stems — har index par alag (duplicate-detector se bachne ke liye)
_STEMS = [
    "Explain how bacteria help in turning milk into curd today",
    "Which microorganism spreads malaria in tropical regions",
    "Describe what happens during fermentation of dough",
    "Why is salt used to preserve pickles for months",
    "How do yeast cells release energy without any oxygen",
    "Name two human diseases that are caused by viruses",
    "What work do nitrogen fixing bacteria do in soil",
    "How does a vaccine train the immune system of kids",
]


def _paper(**overrides: object):
    return config_to_source({**BASE_CONFIG, **overrides})


def _stem_for(slot: dict, index: int) -> str:
    """Slot ki position se text chuno — **poora paper** unique rahe.

    `slot_id` = "Q1".."Q6" (planner yahi deta hai), isliye per-type index par
    bharosa nahi karte (warna MCQ 1 aur Short 1 ka text same ho jata —
    duplicate detector phir theek hi pakadta).
    """
    sid = str(slot.get("slot_id") or "")
    num = int(sid[1:]) if sid[1:].isdigit() else index + 1
    return _STEMS[(num - 1) % len(_STEMS)]


def _question(slot: dict, qtype: str, index: int) -> dict:
    """Ek complete question — `_merge_slots` ke output ka same shape.

    Texts jaan-boojh kar ekdum alag rakhe hain: `rule_checks` token-overlap
    (jaccard >= 0.8) ko duplicate maanta hai — "sawaal 1/2/3" jaise texts
    asli duplicate hi hote hain.
    """
    is_mcq = qtype in ("MCQ", "MultipleSelect")
    stem = _stem_for(slot, index)
    return {
        "id": str(slot.get("slot_id") or f"Q{index + 1}").lower(),
        "type": qtype,
        "marks": int(slot.get("marks") or 1),
        "difficulty": slot.get("difficulty") or "Medium",
        "bloom": slot.get("bloom") or "Understand",
        "chapter": slot.get("chapter") or "",
        "topic": slot.get("topic") or "",
        "hasImage": bool(slot.get("has_image")),
        "origin": "ai",
        "locked": False,
        "text": stem,
        "answer": "one" if is_mcq else "Expected key points.",
        "options": ["A) one", "B) two", "C) three", "D) four"] if is_mcq else [],
        "markingScheme": "1 mark",
        "sourceRefs": [],
        "incomplete": False,
    }


def _fill_all(qtype: str, slots: list[dict]) -> list[dict]:
    return [_question(slot, qtype, i) for i, slot in enumerate(slots)]


def _install_fake_section(monkeypatch: pytest.MonkeyPatch, produce):
    """`generate_section` ko fake se badlo — **dono** modules mein.

    ⚠️ Dono jagah patch karna zaroori hai: graph ke `generate` node aur
    `repair_incomplete` (services) apne-apne module namespace se
    `generate_section` uthate hain — sirf ek patch karne se repair waala raasta
    asli LLM par chala jata (test slow/hang).
    """
    calls: list[dict] = []

    def fake_section(**kwargs):
        calls.append(kwargs)
        return produce(kwargs["qtype"], list(kwargs.get("slots") or []))

    monkeypatch.setattr(paper_graph, "generate_section", fake_section)
    monkeypatch.setattr(llm_services, "generate_section", fake_section)
    return calls


@pytest.fixture()
def retrieve_stub(monkeypatch: pytest.MonkeyPatch):
    """RAG (`build_sources`) ko stub karo — ye tests Qdrant ko touch nahi karte."""
    calls: list[dict] = []

    def fake_build_sources(paper, *, plan=None, school_id=None):
        calls.append({"plan": plan, "school_id": school_id})
        return (
            [{"sourceType": "D", "label": "notes", "textExcerpt": "Bacteria..."}],
            ["[notes] Bacteria are single-celled organisms."],
        )

    monkeypatch.setattr(paper_graph, "build_sources", fake_build_sources)
    return calls


# ------------------------------------------------------------
# Fan-out — "parallel batches, par paper ka order barqarar"
# ------------------------------------------------------------


def test_graph_fan_out_generates_every_slot_in_blueprint_order(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    calls = _install_fake_section(monkeypatch, _fill_all)

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        use_judge=False,
    )

    # 2 sections = 2 parallel batches (MCQ 4 + Short 2)
    assert [len(c["slots"]) for c in calls] == [4, 2]
    assert [c["qtype"] for c in calls] == ["MCQ", "Short"]

    questions = final["questions"]
    assert len(questions) == 6
    assert [q["type"] for q in questions] == ["MCQ"] * 4 + ["Short"] * 2
    assert sum(q["marks"] for q in questions) == TOTAL_MARKS

    summary = final["summary"]
    assert summary["question_count"] == 6
    assert summary["expected_count"] == 6
    assert summary["marks_total"] == TOTAL_MARKS
    # Marks Contract: AI 8 + teacher 0 == total 8 ✅ (server-side audit)
    assert summary["contract"] == {
        "ai_marks": TOTAL_MARKS,
        "teacher_marks": 0,
        "total_marks": TOTAL_MARKS,
        "ok": True,
    }
    assert summary["balanced"] is True
    assert summary["incomplete"] == []
    assert summary["failed_batches"] == []
    # Coverage node ne target vs got verify kiya (marks mode)
    assert summary["coverage"] == [
        {
            "chapter": "Microorganisms",
            "target": TOTAL_MARKS,
            "got": TOTAL_MARKS,
            "ok": True,
            "mode": "marks",
        }
    ]
    # Node sequence — judge off hone par seedha finalize
    assert final["nodes_done"] == [
        "plan",
        "guard",
        "retrieve",
        "batches",
        "generate",
        "generate",
        "merge",
        "check",
        "finalize",
    ]


def test_graph_passes_retrieved_context_into_parallel_batches(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    calls = _install_fake_section(monkeypatch, _fill_all)

    paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        use_judge=False,
    )

    assert len(retrieve_stub) == 1  # retrieve node sirf ek baar chala
    for call in calls:
        # ⭐ Yahi wo bug tha jise `Send` payload mein context explicitly bhej kar
        # roka: context ke bina prompt "Class 8 Science" bhool jata hai.
        assert call["ctx"]["class_name"] == "8"
        assert call["ctx"]["subject"] == "Science"
        assert call["ctx"]["chapters"] == ["Microorganisms"]
        assert call["sources"] and call["excerpts"]
        assert call["constraints"] == {"noDuplicates": True}
        assert call["instructions"] == ["Use simple English."]


def test_graph_splits_large_sections_into_batches(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    calls = _install_fake_section(monkeypatch, _fill_all)
    blueprint = [{"type": "MCQ", "count": 5, "marksEach": 1}]

    final = paper_graph.run_paper_graph(
        paper=_paper(blueprint=blueprint, total_marks=5, coverage_plan={}),
        blueprint=blueprint,
        coverage_plan={},
        total_marks=5,
        batch_size=2,  # 5 MCQ → 2 + 2 + 1
        use_judge=False,
    )

    assert [len(c["slots"]) for c in calls] == [2, 2, 1]
    assert [q["id"] for q in final["questions"]] == ["q1", "q2", "q3", "q4", "q5"]
    assert final["nodes_done"].count("generate") == 3


def test_graph_handles_many_batches_without_recursion_limit_error(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    """40 batches — LangGraph ka default recursion_limit (25) yahan toot jata tha."""
    calls = _install_fake_section(monkeypatch, _fill_all)
    blueprint = [{"type": "MCQ", "count": 40, "marksEach": 1}]

    final = paper_graph.run_paper_graph(
        paper=_paper(blueprint=blueprint, total_marks=40, coverage_plan={}),
        blueprint=blueprint,
        coverage_plan={},
        total_marks=40,
        batch_size=1,  # jaan-boojh kar 40 chhote batches
        use_judge=False,
    )

    assert len(calls) == 40
    assert final["summary"]["question_count"] == 40
    assert final["summary"]["contract"]["ok"] is True
    # 40 generate + 7 fixed nodes (plan, guard, retrieve, batches, merge, check,
    # finalize) = 47 supersteps → default limit 25 par ye GraphRecursionError deta
    assert final["nodes_done"].count("generate") == 40
    assert len(final["nodes_done"]) == 40 + 7


# ------------------------------------------------------------
# Bounded repair loop — "khaali question bache to dobara, par leash ke saath"
# ------------------------------------------------------------


def _fail_short(qtype: str, slots: list[dict]) -> list[dict]:
    # Short section hamesha fail (first pass + repair pass dono) — worst case
    return [] if qtype == "Short" else _fill_all(qtype, slots)


def test_graph_repair_loop_is_bounded_and_keeps_contract_honest(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    _install_fake_section(monkeypatch, _fail_short)

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        repair_passes=1,
        use_judge=False,
    )

    summary = final["summary"]
    # Repair ek hi baar chala — model ne phir bhi kuch nahi diya, to loop ruk gaya
    assert final["nodes_done"].count("repair") == 1
    assert final["nodes_done"].count("check") == 2
    assert summary["failed_batches"] == ["Short 1-2"]
    # Khaali slots **drop nahi** hue — incomplete ke saath paper mein hain
    assert len(summary["incomplete"]) == 2
    assert summary["question_count"] == 4
    assert summary["marks_total"] == 4
    # 4 + 0 != 8 → server ne saaf mana kar diya (silent pass nahi)
    assert summary["contract"]["ok"] is False
    assert summary["balanced"] is False
    assert summary["repaired_count"] == 0


def test_graph_repair_records_repaired_ids_when_model_recovers(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    def produce(qtype: str, slots: list[dict]) -> list[dict]:
        if qtype != "Short":
            return _fill_all(qtype, slots)
        # Pehli koshish fail; repair waale slot (`repair=True`) par model chala
        repaired = any(s.get("repair") for s in slots)
        return _fill_all(qtype, slots) if repaired else []

    _install_fake_section(monkeypatch, produce)

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        repair_passes=1,
        use_judge=False,
    )

    summary = final["summary"]
    assert final["nodes_done"].count("repair") == 1
    assert summary["repaired_count"] == 2
    assert summary["incomplete"] == []
    assert summary["contract"]["ok"] is True  # repair ke baad contract wapas ✅


def test_graph_skips_repair_when_disabled(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    _install_fake_section(monkeypatch, _fail_short)

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        repair_passes=0,  # ops ne repair band kiya (emergency switch)
        use_judge=False,
    )

    assert "repair" not in final["nodes_done"]
    assert final["nodes_done"].count("check") == 1
    assert len(final["summary"]["incomplete"]) == 2


# ------------------------------------------------------------
# Guard — "0 marks bache to saaf wajah, chup-chaap empty nahi"
# ------------------------------------------------------------


def test_graph_guard_exits_early_with_clear_note(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    calls = _install_fake_section(monkeypatch, _fill_all)

    final = paper_graph.run_paper_graph(
        paper=_paper(part_b=[{"type": "Long", "text": "Big question?", "marks": 8}]),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,  # poore 8 marks teacher ne le liye
        use_judge=False,
    )

    assert final["nodes_done"] == ["plan", "guard", "finalize"]
    assert calls == [] and retrieve_stub == []  # koi LLM/RAG call nahi hui
    assert final["questions"] == []
    summary = final["summary"]
    assert "0 marks bache" in summary["note"]  # frontend ko asli wajah dikhe
    assert summary["question_count"] == 0
    # Marks ka hisaab sahi hai (teacher ke 8 marks hi poora paper hain) — par
    # AI ki taraf se kuch nahi bana, isliye note/`incomplete` se saaf pata chale.
    assert summary["contract"]["ok"] is True
    assert summary["ai_budget"] == 0
    assert summary["warnings"] and "0 marks bache" in summary["warnings"][0]


# ------------------------------------------------------------
# Progress events + checkpoints — "job restart ho to pata chale kahan tha"
# ------------------------------------------------------------


def test_graph_streams_progress_events_and_checkpoints(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    _install_fake_section(monkeypatch, _fill_all)
    events: list[dict] = []
    checkpoints: list[tuple[str, int, dict]] = []

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        use_judge=False,
        on_event=events.append,
        on_checkpoint=lambda node, done, state: checkpoints.append(
            (node, len(done), dict(state))
        ),
    )

    nodes = [e["node"] for e in events]
    assert nodes[0] == "plan" and nodes[-1] == "finalize"
    assert all(isinstance(e.get("stage"), str) and e["stage"] for e in events)
    assert all(0 <= int(e["pct"]) <= 100 for e in events)
    # Batch label progress mein aaya (UI "Writing MCQ 1-4..." dikha sake)
    assert any("MCQ 1-4" in e["stage"] for e in events)
    assert any("Short 1-2" in e["stage"] for e in events)

    # Checkpoints node ke saath badhte hain aur live state ka snapshot dete hain
    assert [c[0] for c in checkpoints] == final["nodes_done"]
    assert [c[1] for c in checkpoints] == list(range(1, len(final["nodes_done"]) + 1))
    last_state = checkpoints[-1][2]
    assert len(last_state["questions"]) == 6
    assert last_state["summary"]["question_count"] == 6


# ------------------------------------------------------------
# Judge node — Layer 2 quality (LLM), optional
# ------------------------------------------------------------


class _FakeJudgeLLM:
    """Judge ka minimal stub (`check_quality` sirf structured output maangta hai)."""

    def __init__(self, issues: list[dict] | None = None) -> None:
        self.issues = issues or []
        self.calls = 0

    def with_structured_output(self, _schema: object) -> _FakeJudgeLLM:
        return self

    def invoke(self, _messages: object) -> QualityReport:
        self.calls += 1
        return QualityReport(issues=[QualityIssue(**issue) for issue in self.issues])


class _BrokenJudge:
    """Judge model down — job phir bhi complete hona chahiye (rules-only)."""

    def with_structured_output(self, _schema: object) -> _BrokenJudge:
        return self

    def invoke(self, _messages: object) -> None:
        raise RuntimeError("judge model down")


def test_graph_judge_node_attaches_quality_report(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    _install_fake_section(monkeypatch, _fill_all)
    judge = _FakeJudgeLLM()

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        use_judge=True,
        llm=judge,
    )

    assert "judge" in final["nodes_done"]
    assert final["nodes_done"].index("judge") < final["nodes_done"].index("finalize")
    assert judge.calls == 1

    report = final["summary"]["quality"]
    assert report["source"] == "rules+judge"
    assert report["verdict"] == "ok"  # koi high severity issue nahi
    assert report["counts"]["high"] == 0


def test_graph_judge_failure_degrades_to_rules_only(
    monkeypatch: pytest.MonkeyPatch, retrieve_stub
) -> None:
    _install_fake_section(monkeypatch, _fill_all)

    final = paper_graph.run_paper_graph(
        paper=_paper(),
        blueprint=BLUEPRINT,
        coverage_plan=COVERAGE_PLAN,
        total_marks=TOTAL_MARKS,
        use_judge=True,
        llm=_BrokenJudge(),
    )

    report = final["summary"]["quality"]
    # Judge down hone par bhi job **fail nahi** hona chahiye — rules ka report mila
    assert report["source"] == "rules"
    assert report["llm_error"] and "judge model down" in report["llm_error"]
    assert final["summary"]["question_count"] == 6
