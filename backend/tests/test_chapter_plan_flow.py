"""The chapter list's lifecycle and approved progress.

Teacher adds chapters (Draft) -> submits -> principal approves. Then the teacher saves
Completed / Skipped; the counts move only when the principal approves; finishing chapter
4 while 2 and 3 are pending marks 2 and 3 Skipped.
"""

import pytest
from fastapi import HTTPException

from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.schemas import (
    ChapterCreate,
    ChapterUpdate,
    CourseTeacherAssignIn,
    PlanRejectIn,
    ProgressItemIn,
    ProgressSaveIn,
)
from tests.test_course_chapters import _seed, memory_session


def _setup(session, chapters=5):
    data = _seed(session)
    cs = data["first_row"].classroom_subject_id
    service.assign_teacher(
        session,
        cs,
        CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
        user=data["office"],
    )
    for number in range(1, chapters + 1):
        service.add_chapter(
            session, cs, ChapterCreate(name=f"Unit {number}"), user=data["owner"]
        )
    return data, cs


def _approve_plan(session, data, cs):
    service.submit_chapter_plan(session, cs, user=data["owner"])
    service.approve_chapter_plan(session, cs, user=data["office"])


def _subject(session, data):
    course = service.section_course(session, data["first"].id, user=data["office"])
    return course.subjects[0]


def _save(session, data, cs, *pairs, user=None):
    rows = service.list_chapters(session, cs, user=data["office"])
    by_seq = {row.sequence: row.chapter_id for row in rows}
    return service.save_progress(
        session,
        cs,
        ProgressSaveIn(
            items=[ProgressItemIn(chapter_id=by_seq[n], status=s) for n, s in pairs]
        ),
        user=user or data["owner"],
    )


def _statuses(session, data, cs):
    rows = service.list_chapters(session, cs, user=data["office"])
    return {row.sequence: (row.status, row.proposed_status) for row in rows}


def test_chapters_are_numbered_in_order_and_a_delete_closes_the_gap():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        rows = service.list_chapters(session, cs, user=data["owner"])
        assert [(r.sequence, r.name) for r in rows] == [
            (1, "Unit 1"),
            (2, "Unit 2"),
            (3, "Unit 3"),
        ]
        service.delete_chapter(session, rows[0].chapter_id, user=data["owner"])
        rows = service.list_chapters(session, cs, user=data["owner"])
        assert [(r.sequence, r.name) for r in rows] == [(1, "Unit 2"), (2, "Unit 3")]


def test_an_empty_list_cannot_be_submitted():
    with memory_session() as session:
        data = _seed(session)
        cs = data["first_row"].classroom_subject_id
        with pytest.raises(HTTPException) as empty:
            service.submit_chapter_plan(session, cs, user=data["office"])
        assert empty.value.status_code == 409


def test_a_submitted_list_is_locked_and_only_an_approver_decides():
    with memory_session() as session:
        data, cs = _setup(session, 2)
        service.submit_chapter_plan(session, cs, user=data["owner"])
        subject = _subject(session, data)
        assert subject.chapter_plan_status == "Submitted"
        assert subject.total == 2

        with pytest.raises(HTTPException) as locked:
            service.add_chapter(
                session, cs, ChapterCreate(name="Late"), user=data["owner"]
            )
        assert locked.value.status_code == 409

        with pytest.raises(HTTPException) as teacher:
            service.approve_chapter_plan(session, cs, user=data["owner"])
        assert teacher.value.status_code == 403

        service.reject_chapter_plan(
            session, cs, PlanRejectIn(reason="Add unit 3"), user=data["office"]
        )
        subject = _subject(session, data)
        assert subject.chapter_plan_status == "Draft"
        assert subject.chapter_plan_reject_reason == "Add unit 3"
        service.add_chapter(
            session, cs, ChapterCreate(name="Unit 3"), user=data["owner"]
        )

        _approve_plan(session, data, cs)
        assert _subject(session, data).chapter_plan_status == "Approved"


def test_progress_needs_an_approved_list():
    with memory_session() as session:
        data, cs = _setup(session, 2)
        with pytest.raises(HTTPException) as early:
            _save(session, data, cs, (1, "Completed"))
        assert early.value.status_code == 409


def test_a_save_counts_only_after_the_principal_approves():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        _approve_plan(session, data, cs)

        _save(session, data, cs, (1, "Completed"))
        subject = _subject(session, data)
        assert subject.done == 0 and subject.pending_approval == 1
        assert _statuses(session, data, cs)[1] == ("Pending", "Completed")

        service.approve_progress(session, cs, user=data["office"])
        subject = _subject(session, data)
        assert subject.done == 1 and subject.pending_approval == 0
        assert subject.next_chapter == "Ch 2 · Unit 2"
        assert _statuses(session, data, cs)[1] == ("Completed", None)


