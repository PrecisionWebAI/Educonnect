"""Exam module, Phase 10: the whole journey in one test per kind.

schedule -> (syllabus / date sheet) -> marks -> publish -> a correction -> the result, seen by
the class and by each family. Every step goes through the same service functions the routes
call; the single-step rules are pinned in the phase tests, this one only proves they chain.

Runs under pytest.
"""

from tests.exam_helpers import publish
from datetime import date

import pytest
from fastapi import HTTPException
from decimal import Decimal

from app.domains.academic.classroom.exams.plan import overview, school_exam, service
from app.domains.academic.classroom.exams.plan.schemas import (
    SyllabusIn,
    SchoolExamCreateIn,
    SchoolExamRowIn,
)
from tests.test_exam_class_test import heard, world
from tests.test_exam_marks_entry import entry, make_test, save, told

D = Decimal


def test_a_class_test_goes_from_schedule_to_each_familys_result():
    session, data = world()

    # 1. schedule: families of the section hear once
    exam = make_test(session, data)
    paper = exam.papers[0]
    assert len(heard(session, "class_test.scheduled")) == 4

    # 2. nothing published yet: the class sees no test counted, a family sees nothing
    class_view = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    assert class_view.unpublished == 1
    assert all(s.overall.tests_counted == 0 for s in class_view.students)
    family_view = overview.result_overview(session, data["aarav_parent"], "class_test", None)
    assert family_view.tests == []

    # 3. marks entered (one absent, one zero), then published by the teacher
    save(
        session,
        paper.id,
        [entry(data["aarav"], 45), entry(data["kabir"], 0), entry(data["ishaan"], absent=True)],
        data["meera"],
    )
    publish(session, paper.id, data["meera"])
    assert len(told(session, "exam.published", data["aarav_parent"].id)) == 1

    # 4. the saved sheet reads back what was entered
    rows = service.paper_marks(session, paper.id, data["meera"])
    aarav_row = next(r for r in rows if r.student_id == data["aarav"].id)
    assert aarav_row.marks_obtained == D(45)

    # 5. the class view
    class_view = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    assert class_view.unpublished == 0 and len(class_view.tests) == 1
    by_id = {s.student_id: s for s in class_view.students}
    assert by_id[data["aarav"].id].overall.tests_passed == 1
    assert by_id[data["kabir"].id].overall.tests_failed == 1, "zero is a score, and a fail"
    assert by_id[data["ishaan"].id].overall.tests_absent == 1
    assert by_id[data["ishaan"].id].overall.percentage is None

    # 6. each family sees only its own child
    mine = overview.result_overview(session, data["aarav_parent"], "class_test", None)
    assert [s.student_id for s in mine.students] == [data["aarav"].id]
    assert mine.students[0].overall.obtained == D(45)

    # 7. School Exam results stay separate from Class Test results
    other = overview.result_overview(session, data["meera"], "school_exam", data["room"].id)
    assert other.tests == []


def test_a_school_exam_stays_hidden_until_the_sheet_is_published_then_reaches_the_result():
    session, data = world()
    exam = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["maths"].id,
                    exam_date=date(2026, 12, 7),
                    total_marks=D("100"),
                )
            ],
        ),
        data["meera"],
    )
    paper = exam.papers[0]

    # a draft sheet: no family hears, none sees it
    assert heard(session, "school_exam.published") == []
    assert overview.result_overview(
        session, data["aarav_parent"], "school_exam", None
    ).tests == []

    # the syllabus is free text from the subject teacher
    school_exam.set_syllabus(
        session, paper.id, SyllabusIn(syllabus_text="Chapters 1 to 4"), data["meera"]
    )

    # publishing the sheet tells the families; marks follow
    school_exam.publish_date_sheet(session, exam.id, data["meera"])
    assert len(heard(session, "school_exam.published")) == 4

    save(session, paper.id, [entry(data["aarav"], 80), entry(data["kabir"], 20)], data["meera"])
    publish(session, paper.id, data["meera"])

    view = overview.result_overview(session, data["meera"], "school_exam", data["room"].id)
    by_id = {s.student_id: s for s in view.students}
    assert by_id[data["aarav"].id].overall.percentage == D("80.00")
    assert by_id[data["kabir"].id].overall.tests_failed == 1
    mine = overview.result_overview(session, data["kabir_parent"], "school_exam", None)
    assert [s.student_id for s in mine.students] == [data["kabir"].id]


