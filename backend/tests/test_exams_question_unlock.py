"""Unlock gate + scoped regeneration (one job, unlocked ids only).

Covers the rule the teacher actually asked for:

    "to change a question you must first unlock it, and if two questions are
     unlocked and you regenerate, ONLY those two change"

So three things are asserted here:
  · a locked question refuses every change except the unlock itself
  · a bulk regeneration queues exactly the unlocked ids and nothing else
  · taking a question over moves it to part_b as a teacher question, keeping
    the marks total (and therefore the Marks Contract) untouched

DB-less: the repository is stubbed, so the focus stays on guard + filter logic.
"""

from types import SimpleNamespace

import pytest

from app.domains.exams import service
from app.domains.exams.schemas import QuestionPatch, QuestionTakeoverRequest


def _q(
    qid: str,
    marks: int = 2,
    locked: bool = False,
    origin: str = "ai",
    **extra: object,
) -> dict:
    """One question dict in the stored JSONB shape."""
    return {
        "id": qid,
        "type": "Short",
        "text": f"Question {qid}",
        "answer": f"Answer {qid}",
        "marks": marks,
        "difficulty": "Medium",
        "bloom": "Understand",
        "chapter": "Microorganisms",
        "topic": "Bacteria",
        "locked": locked,
        "origin": origin,
        **extra,
    }


def _paper(part_a: list, part_b: list | None = None, total_marks: int = 10):
    return SimpleNamespace(
        id=7,
        part_a=part_a,
        part_b=part_b or [],
        coverage_plan={},
        blueprint=[{"type": "Short", "count": 2, "marksEach": 2}],
        total_marks=total_marks,
    )


@pytest.fixture()
def stub_repo(monkeypatch):
    """Stub the repository so the guards can be tested without a database."""
    created: list[dict] = []
    updated: list[dict] = []

    def fake_create(_session, **kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=101, graph_state=kwargs.get("graph_state"))

    def fake_update(_session, paper, data):
        updated.append(data)
        for key, value in data.items():
            setattr(paper, key, value)
        return paper

    monkeypatch.setattr(service.repository, "create_generation_job", fake_create)
    monkeypatch.setattr(service.repository, "update_paper", fake_update)
    monkeypatch.setattr(
        service.repository, "get_latest_job_by_paper", lambda _s, _p: None
    )
    monkeypatch.setattr(service, "new_trace_id", lambda: "trace-test")

    return SimpleNamespace(created=created, updated=updated, session=object())


def _use_paper(monkeypatch, paper) -> None:
    monkeypatch.setattr(service, "_get_paper_or_404", lambda _s, _p: paper)


# ------------------------------------------------------------
# 1. A locked question refuses every change except the unlock
# ------------------------------------------------------------


def test_locked_question_cannot_be_edited(monkeypatch, stub_repo) -> None:
    """Editing the text of a locked question is refused with `question_locked`."""
    paper = _paper([_q("q1", locked=True), _q("q2")])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.patch_question(
            stub_repo.session, 7, "q1", QuestionPatch(text="teacher rewrote this")
        )

    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == service.ERR_QUESTION_LOCKED
    # the teacher never sees a raw technical string
    assert "q1" not in caught.value.detail["message"]


def test_locked_question_cannot_change_marks(monkeypatch, stub_repo) -> None:
    """Rebalancing marks on a locked question is refused too."""
    paper = _paper([_q("q1", marks=2, locked=True)])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.patch_question(stub_repo.session, 7, "q1", QuestionPatch(mark=5))

    assert caught.value.detail["code"] == service.ERR_QUESTION_LOCKED
    assert stub_repo.updated == []  # nothing was written


def test_unlock_itself_is_allowed_while_locked(monkeypatch, stub_repo) -> None:
    """The unlock toggle must always work, or a locked question is a dead end."""
    paper = _paper([_q("q1", locked=True), _q("q2")])
    _use_paper(monkeypatch, paper)

    service.patch_question(stub_repo.session, 7, "q1", QuestionPatch(locked=False))

    assert stub_repo.updated, "the unlock was not persisted"
    assert paper.part_a[0]["locked"] is False


def test_unlocked_question_can_be_edited(monkeypatch, stub_repo) -> None:
    """Once unlocked, the same edit that was refused before now goes through."""
    paper = _paper([_q("q1", locked=False)])
    _use_paper(monkeypatch, paper)

    service.patch_question(
        stub_repo.session, 7, "q1", QuestionPatch(text="teacher rewrote this")
    )

    assert paper.part_a[0]["text"] == "teacher rewrote this"