def test_finishing_chapter_four_skips_the_ones_left_behind():
    with memory_session() as session:
        data, cs = _setup(session, 5)
        _approve_plan(session, data, cs)

        _save(session, data, cs, (1, "Completed"), (4, "Completed"))
        proposed = {seq: p for seq, (_, p) in _statuses(session, data, cs).items()}
        assert proposed == {
            1: "Completed",
            2: "Skipped",
            3: "Skipped",
            4: "Completed",
            5: None,
        }

        service.approve_progress(session, cs, user=data["office"])
        subject = _subject(session, data)
        assert (subject.done, subject.skipped, subject.total) == (2, 2, 5)
        assert subject.next_chapter == "Ch 5 · Unit 5"

        # A skipped chapter can be completed later; the count moves after approval.
        _save(session, data, cs, (2, "Completed"))
        service.approve_progress(session, cs, user=data["office"])
        subject = _subject(session, data)
        assert (subject.done, subject.skipped) == (3, 1)


def test_a_teacher_can_mark_skipped_and_take_a_save_back():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        _approve_plan(session, data, cs)
        _save(session, data, cs, (1, "Skipped"))
        assert _statuses(session, data, cs)[1] == ("Pending", "Skipped")
        _save(session, data, cs, (1, "Pending"))
        assert _statuses(session, data, cs)[1] == ("Pending", None)

        _save(session, data, cs, (1, "Completed"))
        service.reject_progress(session, cs, user=data["office"])
        assert _subject(session, data).done == 0
        assert _statuses(session, data, cs)[1] == ("Pending", None)


def test_taking_a_completed_chapter_back_needs_approval_and_frees_the_rule_skipped():
    with memory_session() as session:
        data, cs = _setup(session, 5)
        _approve_plan(session, data, cs)
        # Teacher skips 2 on purpose; finishing 4 skips 3 by the rule (and 1).
        _save(session, data, cs, (2, "Skipped"), (4, "Completed"))
        service.approve_progress(session, cs, user=data["office"])
        assert {s: v[0] for s, v in _statuses(session, data, cs).items()} == {
            1: "Skipped",
            2: "Skipped",
            3: "Skipped",
            4: "Completed",
            5: "Pending",
        }

        # Reverting 4 is a proposal: nothing changes until it is approved.
        _save(session, data, cs, (4, "Pending"))
        assert _subject(session, data).done == 1
        proposed = {s: v[1] for s, v in _statuses(session, data, cs).items()}
        assert proposed[4] == "Pending"
        # 1 and 3 were skipped only by the rule, so they go back; 2 was the teacher's
        # own choice and stays skipped.
        assert proposed[1] == "Pending" and proposed[3] == "Pending"
        assert proposed[2] is None

        service.approve_progress(session, cs, user=data["office"])
        assert {s: v[0] for s, v in _statuses(session, data, cs).items()} == {
            1: "Pending",
            2: "Skipped",
            3: "Pending",
            4: "Pending",
            5: "Pending",
        }
        subject = _subject(session, data)
        assert (subject.done, subject.skipped) == (0, 1)


def test_a_chapter_still_between_completed_chapters_stays_skipped():
    with memory_session() as session:
        data, cs = _setup(session, 5)
        _approve_plan(session, data, cs)
        _save(session, data, cs, (2, "Completed"), (5, "Completed"))
        service.approve_progress(session, cs, user=data["office"])
        _save(session, data, cs, (5, "Pending"))
        service.approve_progress(session, cs, user=data["office"])
        # 3 and 4 were skipped by 5; with 5 gone, 2 still ends after... 1 stays skipped.
        statuses = {s: v[0] for s, v in _statuses(session, data, cs).items()}
        assert statuses == {
            1: "Skipped",
            2: "Completed",
            3: "Pending",
            4: "Pending",
            5: "Pending",
        }


def test_a_teacher_cannot_save_for_another_subject_or_approve_their_own_save():
    with memory_session() as session:
        data, cs = _setup(session, 2)
        _approve_plan(session, data, cs)
        _save(session, data, cs, (1, "Completed"))

        with pytest.raises(HTTPException) as other:
            _save(session, data, cs, (2, "Completed"), user=data["outsider"])
        assert other.value.status_code == 403

        with pytest.raises(HTTPException) as nobody_approves:
            service.approve_progress(session, cs, user=data["owner"])
        assert nobody_approves.value.status_code == 403