def test_one_date_sheet_can_be_made_for_several_sections_at_once():
    session, data = world()
    rows = [
        SchoolExamRowIn(
            classroom_subject_id=data["maths"].id, exam_date=date(2026, 12, 7), total_marks=D("100")
        ),
        SchoolExamRowIn(
            classroom_subject_id=data["science"].id, exam_date=date(2026, 12, 8), total_marks=D("50")
        ),
    ]
    choices = school_exam.sections_of_class(session, data["room"].id)
    assert {c.classroom_id for c in choices} == {data["room"].id, data["other_room"].id}
    assert next(c for c in choices if c.classroom_id == data["other_room"].id).subjects == [
        "Mathematics"
    ]

    exam = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            section_ids=[data["room"].id, data["other_room"].id],
            exam_type="unit_test",
            rows=rows,
        ),
        data["office"],
    )
    assert exam.classroom_id == data["room"].id
    sheets = service.list_exams(session, data["office"], classroom_id=None)
    by_room = {e.classroom_id: e for e in sheets}
    assert len(by_room[data["room"].id].papers) == 2
    assert len(by_room[data["other_room"].id].papers) == 1, "9-B has no Science: left off"


def test_a_section_with_none_of_the_subjects_stops_the_whole_batch():
    import pytest
    from fastapi import HTTPException

    session, data = world()
    rows = [
        SchoolExamRowIn(
            classroom_subject_id=data["science"].id, exam_date=date(2026, 12, 8), total_marks=D("50")
        )
    ]
    with pytest.raises(HTTPException) as caught:
        school_exam.create_school_exam(
            session,
            SchoolExamCreateIn(
                classroom_id=data["room"].id,
                section_ids=[data["other_room"].id],
                exam_type="unit_test",
                rows=rows,
            ),
            data["office"],
        )
    assert caught.value.status_code == 422
    session.rollback()
    assert service.list_exams(session, data["office"], classroom_id=None) == []


def test_a_class_test_carries_a_free_text_syllabus_that_families_can_read_at_once():
    from app.domains.academic.classroom.exams.plan import class_test
    from app.domains.academic.classroom.exams.plan.schemas import ClassTestUpdateIn

    session, data = world()
    exam = make_test(session, data, syllabus_text="  Chapter 3 and 4, all exercises  ")
    paper = exam.papers[0]
    assert paper.has_syllabus

    read = school_exam.get_syllabus(session, paper.id, data["aarav_parent"])
    assert read.syllabus_text == "Chapter 3 and 4, all exercises" and not read.can_edit

    # changing it tells the families it changed; the same text again tells nobody
    before = len(heard(session, "class_test.updated"))
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(syllabus_text="Chapter 5"), data["meera"]
    )
    assert len(heard(session, "class_test.updated")) == before + 4
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(syllabus_text="Chapter 5"), data["meera"]
    )
    assert len(heard(session, "class_test.updated")) == before + 4

    # cleared with an empty text
    out = class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(syllabus_text=""), data["meera"]
    )
    assert not out.papers[0].has_syllabus


