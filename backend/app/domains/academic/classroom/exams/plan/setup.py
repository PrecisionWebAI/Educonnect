"""The school's **starting values** for a paper's pass line.

Not a screen and not a table of its own: the school's 33% lives in `school_setting`
(`exam.pass_percent`), its ladder in `grade_scale` (or the built-in one), and the way a
result is shown in `exam.display_mode`. This module only reads them, so a date-sheet row
or a class-test form can pre-fill itself. Whatever the teacher changes after that belongs
to **that paper** (`exam_paper.pass_mode / passing_marks / passing_grade / grading_scale`).
"""

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.admin.settings import values as setting_values

from . import grades, marking
from .schemas import LadderRungRead, MarkingDefaultsRead

#: The words `exam.display_mode` may hold.
DISPLAY_MODES = ("marks", "grades", "both")

#: A paper's total is `numeric(6,2)`, so nothing above this fits in a column.
MAX_TOTAL = Decimal("9999.99")


def school_pass_percent(session: Session) -> Decimal:
    """The school's pass percentage; a stored non-number or out-of-range value falls back."""
    raw = setting_values.get_value(session, "exam.pass_percent")
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError):
        return marking.DEFAULT_PASS_PERCENT
    if value < 0 or value > 100:
        return marking.DEFAULT_PASS_PERCENT
    return marking.round2(value)


def school_display_mode(session: Session) -> str:
    raw = (setting_values.get_value(session, "exam.display_mode") or "").strip().lower()
    return raw if raw in DISPLAY_MODES else "both"


def school_ladder(session: Session) -> marking.Ladder:
    """The school's ladder as clean rungs, highest first (its own rows or the built-in)."""
    rows = [
        {"min_percent": minimum, "grade": grade}
        for minimum, grade in grades.ladder(session)
    ]
    return marking.validate_ladder(rows)


def marking_defaults(session: Session, total: Decimal) -> MarkingDefaultsRead:
    """The pre-filled pass line for a paper out of `total`."""
    if total <= 0 or total > MAX_TOTAL:
        raise HTTPException(
            status_code=422,
            detail=f"Total marks must be more than 0 and at most {MAX_TOTAL}.",
        )
    percent = school_pass_percent(session)
    ladder = school_ladder(session)
    return MarkingDefaultsRead(
        total_marks=total,
        pass_marks=marking.default_pass_marks(total, percent),
        pass_percent=percent,
        passing_grade=marking.grade_for(ladder, percent),
        ladder=[LadderRungRead(**rung) for rung in ladder],
        display_mode=school_display_mode(session),
    )