# ------------------------------------------------------------
# 2. Bulk regeneration touches ONLY the unlocked ids given
# ------------------------------------------------------------


def test_bulk_regeneration_queues_only_unlocked_ids(monkeypatch, stub_repo) -> None:
    """Two unlocked questions regenerate; the locked one is reported, not touched."""
    paper = _paper([_q("q1"), _q("q2", locked=True), _q("q3")])
    _use_paper(monkeypatch, paper)

    _job, queued, skipped_locked, skipped_unknown = service.enqueue_bulk_regeneration(
        stub_repo.session, 7, ["q1", "q2", "q3"]
    )

    assert queued == ["q1", "q3"]
    assert skipped_locked == ["q2"]
    assert skipped_unknown == []
    # ONE job for both questions, targeting exactly the unlocked ids
    assert len(stub_repo.created) == 1
    assert stub_repo.created[0]["graph_state"]["qids"] == ["q1", "q3"]
    assert stub_repo.created[0]["graph_state"]["kind"] == service.KIND_QUESTION


def test_bulk_regeneration_ignores_questions_not_asked_for(
    monkeypatch, stub_repo
) -> None:
    """A question nobody selected is never in the job — no cascading changes."""
    paper = _paper([_q("q1"), _q("q2"), _q("q3"), _q("q4")])
    _use_paper(monkeypatch, paper)

    _job, queued, _locked, _unknown = service.enqueue_bulk_regeneration(
        stub_repo.session, 7, ["q2", "q4"]
    )

    assert queued == ["q2", "q4"]
    assert "q1" not in stub_repo.created[0]["graph_state"]["qids"]
    assert "q3" not in stub_repo.created[0]["graph_state"]["qids"]


def test_bulk_regeneration_deduplicates_ids(monkeypatch, stub_repo) -> None:
    """The same id sent twice is regenerated once, not twice (no double LLM cost)."""
    paper = _paper([_q("q1"), _q("q2")])
    _use_paper(monkeypatch, paper)

    _job, queued, _l, _u = service.enqueue_bulk_regeneration(
        stub_repo.session, 7, ["q1", "q1", "q1"]
    )

    assert queued == ["q1"]


def test_bulk_regeneration_reports_unknown_ids(monkeypatch, stub_repo) -> None:
    """An id that is not in this paper comes back as `skipped_unknown`."""
    paper = _paper([_q("q1")])
    _use_paper(monkeypatch, paper)

    _job, queued, _locked, skipped_unknown = service.enqueue_bulk_regeneration(
        stub_repo.session, 7, ["q1", "ghost"]
    )

    assert queued == ["q1"]
    assert skipped_unknown == ["ghost"]


def test_bulk_regeneration_409_when_every_target_is_locked(
    monkeypatch, stub_repo
) -> None:
    """Asking to regenerate only locked questions is a 409, with a clear code."""
    paper = _paper([_q("q1", locked=True), _q("q2", locked=True)])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.enqueue_bulk_regeneration(stub_repo.session, 7, ["q1", "q2"])

    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == service.ERR_QUESTION_LOCKED
    assert stub_repo.created == []  # no job was queued


def test_bulk_regeneration_409_when_no_id_matched(monkeypatch, stub_repo) -> None:
    """Nothing matched at all -> `no_targets`, not a silent success."""
    paper = _paper([_q("q1")])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.enqueue_bulk_regeneration(stub_repo.session, 7, ["ghost"])

    assert caught.value.detail["code"] == service.ERR_NO_TARGETS


def test_bulk_regeneration_blocked_while_another_job_runs(
    monkeypatch, stub_repo
) -> None:
    """A running job for the same question is a 409, not a second LLM call."""
    paper = _paper([_q("q1")])
    _use_paper(monkeypatch, paper)
    monkeypatch.setattr(
        service.repository,
        "get_latest_job_by_paper",
        lambda _s, _p: SimpleNamespace(
            id=55,
            status=service.GenerationJobStatus.running,
            graph_state={"kind": service.KIND_QUESTION, "qids": ["q1"]},
        ),
    )

    with pytest.raises(service.HTTPException) as caught:
        service.enqueue_bulk_regeneration(stub_repo.session, 7, ["q1"])

    assert caught.value.detail["code"] == service.ERR_REGENERATION_RUNNING


# ------------------------------------------------------------
# 3. "Write my own" — takeover moves the question to part_b
# ------------------------------------------------------------