def test_a_date_sheet_is_archived_and_restored_never_deleted_and_families_stop_seeing_it():
    session, data = world()
    exam = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["maths"].id,
                    exam_date=date(2026, 12, 7),
                    total_marks=D("100"),
                )
            ],
        ),
        data["meera"],
    )
    school_exam.publish_date_sheet(session, exam.id, data["meera"])

    # a published sheet cannot be archived: cancel it first (the families are told)
    with pytest.raises(HTTPException) as caught:
        school_exam.archive_school_exam(session, exam.id, data["meera"])
    assert caught.value.status_code == 409 and "Cancel it first" in caught.value.detail
    cancelled = school_exam.cancel_school_exam(session, exam.id, data["meera"])
    assert cancelled.status == "cancelled"
    assert len(heard(session, "school_exam.cancelled")) == 4
    with pytest.raises(HTTPException):
        school_exam.cancel_school_exam(session, exam.id, data["meera"])

    out = school_exam.archive_school_exam(session, exam.id, data["meera"])
    assert out.archived_at is not None
    mine = [e.id for e in service.list_exams(session, data["meera"])]
    assert exam.id in mine, "staff still list it (the screen hides it behind Show archived)"
    assert service.list_exams(session, data["aarav_parent"]) == []

    back = school_exam.archive_school_exam(session, exam.id, data["meera"], archive=False)
    assert back.archived_at is None
    assert [e.id for e in service.list_exams(session, data["aarav_parent"])] == [exam.id]


def test_the_syllabus_can_be_given_to_another_teacher_who_may_then_write_it():
    from app.domains.academic.classroom.exams.plan.schemas import SyllabusIn

    session, data = world()
    exam = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["science"].id,
                    exam_date=date(2026, 12, 8),
                    total_marks=D("50"),
                )
            ],
        ),
        data["meera"],
    )
    paper = exam.papers[0]
    assert paper.syllabus_is_temporary is False

    # the assigned teacher is picked explicitly: not temporary
    out = school_exam.set_syllabus(
        session,
        paper.id,
        SyllabusIn(syllabus_text="Light and sound", by_employee_id=data["employee"].id),
        data["meera"],
    )
    assert out.syllabus_text == "Light and sound"
    read = service.read_exam(session, exam.id, data["meera"]).papers[0]
    assert read.has_syllabus and read.syllabus_by_employee_id == data["employee"].id


def test_the_grade_mode_is_set_when_scheduling_a_class_test_and_a_date_sheet():
    from app.domains.academic.classroom.exams.plan import class_test
    from app.domains.academic.classroom.exams.plan.schemas import ClassTestUpdateIn

    session, data = world()
    plain = make_test(session, data)
    assert plain.papers[0].grade_mode == "na", "NA unless chosen"
    manual = make_test(
        session, data, exam_date=date(2026, 12, 9), grade_mode="manual"
    )
    assert manual.papers[0].grade_mode == "manual"
    out = class_test.update_class_test(
        session, manual.id, ClassTestUpdateIn(grade_mode="auto"), data["meera"]
    )
    assert out.papers[0].grade_mode == "auto"
    with pytest.raises(HTTPException):
        class_test.update_class_test(
            session, manual.id, ClassTestUpdateIn(grade_mode="weird"), data["meera"]
        )

    sheet = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["maths"].id,
                    exam_date=date(2026, 12, 7),
                    total_marks=D("100"),
                    grade_mode="auto",
                ),
                SchoolExamRowIn(
                    classroom_subject_id=data["science"].id,
                    exam_date=date(2026, 12, 8),
                    total_marks=D("50"),
                ),
            ],
        ),
        data["meera"],
    )
    modes = {p.subject.lower(): p.grade_mode for p in sheet.papers}
    assert modes == {"mathematics": "auto", "science": "na"}


def test_a_class_test_is_cancelled_first_and_only_then_archived():
    from app.domains.academic.classroom.exams.plan import class_test

    session, data = world()
    exam = make_test(session, data)
    with pytest.raises(HTTPException) as caught:
        class_test.archive_class_test(session, exam.id, data["meera"])
    assert caught.value.status_code == 409 and "Cancel it first" in caught.value.detail
    class_test.cancel_class_test(session, exam.id, data["meera"])
    out = class_test.archive_class_test(session, exam.id, data["meera"])
    assert out.archived_at is not None
    assert service.list_exams(session, data["aarav_parent"]) == [], "families stop seeing it"
    back = class_test.archive_class_test(session, exam.id, data["meera"], archive=False)
    assert back.archived_at is None
