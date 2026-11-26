"""How one child's mark reads - the figures behind a marks row and a notification.

A paper carries its **own** pass line and its **own** copy of the grading ladder
(`exam_paper.grading_scale`), so a result is judged by the rules that were set for that
paper, whatever the school's ladder says today. An older paper without a copy falls back
to the school's ladder. Nothing here writes: it only turns `(paper, mark)` into
percentage, grade, pass/fail and a sentence.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session

from app.domains.academic.classroom.exams.models import ExamPaper, Mark

from . import marking, setup


@dataclass(frozen=True)
class Figures:
    """What one mark comes to on its paper."""

    obtained: Decimal | None
    absent: bool
    percentage: Decimal | None
    grade: str | None
    #: `True` pass, `False` fail, `None` for an absent or unmarked child.
    passed: bool | None


def ladder_of(session: Session, paper: ExamPaper) -> marking.Ladder:
    """This paper's own ladder, or the school's when the paper has none (older rows)."""
    own = marking.ladder_from_json(paper.grading_scale)
    return own if own else setup.school_ladder(session)


def _grade_of(
    paper: ExamPaper, mark: Mark, ladder: marking.Ladder, percent: Decimal
) -> str | None:
    """The grade a sheet shows: from the ladder (`auto`), the teacher's own (`manual`) or none."""
    mode = getattr(paper, "grade_mode", "auto") or "auto"
    if mode == "na":
        return None
    if mode == "manual":
        return (mark.grade or "").strip() or None
    return marking.grade_for(ladder, percent)


def figures(paper: ExamPaper, mark: Mark | None, ladder: marking.Ladder) -> Figures:
    """Percentage, grade and pass/fail of one mark. An absence has none of them."""
    if mark is None or mark.is_absent or mark.marks_obtained is None:
        return Figures(
            obtained=None,
            absent=bool(mark and mark.is_absent),
            percentage=None,
            grade=None,
            passed=None,
        )
    total = Decimal(str(paper.max_marks))
    obtained = Decimal(str(mark.marks_obtained))
    percent = marking.percentage(obtained, total)
    return Figures(
        obtained=obtained,
        absent=False,
        percentage=percent,
        grade=_grade_of(paper, mark, ladder, percent),
        passed=marking.is_pass(
            obtained,
            total,
            mode=paper.pass_mode,
            passing_marks=(
                Decimal(str(paper.passing_marks))
                if paper.passing_marks is not None
                else None
            ),
            pass_percent=(
                Decimal(str(paper.pass_percent))
                if paper.pass_percent is not None
                else None
            ),
        ),
    )


def _figure(value: Decimal) -> str:
    """`50.00` -> `50`, `16.50` -> `16.5`."""
    return f"{value.normalize():f}"


def result_line(paper: ExamPaper, found: Figures, display_mode: str = "both") -> str:
    """One child's result as a sentence: `45/50 (90%) · Grade A1 · Pass`.

    `display_mode` is the school's `exam.display_mode`: `marks`, `grades` or `both`.
    An absent child reads `Absent`; an unmarked one `Not marked yet`.
    """
    if found.absent:
        return "Absent"
    if found.obtained is None:
        return "Not marked yet"
    total = Decimal(str(paper.max_marks))
    parts: list[str] = []
    if display_mode in ("marks", "both"):
        text = f"{_figure(found.obtained)}/{_figure(total)}"
        if found.percentage is not None:
            text += f" ({_figure(found.percentage)}%)"
        parts.append(text)
    if display_mode in ("grades", "both") and found.grade:
        parts.append(f"Grade {found.grade}")
    if found.passed is not None:
        parts.append("Pass" if found.passed else "Fail")
    return " · ".join(parts)
