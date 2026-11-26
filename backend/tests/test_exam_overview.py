"""Exam module, Phase 6: the result overview.

What these scenarios pin (see `plan/overview.py`):

1. **the formula** - a subject so far is `sum obtained / sum total` (weighted by each test's
   total), not the average of percentages; overall is the same across all subjects; an absent
   child and an unmarked one are left out of both sums, and zero is a score;
2. **one kind at a time** - Class Test and School Exam results are never mixed;
3. **only published tests count** - staff are told how many are still waiting, a family is
   not told they exist;
4. **the class view** - average, highest, lowest, passed and failed per test, absent counted
   apart; each child is judged by **that test's own** pass line;
5. **who sees what** - leadership any section; a teacher only a section they teach in or are
   the class teacher of (`404` otherwise); a student or guardian only their own children,
   with no class figures.

Runs under pytest.
"""

from tests.exam_helpers import publish as publish_filled
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.domains.academic.classroom.exams.plan import (
    class_test,
    overview,
    school_exam,
    service,
)
from app.domains.academic.classroom.exams.plan.schemas import (
    SchoolExamCreateIn,
    SchoolExamRowIn,
)
from tests.test_classroom_exams import _user
from tests.test_exam_class_test import world
from tests.test_exam_marks_entry import entry, make_test, save

D = Decimal


# ---------------------------------------------------------------- helpers


def publish(session, exam, user):
    for paper in exam.papers:
        publish_filled(session, paper.id, user)


def scheduled_with_marks(session, data, *, total, day, marks, subject="maths", user=None, **over):
    """A class test whose marks are saved (not published); `marks` = {student: score|'A'}."""
    exam = make_test(
        session,
        data,
        user=user or data["meera"],
        classroom_subject_id=data[subject].id,
        total_marks=D(str(total)),
        exam_date=day,
        **over,
    )
    entries = [
        entry(data[key], absent=True) if value == "A" else entry(data[key], value)
        for key, value in marks.items()
    ]
    save(session, exam.papers[0].id, entries, user or data["meera"])
    return exam


def student_block(result, student):
    return next(s for s in result.students if s.student_id == student.id)


def subject_line(block, name):
    return next(s for s in block.subjects if s.subject.lower() == name)


@pytest.fixture
def results():
    """Three class tests (two Maths, one Science) all published, in 9-A."""
    session, data = world()
    # Science has no assigned teacher: the office schedules it and names who takes it.
    ct1 = scheduled_with_marks(
        session, data, total=50, day=date(2026, 12, 1),
        marks={"aarav": 45, "kabir": 10, "ishaan": "A"},
    )
    ct2 = scheduled_with_marks(
        session, data, total=20, day=date(2026, 12, 8),
        marks={"aarav": 10, "kabir": 18, "ishaan": 0},
    )
    ct3 = scheduled_with_marks(
        session, data, total=30, day=date(2026, 12, 15), subject="science",
        user=data["office"], taken_by_employee_id=data["employee"].id,
        marks={"aarav": 24, "kabir": 12},
    )
    for exam in (ct1, ct2, ct3):
        publish(session, exam, data["office"])
    return session, data, (ct1, ct2, ct3)


# --------------------------------------------------------------- the formula


def test_a_subject_so_far_is_weighted_by_each_tests_total_not_an_average_of_percentages():
    from app.domains.academic.classroom.exams.plan.overview import Score, fold

    ladder = [{"min_percent": D(0), "grade": "E"}]
    scores = [
        Score("Maths", D(50), D(45), False, True),  # 90%
        Score("Maths", D(20), D(10), False, True),  # 50%
    ]
    subjects, total = fold(scores, ladder)
    assert subjects[0].obtained == D(55) and subjects[0].total == D(70)
    assert subjects[0].percentage == D("78.57"), "55/70, not (90 + 50) / 2 = 70"
    assert total.percentage == D("78.57")


def test_absent_and_unmarked_stay_out_of_the_sums_and_zero_stays_in():
    from app.domains.academic.classroom.exams.plan.overview import Score, fold

    ladder = [{"min_percent": D(0), "grade": "E"}]
    scores = [
        Score("Maths", D(50), None, True, None),  # absent
        Score("Maths", D(50), None, False, None),  # not marked yet
        Score("Maths", D(50), D(0), False, False),  # a real zero
        Score("Science", D(30), D(24), False, True),
    ]
    subjects, total = fold(scores, ladder)
    maths = next(s for s in subjects if s.subject == "Maths")
    assert (maths.obtained, maths.total) == (D(0), D(50))
    assert maths.percentage == D("0.00") and maths.tests_counted == 1
    assert maths.tests_absent == 1
    assert total.obtained == D(24) and total.total == D(80)
    assert (total.tests_passed, total.tests_failed, total.tests_absent) == (1, 1, 1)


def test_a_child_with_nothing_marked_has_no_percentage_at_all():
    from app.domains.academic.classroom.exams.plan.overview import fold

    subjects, total = fold([], [{"min_percent": D(0), "grade": "E"}])
    assert subjects == [] and total.percentage is None and total.grade is None


