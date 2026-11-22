"""Exam papers are per section; sections that sit one paper share a group (phase3.md, 3.x).

* a subject **named** on the date sheet becomes one paper per section that already has it,
  all in one shared group (title + chapters by name); a section without it is reported
  back as skipped and nothing is created for it;
* marks and results are per section - a child is marked on their own section's paper;
* the group is **locked** by the first mark or publication (edits are `409`), but any
  section can still be detached to get a paper of its own, chapters matched by name;
* a paper's maximum cannot move under marks already entered;
* another school's group or paper is a `404`.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.academics.models import Chapter
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.exams.models import (
    ExamPaper,
    ExamPaperChapter,
    ExamPaperGroup,
    PaperDraft,
)
from app.domains.academic.classroom.exams.plan import groups, service
from app.domains.academic.classroom.exams.plan.schemas import (
    ExamCreateIn,
    ExamUpdateIn,
    MarkEntryIn,
    MarksSaveIn,
    PaperGroupUpdateIn,
    PaperScheduleIn,
)
from app.domains.admin.platform.models import School
from tests.course_support import ensure_year, section_subject
from tests.test_classroom_exams import (
    TODAY,
    _room,
    _student,
    memory_session,
    seed,
)


def _chapters(session, course, names):
    year = ensure_year(session)
    for number, name in enumerate(names, start=1):
        session.add(
            Chapter(
                classroom_subject_id=course.id,
                academic_year_id=year.id,
                sequence=number,
                name=name,
            )
        )
    session.commit()


def _world(session):
    """9-A and 9-B both have Mathematics (with chapters); only 9-A has Science."""
    data = seed(session)
    courses = {
        course.classroom_id: course
        for course in session.exec(
            select(ClassroomSubject).where(ClassroomSubject.name == "Mathematics")
        ).all()
    }
    data["maths_a"] = data["maths"]
    data["maths_b"] = courses[data["other_room"].id]
    _chapters(session, data["maths_a"], ["Algebra", "Geometry", "Mensuration"])
    _chapters(session, data["maths_b"], ["Algebra", "Geometry"])
    data["nina"] = _student(session, "nina das", "P7-9", data["other_room"])
    return data


def _maths_by_name(**extra) -> PaperScheduleIn:
    values = {
        "subject_name": "Mathematics",
        "exam_date": TODAY,
        "max_marks": Decimal("80"),
        "passing_marks": Decimal("24"),
        "chapters": ["Algebra", "Geometry"],
    }
    values.update(extra)
    return PaperScheduleIn(**values)


def _class_exam(session, data, papers, user=None, status="scheduled"):
    return service.create_exam(
        session,
        ExamCreateIn(
            name="Half Yearly",
            scope="class",
            class_id=data["room"].class_id,
            start_date=TODAY,
            end_date=TODAY + timedelta(days=5),
            status=status,
            papers=papers,
        ),
        user or data["office"],
    )


def _mark(session, data, paper_id, student, score, user=None):
    return service.save_marks(
        session,
        paper_id,
        MarksSaveIn(entries=[MarkEntryIn(student_id=student.id, marks_obtained=score)]),
        user or data["office"],
    )


def test_a_subject_name_becomes_one_paper_per_section_sharing_one_group():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(session, data, [_maths_by_name()])

    assert len(exam.papers) == 2
    assert {paper.classroom_id for paper in exam.papers} == {
        data["room"].id,
        data["other_room"].id,
    }
    group_ids = {paper.paper_group_id for paper in exam.papers}
    assert len(group_ids) == 1 and None not in group_ids
    assert all(paper.title == "Mathematics" for paper in exam.papers)
    assert all(paper.chapters == ["Algebra", "Geometry"] for paper in exam.papers)
    assert [group.chapters for group in exam.groups] == [["Algebra", "Geometry"]]
    assert exam.groups[0].locked is False
    # Each section's own subject is the one its paper hangs from - never a shared one.
    assert {paper.classroom_subject_id for paper in exam.papers} == {
        data["maths_a"].id,
        data["maths_b"].id,
    }
    assert exam.skipped == []


def test_a_section_without_the_subject_is_reported_and_nothing_is_invented():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(
        session,
        data,
        [
            PaperScheduleIn(
                subject_name="Science", exam_date=TODAY, max_marks=Decimal("50")
            )
        ],
    )
    # 9-A has Science, 9-B does not: one paper, no group, and 9-B is named as skipped.
    assert len(exam.papers) == 1 and exam.papers[0].paper_group_id is None
    assert [(item.classroom_id, item.subject) for item in exam.skipped] == [
        (data["other_room"].id, "Science")
    ]
    assert (
        session.exec(select(Chapter).where(Chapter.name == "Science")).first() is None
    )

    with pytest.raises(HTTPException) as nobody:
        _class_exam(
            session,
            data,
            [PaperScheduleIn(subject_name="Chemistry", exam_date=TODAY)],
        )
    assert nobody.value.status_code == 422
    assert "Course tab" in nobody.value.detail


def test_a_single_section_paper_matches_chapters_by_name_or_says_which_are_missing():
    session = memory_session()
    data = _world(session)
    with pytest.raises(HTTPException) as missing:
        _class_exam(
            session,
            data,
            [
                PaperScheduleIn(
                    subject_name="Science",
                    exam_date=TODAY,
                    chapters=["Light", "Sound"],
                )
            ],
        )
    assert missing.value.status_code == 409
    assert "Light" in missing.value.detail and "Sound" in missing.value.detail


def test_marks_and_results_are_per_section_paper():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(session, data, [_maths_by_name()])
    paper_a = next(p for p in exam.papers if p.classroom_id == data["room"].id)
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)

    _mark(session, data, paper_a.id, data["aarav"], Decimal("70"))
    _mark(session, data, paper_b.id, data["nina"], Decimal("60"))

    # A child of the other section is not on this paper's sheet.
    with pytest.raises(HTTPException) as wrong:
        _mark(session, data, paper_a.id, data["nina"], Decimal("10"))
    assert wrong.value.status_code == 422
    assert [
        row.student_id
        for row in service.paper_marks(session, paper_b.id, data["office"])
    ] == [data["nina"].id]

    result = service.results(session, exam.id, data["office"])
    by_student = {row.student_id: row for row in result.rows}
    assert [m.paper_id for m in by_student[data["aarav"].id].marks] == [paper_a.id]
    assert [m.paper_id for m in by_student[data["nina"].id].marks] == [paper_b.id]
    assert {paper.classroom_id for paper in result.papers} == {
        data["room"].id,
        data["other_room"].id,
    }, "a class exam's result sheet has one column per section paper"
    assert all(paper.section for paper in result.papers)
    # Ranks are per section: each section's only scorer is first in their own section.
    assert by_student[data["aarav"].id].rank == 1
    assert by_student[data["nina"].id].rank == 1


def test_the_first_mark_locks_the_group_but_a_section_can_still_be_detached():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(session, data, [_maths_by_name()])
    group = exam.groups[0]
    paper_a = next(p for p in exam.papers if p.classroom_id == data["room"].id)
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)

    # Before any mark the shared paper is editable, and the edit reaches every row.
    edited = service.update_group(
        session,
        group.id,
        PaperGroupUpdateIn(
            display_title="Maths (Half Yearly)",
            chapters=["Algebra", "Geometry"],
            max_marks=Decimal("100"),
        ),
        data["office"],
    )
    assert edited.display_title == "Maths (Half Yearly)" and edited.locked is False
    refreshed = service.read_exam(session, exam.id, data["office"])
    assert {paper.max_marks for paper in refreshed.papers} == {Decimal("100.00")}
    assert {paper.title for paper in refreshed.papers} == {"Maths (Half Yearly)"}

    _mark(session, data, paper_a.id, data["aarav"], Decimal("70"))
    assert groups.is_locked(session, group.id) is True
    with pytest.raises(HTTPException) as locked:
        service.update_group(
            session,
            group.id,
            PaperGroupUpdateIn(display_title="Changed"),
            data["office"],
        )
    assert locked.value.status_code == 409

    # Detaching is still allowed: 9-B gets its own paper, 9-A keeps the shared one.
    detached = service.detach_paper(session, group.id, paper_b.id, data["office"])
    assert detached.paper_group_id is None
    assert detached.chapters == ["Algebra", "Geometry"]
    assert len(detached.chapter_ids) == 2, "real chapter rows of 9-B's own subject"
    owned = session.exec(
        select(Chapter.classroom_subject_id)
        .join(ExamPaperChapter, ExamPaperChapter.chapter_id == Chapter.id)
        .where(ExamPaperChapter.exam_paper_id == paper_b.id)
    ).all()
    assert set(owned) == {data["maths_b"].id}
    still = session.get(ExamPaper, paper_a.id)
    assert still.paper_group_id == group.id, "the others keep sharing"


def test_detach_names_a_chapter_the_section_does_not_have_and_changes_nothing():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(
        session,
        data,
        [_maths_by_name(chapters=["Algebra", "Geometry", "Mensuration"])],
    )
    group = exam.groups[0]
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)

    with pytest.raises(HTTPException) as missing:
        service.detach_paper(session, group.id, paper_b.id, data["office"])
    assert missing.value.status_code == 409
    assert "Mensuration" in missing.value.detail
    assert session.get(ExamPaper, paper_b.id).paper_group_id == group.id


def test_detach_clones_the_groups_question_paper_draft():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(session, data, [_maths_by_name()])
    group = exam.groups[0]
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)
    session.add(
        PaperDraft(
            title="Half Yearly Maths",
            paper_group_id=group.id,
            classroom_subject_id=data["maths_a"].id,
            subject="Mathematics",
            total_marks=80,
        )
    )
    session.commit()

    service.detach_paper(session, group.id, paper_b.id, data["office"])
    drafts = session.exec(select(PaperDraft)).all()
    assert len(drafts) == 2
    own = next(draft for draft in drafts if draft.exam_paper_id == paper_b.id)
    assert own.paper_group_id is None and own.title == "Half Yearly Maths"
    assert own.classroom_subject_id == data["maths_b"].id
    assert next(d for d in drafts if d.paper_group_id == group.id).exam_paper_id is None


def test_a_maximum_cannot_move_under_marks_and_a_paper_with_marks_cannot_be_dropped():
    session = memory_session()
    data = _world(session)
    exam = _class_exam(
        session,
        data,
        [
            _maths_by_name(),
            PaperScheduleIn(
                classroom_subject_id=data["science"].id,
                exam_date=TODAY,
                max_marks=Decimal("50"),
            ),
        ],
    )
    science = next(
        p for p in exam.papers if p.classroom_subject_id == data["science"].id
    )
    _mark(session, data, science.id, data["aarav"], Decimal("40"))

    with pytest.raises(HTTPException) as moved:
        service.update_exam(
            session,
            exam.id,
            ExamUpdateIn(
                papers=[
                    _maths_by_name(),
                    PaperScheduleIn(
                        classroom_subject_id=data["science"].id,
                        exam_date=TODAY,
                        max_marks=Decimal("60"),
                    ),
                ]
            ),
            data["office"],
        )
    assert moved.value.status_code == 409 and "marks entered" in moved.value.detail

    with pytest.raises(HTTPException) as dropped:
        service.update_exam(
            session, exam.id, ExamUpdateIn(papers=[_maths_by_name()]), data["office"]
        )
    assert dropped.value.status_code == 409
    assert session.get(ExamPaper, science.id) is not None


def test_a_teacher_may_plan_only_the_subjects_they_hold_in_every_section():
    session = memory_session()
    data = _world(session)
    # Meera holds Mathematics in 9-A only: a name row also covers 9-B, which she does not hold.
    with pytest.raises(HTTPException) as refused:
        _class_exam(session, data, [_maths_by_name()], user=data["meera"])
    assert refused.value.status_code == 403

    own = _class_exam(
        session,
        data,
        [
            PaperScheduleIn(
                classroom_subject_id=data["maths_a"].id,
                exam_date=TODAY,
                max_marks=Decimal("25"),
                chapter_ids=[
                    chapter.id
                    for chapter in session.exec(
                        select(Chapter).where(
                            Chapter.classroom_subject_id == data["maths_a"].id
                        )
                    ).all()
                ][:2],
            )
        ],
        user=data["meera"],
    )
    assert own.papers[0].can_edit is True and own.papers[0].paper_group_id is None
    assert len(own.papers[0].chapter_ids) == 2


def test_another_schools_group_and_paper_are_a_404():
    session = memory_session()
    data = _world(session)
    mine = session.info["school_id"]

    other = School(name="Other school", code="OTH-1", email="oth@test")
    session.add(other)
    session.commit()
    session.refresh(other)
    session.info["school_id"] = other.id
    group = ExamPaperGroup(exam_id=data["school"].id, school_id=other.id)
    session.add(group)
    session.commit()
    session.refresh(group)
    session.info["school_id"] = mine

    with pytest.raises(HTTPException) as edit:
        service.update_group(
            session, group.id, PaperGroupUpdateIn(display_title="x"), data["office"]
        )
    assert edit.value.status_code == 404
    with pytest.raises(HTTPException) as detach:
        service.detach_paper(session, group.id, data["school"].id, data["office"])
    assert detach.value.status_code == 404


def test_the_date_sheet_read_uses_a_fixed_number_of_queries():
    from sqlalchemy import event

    session = memory_session()
    data = _world(session)
    exam = _class_exam(session, data, [_maths_by_name()])

    def count(exam_id) -> int:
        seen: list[str] = []
        engine = session.get_bind()

        def on_execute(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)

        event.listen(engine, "before_cursor_execute", on_execute)
        try:
            service.read_exam(session, exam_id, data["office"])
        finally:
            event.remove(engine, "before_cursor_execute", on_execute)
        return len(seen)

    service.read_exam(session, exam.id, data["office"])  # warm one-off lookups
    two_sections = count(exam.id)

    # Eight more sections, each with Mathematics: the read must not grow.
    for letter in "CDEFGHIJ":
        room = _room(session, "Class 9", letter, 9)
        section_subject(session, room.id, "Mathematics", code="MATH")
    bigger = _class_exam(session, data, [_maths_by_name(chapters=[])])
    assert len(bigger.papers) == 10
    service.read_exam(session, bigger.id, data["office"])
    ten_sections = count(bigger.id)
    assert ten_sections == two_sections, f"{two_sections} vs {ten_sections} statements"