def test_takeover_moves_question_to_part_b_as_teacher(monkeypatch, stub_repo) -> None:
    """The AI question leaves part_a and comes back as a Custom question."""
    paper = _paper([_q("q1", marks=4), _q("q2", marks=4)], total_marks=8)
    _use_paper(monkeypatch, paper)

    service.takeover_question(
        stub_repo.session,
        7,
        "q1",
        QuestionTakeoverRequest(text="My own question", answer="My own answer"),
    )

    assert [q["id"] for q in paper.part_a] == ["q2"]
    assert [q["id"] for q in paper.part_b] == ["q1"]
    assert paper.part_b[0]["origin"] == "teacher"
    assert paper.part_b[0]["locked"] is False
    assert paper.part_b[0]["text"] == "My own question"
    assert paper.part_b[0]["answer"] == "My own answer"


def test_takeover_keeps_the_marks_total_intact(monkeypatch, stub_repo) -> None:
    """Marks come from the old slot, so the Marks Contract cannot break."""
    paper = _paper([_q("q1", marks=4), _q("q2", marks=4)], total_marks=8)
    _use_paper(monkeypatch, paper)

    before = sum(int(q["marks"]) for q in paper.part_a)
    service.takeover_question(
        stub_repo.session, 7, "q1", QuestionTakeoverRequest(text="My own question")
    )
    after = sum(int(q["marks"]) for q in paper.part_a) + sum(
        int(q["marks"]) for q in paper.part_b
    )

    assert before == after == 8
    assert paper.part_b[0]["marks"] == 4


def test_takeover_blocked_while_locked(monkeypatch, stub_repo) -> None:
    """Write-my-own is a change, so the question must be unlocked first."""
    paper = _paper([_q("q1", locked=True)])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.takeover_question(
            stub_repo.session, 7, "q1", QuestionTakeoverRequest(text="My own")
        )

    assert caught.value.detail["code"] == service.ERR_QUESTION_LOCKED
    assert stub_repo.updated == []


def test_takeover_of_unknown_question_is_404(monkeypatch, stub_repo) -> None:
    """Unknown id -> `question_not_found`, never a 500."""
    paper = _paper([_q("q1")])
    _use_paper(monkeypatch, paper)

    with pytest.raises(service.HTTPException) as caught:
        service.takeover_question(
            stub_repo.session, 7, "ghost", QuestionTakeoverRequest(text="My own")
        )

    assert caught.value.status_code == 404
    assert caught.value.detail["code"] == service.ERR_QUESTION_NOT_FOUND


# ------------------------------------------------------------
# 4. Professional copy — no technical text ever reaches the teacher
# ------------------------------------------------------------


@pytest.mark.parametrize(
    ("reason", "expected_fragment"),
    [
        ("ValueError: Question 'q1' is locked", "locked"),
        ("LLM unavailable: model not installed", "AI service"),
        ("QuestionNotInPaper: Question 'q1' not found", "could not be found"),
    ],
)
def test_professional_reason_maps_known_conditions(
    reason: str, expected_fragment: str
) -> None:
    assert expected_fragment in service._professional_reason(reason)


def test_professional_reason_never_leaks_internals() -> None:
    """An unknown crash still produces a sentence with no stack-trace words."""
    message = service._professional_reason("KeyError: 'sources' in graph node x")

    assert "KeyError" not in message
    assert "graph node" not in message
    assert message.endswith(".")


# ------------------------------------------------------------
# 5. Helpers — legacy job shape + question lookup
# ------------------------------------------------------------


def test_job_target_qids_supports_both_shapes() -> None:
    """New bulk jobs carry `qids`; jobs queued before this change carry `qid`."""
    assert service._job_target_qids({"qids": ["q1", "q2"]}) == ["q1", "q2"]
    assert service._job_target_qids({"qid": "q9"}) == ["q9"]
    assert service._job_target_qids({}) == []


def test_find_question_searches_part_a_and_part_b() -> None:
    """Lookup works across both parts, and with part_a stored as sections."""
    sections = _paper(
        {"sections": [{"questions": [_q("a1")]}]}, [_q("b1", origin="teacher")]
    )
    assert service._find_question(sections, "a1") is not None
    assert service._find_question(sections, "b1") is not None
    assert service._find_question(sections, "zz") is None


def test_error_helper_always_returns_a_code() -> None:
    """Every guard carries a machine code so the client can pick its own wording."""
    exc = service._error(409, service.ERR_QUESTION_LOCKED, "nope")

    assert exc.status_code == 409
    assert exc.detail == {"code": "question_locked", "message": "nope"}