def test_the_class_view_figures_ignore_the_absent_child():
    from app.domains.academic.classroom.exams.plan.marks_text import Figures
    from app.domains.academic.classroom.exams.plan.overview import stats_of

    found = [
        Figures(D(45), False, D("90.00"), "A1", True),
        Figures(D(10), False, D("20.00"), "E", False),
        Figures(None, True, None, None, None),
    ]
    stats = stats_of(D(50), found)
    assert (stats.marked, stats.absent) == (2, 1)
    assert stats.average_marks == D("27.50") and stats.average_percentage == D("55.00")
    assert (stats.highest, stats.lowest) == (D(45), D(10))
    assert (stats.passed, stats.failed) == (1, 1)
    assert stats_of(D(50), []).marked == 0 and stats_of(D(50), []).average_marks is None


# ------------------------------------------------------------ the class view


def test_the_class_view_has_every_test_and_every_childs_subject_wise_and_overall(results):
    session, data, _ = results
    out = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    assert out.view == "section" and out.kind == "class_test"
    assert len(out.tests) == 3 and out.unpublished == 0

    aarav = student_block(out, data["aarav"])
    assert len(aarav.entries) == 3
    assert subject_line(aarav, "mathematics").percentage == D("78.57")
    assert subject_line(aarav, "science").percentage == D("80.00")
    assert aarav.overall.percentage == D("79.00"), "79 of 100 marks across every test"
    assert aarav.overall.tests_counted == 3

    kabir = student_block(out, data["kabir"])
    # (10 + 18) / (50 + 20) = 40% in Maths; Science 12/30 = 40%; overall 40/100.
    assert subject_line(kabir, "mathematics").percentage == D("40.00")
    assert kabir.overall.percentage == D("40.00")


def test_an_absent_child_is_shown_as_absent_and_kept_out_of_the_percentage(results):
    session, data, (ct1, ct2, _) = results
    out = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    ishaan = student_block(out, data["ishaan"])
    first = next(e for e in ishaan.entries if e.paper_id == ct1.papers[0].id)
    assert first.absent is True and first.obtained is None and first.passed is None
    maths = subject_line(ishaan, "mathematics")
    assert maths.tests_absent == 1
    assert (maths.obtained, maths.total) == (D(0), D(20)), "only the test he sat counts"
    assert maths.percentage == D("0.00"), "a real zero, not an absence"


def test_each_test_shows_the_class_average_highest_lowest_and_pass_fail(results):
    session, data, (ct1, ct2, _) = results
    out = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    column = next(t for t in out.tests if t.paper_id == ct1.papers[0].id)
    stats = column.stats
    # a child with nothing entered is marked absent by the helper so the paper can publish
    assert (stats.marked, stats.absent) == (2, 2)
    assert stats.average_marks == D("27.50") and stats.average_percentage == D("55.00")
    assert (stats.highest, stats.lowest) == (D(45), D(10))
    assert (stats.passed, stats.failed) == (1, 1)

    second = next(t for t in out.tests if t.paper_id == ct2.papers[0].id).stats
    assert (second.marked, second.passed, second.failed) == (3, 2, 1), "the zero fails"


def test_every_child_is_judged_by_that_tests_own_pass_line():
    session, data = world()
    strict = scheduled_with_marks(
        session, data, total=100, day=date(2026, 12, 1), passing_marks=D("60"),
        marks={"aarav": 50},
    )
    lenient = scheduled_with_marks(
        session, data, total=100, day=date(2026, 12, 2), passing_marks=D("40"),
        marks={"aarav": 50},
    )
    publish(session, strict, data["meera"])
    publish(session, lenient, data["meera"])
    out = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    entries = {e.paper_id: e for e in student_block(out, data["aarav"]).entries}
    assert entries[strict.papers[0].id].passed is False
    assert entries[lenient.papers[0].id].passed is True
    assert student_block(out, data["aarav"]).overall.tests_failed == 1


def test_a_test_that_is_not_published_is_counted_for_staff_and_invisible_to_a_family(results):
    session, data, _ = results
    waiting = scheduled_with_marks(
        session, data, total=40, day=date(2026, 12, 20), marks={"aarav": 40}
    )
    staff = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    assert staff.unpublished == 1
    column = next(t for t in staff.tests if t.paper_id == waiting.papers[0].id)
    assert column.published is False and column.stats is None
    assert len(student_block(staff, data["aarav"]).entries) == 3, "not counted anywhere"

    family = overview.result_overview(session, data["aarav_parent"], "class_test", None)
    assert all(t.paper_id != waiting.papers[0].id for t in family.tests)
    assert family.unpublished == 0, "a family never hears of it"


def test_a_cancelled_test_is_not_in_the_results(results):
    session, data, (ct1, _, _) = results
    class_test.cancel_class_test(session, ct1.id, data["meera"])
    out = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    assert len(out.tests) == 2
    aarav = student_block(out, data["aarav"])
    assert subject_line(aarav, "mathematics").percentage == D("50.00"), "only the 10/20"


# ---------------------------------------------------------- one kind at a time