def test_an_approvers_own_save_also_waits_for_approval():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        _approve_plan(session, data, cs)
        _save(session, data, cs, (2, "Completed"), user=data["office"])
        subject = _subject(session, data)
        assert (subject.done, subject.skipped, subject.pending_approval) == (0, 0, 2)
        service.approve_progress(session, cs, user=data["office"])
        subject = _subject(session, data)
        assert (subject.done, subject.skipped, subject.pending_approval) == (1, 1, 0)


def test_any_change_to_an_approved_list_goes_back_for_approval():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        _approve_plan(session, data, cs)
        assert _subject(session, data).chapter_plan_status == "Approved"

        # Adding, renaming and removing each send the list back to the principal.
        for change in ("add", "rename", "delete"):
            service.approve_chapter_plan(session, cs, user=data["office"]) if (
                _subject(session, data).chapter_plan_status == "Submitted"
            ) else None
            rows = service.list_chapters(session, cs, user=data["owner"])
            if change == "add":
                service.add_chapter(
                    session, cs, ChapterCreate(name="Unit 4"), user=data["owner"]
                )
            elif change == "rename":
                service.update_chapter(
                    session,
                    rows[0].chapter_id,
                    ChapterUpdate(name="Renamed"),
                    user=data["owner"],
                )
            else:
                service.delete_chapter(session, rows[-1].chapter_id, user=data["owner"])
            subject = _subject(session, data)
            assert subject.chapter_plan_status == "Submitted", change
            assert subject.chapter_plan_reapproval is True, change


def test_while_changes_wait_the_teacher_can_keep_editing_and_teaching_but_not_approve():
    with memory_session() as session:
        data, cs = _setup(session, 3)
        _approve_plan(session, data, cs)
        service.add_chapter(
            session, cs, ChapterCreate(name="Unit 4"), user=data["owner"]
        )
        # More edits are fine while the first change waits ...
        service.add_chapter(
            session, cs, ChapterCreate(name="Unit 5"), user=data["owner"]
        )
        assert _subject(session, data).total == 5
        # ... and the approved part keeps being taught.
        _save(session, data, cs, (1, "Completed"))
        assert _subject(session, data).pending_approval == 1
        # Only an approver closes it.
        with pytest.raises(HTTPException) as teacher:
            service.approve_chapter_plan(session, cs, user=data["owner"])
        assert teacher.value.status_code == 403
        service.approve_chapter_plan(session, cs, user=data["office"])
        subject = _subject(session, data)
        assert subject.chapter_plan_status == "Approved"
        assert subject.chapter_plan_reapproval is False


def test_a_first_submission_is_still_locked_while_it_waits():
    with memory_session() as session:
        data, cs = _setup(session, 2)
        service.submit_chapter_plan(session, cs, user=data["owner"])
        with pytest.raises(HTTPException) as locked:
            service.add_chapter(
                session, cs, ChapterCreate(name="Late"), user=data["owner"]
            )
        assert locked.value.status_code == 409


def test_the_line_under_the_subject_name_is_never_empty_once_there_are_chapters():
    with memory_session() as session:
        data, cs = _setup(session, 2)
        _approve_plan(session, data, cs)
        assert _subject(session, data).next_chapter == "Ch 1 · Unit 1"
        _save(
            session, data, cs, (1, "Completed"), (2, "Completed"), user=data["office"]
        )
        service.approve_progress(session, cs, user=data["office"])
        # Everything is closed: it still names the last chapter.
        assert _subject(session, data).next_chapter == "Ch 2 · Unit 2"


def test_while_changes_wait_the_table_keeps_the_last_approved_count():
    with memory_session() as session:
        data, cs = _setup(session, 4)
        _approve_plan(session, data, cs)
        assert _subject(session, data).approved_total is None  # nothing waiting

        service.add_chapter(
            session, cs, ChapterCreate(name="Unit 5"), user=data["owner"]
        )
        service.add_chapter(
            session, cs, ChapterCreate(name="Unit 6"), user=data["owner"]
        )
        waiting = _subject(session, data)
        assert waiting.total == 6  # the edited list
        assert waiting.approved_total == 4  # what the table shows until approval

        service.approve_chapter_plan(session, cs, user=data["office"])
        approved = _subject(session, data)
        assert approved.approved_total is None and approved.total == 6


def test_section_completion_counts_every_chapter_once():
    with memory_session() as session:
        data, cs = _setup(session, 6)  # one subject with 6 chapters
        _approve_plan(session, data, cs)
        _save(
            session, data, cs, (1, "Completed"), (2, "Completed"), user=data["office"]
        )
        service.approve_progress(session, cs, user=data["office"])

        course = service.section_course(session, data["first"].id, user=data["office"])
        assert course.completion_percent == 33.3  # 2 of 6
