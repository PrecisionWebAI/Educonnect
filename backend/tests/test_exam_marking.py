"""Exam module, Phase 2: the pass line (marks or grade), grade, pass/fail, school defaults.

The first half is pure arithmetic (`plan/marking.py` has no database); the second half
checks that the school's starting values reach a new paper.
"""

from decimal import Decimal as D

import pytest
from fastapi import HTTPException

from app.domains.academic.classroom.exams.models import GradeScale
from app.domains.academic.classroom.exams.plan import marking, setup
from app.domains.admin.settings import values as setting_values
from tests.test_classroom_timetable import memory_session, seed

LADDER = [
    {"min_percent": D(minimum), "grade": grade}
    for minimum, grade in [
        (90, "A1"),
        (80, "A2"),
        (70, "B1"),
        (60, "B2"),
        (50, "C1"),
        (40, "C2"),
        (33, "D"),
        (0, "E"),
    ]
]


# ---------------------------------------------------------------- numbers


def test_the_pass_marks_start_at_33_percent_of_the_total():
    assert marking.default_pass_marks(D(100)) == D("33.00")
    assert marking.default_pass_marks(D(50)) == D("16.50")
    assert marking.default_pass_marks(D(20)) == D("6.60")


def test_halves_round_up_not_to_even():
    # 12.5 * 33% = 4.125 -> 4.13 (banker's rounding would give 4.12).
    assert marking.default_pass_marks(D("12.5")) == D("4.13")


def test_changing_the_pass_marks_shows_what_percent_of_the_total_it_is():
    assert marking.pass_percent_of(D(40), D(100)) == D("40.00")
    assert marking.pass_percent_of(D(16), D(50)) == D("32.00")
    assert marking.pass_percent_of(D(10), D(0)) is None


def test_a_percentage_is_exact_and_an_absent_student_has_none():
    assert marking.percentage(D(45), D(60)) == D("75.00")
    assert marking.percentage(None, D(60)) is None


# ----------------------------------------------------------------- ladder


def test_a_grade_comes_from_the_ladder_at_the_boundary():
    assert marking.grade_for(LADDER, D("92")) == "A1"
    assert marking.grade_for(LADDER, D("33")) == "D"
    assert marking.grade_for(LADDER, D("32.99")) == "E"
    assert marking.grade_for(LADDER, None) is None


@pytest.mark.parametrize(
    "rows, message",
    [
        ([], "at least one grade"),
        ([{"grade": "A", "min_percent": 10}], "start at 0%"),
        (
            [{"grade": "A", "min_percent": 0}, {"grade": "B", "min_percent": 0}],
            "same percentage",
        ),
        (
            [{"grade": "A", "min_percent": 0}, {"grade": "a", "min_percent": 50}],
            "same name",
        ),
        ([{"grade": " ", "min_percent": 0}], "needs a name"),
        ([{"grade": "A", "min_percent": 120}], "between 0 and 100"),
    ],
)
def test_a_ladder_that_cannot_be_true_is_refused(rows, message):
    with pytest.raises(marking.MarkingError, match=message):
        marking.validate_ladder(rows)


# --------------------------------------------------------------- pass line


def test_marks_mode_defaults_to_33_percent_and_follows_a_changed_number():
    line = marking.resolve_pass_line(mode=None, total=D(100), ladder=LADDER)
    assert (line.mode, line.passing_marks, line.pass_percent) == (
        "marks",
        D("33.00"),
        D("33.00"),
    )
    changed = marking.resolve_pass_line(
        mode="marks", total=D(100), ladder=LADDER, passing_marks="40"
    )
    assert changed.passing_marks == D("40.00")
    assert changed.pass_percent == D("40.00"), "the small percent beside the number"
    half = marking.resolve_pass_line(mode="marks", total=D(50), ladder=LADDER)
    assert half.passing_marks == D("16.50")


@pytest.mark.parametrize("bad", ["101", "-1", "abc"])
def test_pass_marks_outside_the_paper_are_refused(bad):
    with pytest.raises(marking.MarkingError):
        marking.resolve_pass_line(
            mode="marks", total=D(100), ladder=LADDER, passing_marks=bad
        )


def test_grade_mode_uses_the_grades_own_percentage():
    line = marking.resolve_pass_line(
        mode="grade", total=D(50), ladder=LADDER, passing_grade="c2"
    )
    assert line.passing_grade == "C2", "spelled the way the ladder spells it"
    assert line.pass_percent == D("40.00")
    assert line.passing_marks == D("20.00")