def test_class_test_and_school_exam_results_are_never_mixed(results):
    session, data, _ = results
    sheet = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["maths"].id,
                    exam_date=date(2027, 1, 12),
                    total_marks=D("100"),
                ),
            ],
        ),
        data["meera"],
    )
    save(session, sheet.papers[0].id, [entry(data["aarav"], 70)], data["meera"])
    publish(session, sheet, data["meera"])

    tests = overview.result_overview(session, data["meera"], "class_test", data["room"].id)
    exams = overview.result_overview(session, data["meera"], "school_exam", data["room"].id)
    assert {t.exam_name for t in exams.tests} == {"Unit Test"} and len(exams.tests) == 1
    assert all(t.exam_type == "class_test" for t in tests.tests)

    # The Unit Test's 70/100 is its own: it does not leak into the class-test figures.
    assert student_block(exams, data["aarav"]).overall.percentage == D("70.00")
    assert student_block(tests, data["aarav"]).overall.percentage == D("79.00")


def test_a_kind_that_does_not_exist_is_refused(results):
    session, data, _ = results
    with pytest.raises(HTTPException) as caught:
        overview.result_overview(session, data["meera"], "quiz", data["room"].id)
    assert caught.value.status_code == 422


# -------------------------------------------------------------------- access


def test_leadership_sees_any_section_and_a_teacher_only_their_own(results):
    session, data, _ = results
    for who in (data["principal"], data["office"]):
        out = overview.result_overview(session, who, "class_test", data["other_room"].id)
        assert out.view == "section" and out.tests == []
    assert len(
        overview.result_overview(session, data["principal"], "class_test", data["room"].id).tests
    ) == 3

    # Meera teaches 9-A, not 9-B; and a teacher with no section at all sees nothing.
    for who, room in ((data["meera"], data["other_room"]), (data["outsider"], data["room"])):
        with pytest.raises(HTTPException) as caught:
            overview.result_overview(session, who, "class_test", room.id)
        assert caught.value.status_code == 404


def test_a_family_sees_only_its_own_child_with_no_class_figures(results):
    session, data, _ = results
    out = overview.result_overview(session, data["aarav_parent"], "class_test", None)
    assert out.view == "family"
    assert [s.student_id for s in out.students] == [data["aarav"].id]
    assert all(t.stats is None for t in out.tests), "no class average for a family"
    assert out.students[0].overall.percentage == D("79.00")
    assert subject_line(out.students[0], "mathematics").percentage == D("78.57")


def test_a_student_logging_in_sees_only_themselves(results):
    session, data, _ = results
    login = _user(session, "aarav.login@test")
    data["aarav"].user_id = login.id
    session.add(data["aarav"])
    session.commit()
    out = overview.result_overview(session, login, "class_test", None)
    assert [s.student_id for s in out.students] == [data["aarav"].id]


def test_a_family_cannot_ask_for_a_section_and_a_stranger_has_no_default_view(results):
    session, data, _ = results
    with pytest.raises(HTTPException) as section:
        overview.result_overview(session, data["aarav_parent"], "class_test", data["room"].id)
    assert section.value.status_code == 404
    with pytest.raises(HTTPException) as nothing:
        overview.result_overview(session, data["outsider"], "class_test", None)
    assert nothing.value.status_code == 422


def test_the_response_carries_the_schools_display_mode(results):
    from app.domains.admin.settings import values as setting_values

    session, data, _ = results
    assert overview.result_overview(
        session, data["meera"], "class_test", data["room"].id
    ).display_mode == "both"
    setting_values.set_value(session, "exam.display_mode", "grades")
    assert overview.result_overview(
        session, data["meera"], "class_test", data["room"].id
    ).display_mode == "grades"


# --------------------------------------------------------------- performance


def test_the_overview_uses_a_fixed_number_of_queries_however_big_the_class():
    from sqlalchemy import event

    from tests.test_classroom_exams import _student

    session, data = world()
    first = scheduled_with_marks(
        session, data, total=50, day=date(2026, 12, 1), marks={"aarav": 45, "kabir": 10}
    )
    publish(session, first, data["meera"])

    def count() -> int:
        seen: list[str] = []
        engine = session.get_bind()

        def on_execute(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)

        event.listen(engine, "before_cursor_execute", on_execute)
        try:
            overview.result_overview(session, data["meera"], "class_test", data["room"].id)
        finally:
            event.remove(engine, "before_cursor_execute", on_execute)
        return len(seen)

    count()  # warm one-off lookups
    small = count()

    # Many more children and more tests: the number of statements must not grow.
    extra = [_student(session, f"child {n}", f"P6-{n}", data["room"]) for n in range(20)]
    for number in range(4):
        exam = scheduled_with_marks(
            session, data, total=20, day=date(2026, 12, 2 + number),
            marks={"aarav": 10, "kabir": 12},
        )
        save(
            session, exam.papers[0].id,
            [entry(child, 7 + number) for child in extra], data["meera"],
        )
        publish(session, exam, data["meera"])
    big = count()
    assert big == small, f"{small} vs {big} statements"