def test_a_custom_grade_brings_its_percentage_and_stays_on_this_papers_copy():
    line = marking.resolve_pass_line(
        mode="grade",
        total=D(100),
        ladder=LADDER,
        passing_grade="P",
        custom_min_percent="35",
    )
    assert line.pass_percent == D("35.00")
    assert len(line.ladder) == len(LADDER) + 1
    assert len(LADDER) == 8, "the school's own ladder is untouched"
    # no percentage given: the custom grade passes at the school's own pass percentage
    plain = marking.resolve_pass_line(
        mode="grade", total=D(100), ladder=LADDER, passing_grade="p"
    )
    assert plain.passing_grade == "P" and plain.pass_percent == D("33.00")
    assert plain.passing_marks == D("33.00") and len(plain.ladder) == len(LADDER)
    with pytest.raises(marking.MarkingError, match="same percentage"):
        marking.resolve_pass_line(
            mode="grade",
            total=D(100),
            ladder=LADDER,
            passing_grade="P",
            custom_min_percent="33",
        )


def test_a_custom_grade_is_a_letter_then_a_letter_or_a_number_and_is_stored_in_capitals():
    line = marking.resolve_pass_line(
        mode="grade", total=D(100), ladder=LADDER, passing_grade="pq", custom_min_percent="35"
    )
    assert line.passing_grade == "PQ"
    for fine, kept in (("p", "P"), ("c1", "C1")):
        ok = marking.resolve_pass_line(
            mode="grade", total=D(100), ladder=LADDER, passing_grade=fine, custom_min_percent="35"
        )
        assert ok.passing_grade == kept
    for bad in ("PQR", "1P", "1", "P!", "É"):
        with pytest.raises(marking.MarkingError, match="capital letter first"):
            marking.resolve_pass_line(
                mode="grade",
                total=D(100),
                ladder=LADDER,
                passing_grade=bad,
                custom_min_percent="35",
            )


def test_an_unknown_mode_or_a_zero_total_is_refused():
    with pytest.raises(marking.MarkingError):
        marking.resolve_pass_line(mode="percent", total=D(100), ladder=LADDER)
    with pytest.raises(marking.MarkingError):
        marking.resolve_pass_line(mode="marks", total=D(0), ladder=LADDER)


def test_pass_and_fail_follow_the_mode_and_absent_is_neither():
    def run(obtained, total, **kw):
        return marking.is_pass(obtained, D(total), **kw)

    marks = dict(mode="marks", passing_marks=D("16.5"), pass_percent=D(33))
    assert run(D("16.5"), 50, **marks) is True
    assert run(D(16), 50, **marks) is False
    grade = dict(mode="grade", passing_marks=None, pass_percent=D(40))
    assert run(D(20), 50, **grade) is True
    assert run(D(19), 50, **grade) is False
    assert run(None, 50, **marks) is None, "absent is neither pass nor fail"
    assert run(D(0), 100, **marks) is False, "zero is a fail - a score, not an absence"


# ------------------------------------------------------- school defaults


def test_a_new_paper_starts_from_33_percent_and_the_built_in_ladder():
    session = memory_session()
    seed(session)
    out = setup.marking_defaults(session, D(50))
    assert out.pass_marks == D("16.50")
    assert out.pass_percent == D("33.00")
    assert out.passing_grade == "D"
    assert out.display_mode == "both"
    assert [rung.grade for rung in out.ladder][:2] == ["A1", "A2"]
    assert out.ladder[-1].min_percent == D("0")


def test_the_schools_own_percentage_ladder_and_display_mode_win():
    session = memory_session()
    seed(session)
    setting_values.set_value(session, "exam.pass_percent", 40)
    setting_values.set_value(session, "exam.display_mode", "grades")
    session.add(GradeScale(min_percent=D("0"), grade="Fail"))
    session.add(GradeScale(min_percent=D("40"), grade="Pass"))
    session.commit()
    out = setup.marking_defaults(session, D(100))
    assert out.pass_marks == D("40.00")
    assert out.passing_grade == "Pass"
    assert out.display_mode == "grades"
    assert [rung.grade for rung in out.ladder] == ["Pass", "Fail"]


def test_a_garbage_setting_falls_back_instead_of_breaking_the_form():
    session = memory_session()
    seed(session)
    setting_values.set_value(session, "exam.pass_percent", "lots")
    setting_values.set_value(session, "exam.display_mode", "sideways")
    out = setup.marking_defaults(session, D(100))
    assert out.pass_percent == D("33.00")
    assert out.display_mode == "both"


def test_a_total_that_cannot_be_a_paper_is_refused():
    session = memory_session()
    seed(session)
    for total in (D(0), D("-5"), D("10000")):
        with pytest.raises(HTTPException) as caught:
            setup.marking_defaults(session, total)
        assert caught.value.status_code == 422
