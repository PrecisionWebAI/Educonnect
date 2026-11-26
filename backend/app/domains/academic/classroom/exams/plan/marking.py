"""Marking: how a paper's pass line is stated, and how pass / fail / grade come out.

Pure functions - **no database, no session, no I/O** - so every rule here is testable
without a school and cannot disagree with itself across screens.

The pass line of one paper is stated in one of two ways (the teacher chooses, per paper):

* **marks** - a number. It starts at 33% of the paper's total (100 -> 33, 50 -> 16.5,
  20 -> 6.6) and the teacher may change it; the screen then shows what percentage of the
  total that number is (33 -> 40 on a 100-mark paper reads "40%").
* **grade** - the lowest grade that still passes ("D", or a grade the teacher types). A
  custom grade that is not on the ladder brings its own starting percentage, and is added
  to **this paper's** copy of the ladder only.

Either way a paper ends up with one `pass_percent`: the pass line as a percentage of the
total. That is what the "40%" shows, and what a grade-based pass compares against.

Rules this module keeps
-----------------------
* **Decimal everywhere, never float.** Money-grade exactness: `0.1 + 0.2` is not a
  question a result card should ever ask.
* **Rounding is ROUND_HALF_UP to 2 places** (16.5, 6.6 - not banker's rounding).
* **Absent is not zero.** `is_pass(None, ...)` is `None` - neither a pass nor a fail.
* **A ladder always starts at 0**, so every percentage earns *some* grade.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal(100)

#: What a school gets before it sets its own (the `exam.pass_percent` setting).
DEFAULT_PASS_PERCENT = Decimal(33)

MODE_MARKS = "marks"
MODE_GRADE = "grade"
MODES = (MODE_MARKS, MODE_GRADE)

#: One rung of a ladder: `{"min_percent": Decimal, "grade": "A1"}`.
Ladder = list[dict]


class MarkingError(ValueError):
    """The pass line or ladder cannot be true. The message is shown to the teacher."""


# ---------------------------------------------------------------- numbers


def to_decimal(value, *, what: str = "value") -> Decimal:
    """`value` as a `Decimal`, or a `MarkingError` naming what was wrong."""
    if isinstance(value, Decimal):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise MarkingError(f"Enter the {what}.")
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise MarkingError(f"The {what} must be a number.") from exc


def round2(value: Decimal) -> Decimal:
    """Two decimals, halves rounded **up** (`16.5`, `6.6`, `4.13` for 4.125)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def percentage(obtained: Decimal | None, total: Decimal) -> Decimal | None:
    """`obtained / total * 100` to 2 places; `None` for an absent student or no total."""
    if obtained is None or total <= 0:
        return None
    return round2(obtained * HUNDRED / total)


def default_pass_marks(
    total: Decimal, percent: Decimal = DEFAULT_PASS_PERCENT
) -> Decimal:
    """The number a new paper starts from: `percent` of the total.

    100 -> 33.00, 50 -> 16.50, 20 -> 6.60. The teacher may change it.
    """
    return round2(Decimal(total) * Decimal(percent) / HUNDRED)


def pass_percent_of(passing_marks: Decimal, total: Decimal) -> Decimal | None:
    """What percentage of the total `passing_marks` is - the small "40%" beside it."""
    if total <= 0:
        return None
    return round2(Decimal(passing_marks) * HUNDRED / Decimal(total))


# ----------------------------------------------------------------- ladder


def _rung(row: dict) -> dict:
    grade = str(row.get("grade", "")).strip()
    if not grade:
        raise MarkingError("Every grade needs a name.")
    minimum = to_decimal(row.get("min_percent"), what=f"minimum percentage for {grade}")
    if minimum < 0 or minimum > HUNDRED:
        raise MarkingError(f"{grade}: the percentage must be between 0 and 100.")
    return {"min_percent": round2(minimum), "grade": grade}


def validate_ladder(rows: Iterable[dict]) -> Ladder:
    """The ladder as clean rungs, highest first - or a `MarkingError`.

    Rules: at least one rung, one rung starts at **0** (every percentage earns a grade),
    no two rungs share a percentage, no two share a grade name (any case).
    """
    rungs = [_rung(row) for row in rows]
    if not rungs:
        raise MarkingError("The grading scale needs at least one grade.")
    minimums = [r["min_percent"] for r in rungs]
    if len(set(minimums)) != len(minimums):
        raise MarkingError("Two grades start at the same percentage.")
    names = [r["grade"].casefold() for r in rungs]
    if len(set(names)) != len(names):
        raise MarkingError("Two grades have the same name.")
    if Decimal(0) not in minimums:
        raise MarkingError("The lowest grade must start at 0%.")
    return sorted(rungs, key=lambda r: r["min_percent"], reverse=True)


def grade_for(ladder: Ladder, percent: Decimal | None) -> str | None:
    """The grade `percent` earns on `ladder`; `None` when there is no percentage."""
    if percent is None:
        return None
    for rung in sorted(ladder, key=lambda r: r["min_percent"], reverse=True):
        if percent >= rung["min_percent"]:
            return rung["grade"]
    return None


def min_percent_of(ladder: Ladder, grade: str) -> Decimal | None:
    """Where `grade` starts on `ladder` (name matched ignoring case), or `None`."""
    wanted = grade.strip().casefold()
    for rung in ladder:
        if rung["grade"].casefold() == wanted:
            return rung["min_percent"]
    return None


def custom_grade_name(grade: str) -> str:
    """A custom grade as stored: up to two characters, a capital letter first and then a
    letter or a digit ("P", "PQ", "C1")."""
    name = grade.strip().upper()
    ok = (
        1 <= len(name) <= 2
        and name.isascii()
        and name[0].isalpha()
        and (len(name) == 1 or name[1].isalnum())
    )
    if not ok:
        raise MarkingError(
            "A custom grade is up to two characters: a capital letter first, then a letter "
            "or a number."
        )
    return name


def with_custom_grade(
    ladder: Ladder, grade: str, min_percent: Decimal | str | None
) -> Ladder:
    """`ladder`, plus `grade` if it is not on it yet.

    A grade already on the ladder is used as it is (the given percentage is ignored - the
    ladder is the truth). A **custom** grade must say where it starts; it joins this
    paper's copy of the ladder, never the school's.
    """
    if min_percent_of(ladder, grade) is not None:
        return list(ladder)
    grade = custom_grade_name(grade)
    if min_percent is None or (isinstance(min_percent, str) and not min_percent.strip()):
        raise MarkingError(
            f"'{grade.strip()}' is not in the grading scale - give the percentage it "
            "starts at."
        )
    return validate_ladder([*ladder, {"grade": grade, "min_percent": min_percent}])


def ladder_to_json(ladder: Ladder) -> list[dict]:
    """The ladder as JSON-safe rungs (`Decimal` is not JSON) for `exam_paper.grading_scale`."""
    return [
        {"min_percent": float(rung["min_percent"]), "grade": rung["grade"]}
        for rung in ladder
    ]


def ladder_from_json(rows: list[dict] | None) -> Ladder:
    """A stored ladder back as exact rungs; an empty/missing one is an empty ladder."""
    return [
        {"min_percent": Decimal(str(row["min_percent"])), "grade": row["grade"]}
        for row in (rows or [])
    ]


# --------------------------------------------------------------- pass line


@dataclass(frozen=True)
class PassLine:
    """One paper's resolved pass line. Everything a result needs, nothing it must guess."""

    mode: str
    #: The number of marks that passes (derived from the grade in `grade` mode).
    passing_marks: Decimal
    #: The lowest passing grade (`grade` mode only).
    passing_grade: str | None
    #: The pass line as a percentage of the total, whichever way it was stated.
    pass_percent: Decimal
    #: This paper's own copy of the ladder (a custom grade is added here).
    ladder: Ladder


def resolve_pass_line(
    *,
    mode: str | None,
    total: Decimal,
    ladder: Ladder,
    passing_marks: Decimal | str | None = None,
    passing_grade: str | None = None,
    custom_min_percent: Decimal | str | None = None,
    default_percent: Decimal = DEFAULT_PASS_PERCENT,
) -> PassLine:
    """Turn what the teacher filled in into a complete, consistent pass line.

    * `mode` empty means `marks` (the default).
    * **marks**: no number given -> 33% of the total; a number must be within `0..total`.
    * **grade**: a grade is required; if it is not on `ladder`, `custom_min_percent` says
      where it starts. The pass marks shown are that percentage of the total.
    """
    total = to_decimal(total, what="total marks")
    if total <= 0:
        raise MarkingError("Total marks must be more than 0.")
    chosen = (mode or MODE_MARKS).strip().lower()
    if chosen not in MODES:
        raise MarkingError(f"Pass by '{mode}' is not one of: {', '.join(MODES)}.")
    clean = validate_ladder(ladder)

    if chosen == MODE_MARKS:
        if passing_marks is None or (
            isinstance(passing_marks, str) and not passing_marks.strip()
        ):
            marks = default_pass_marks(total, default_percent)
        else:
            marks = round2(to_decimal(passing_marks, what="passing marks"))
        if marks < 0:
            raise MarkingError("Passing marks cannot be below 0.")
        if marks > total:
            raise MarkingError(
                f"Passing marks ({marks}) cannot be more than total marks ({total})."
            )
        percent = pass_percent_of(marks, total)
        return PassLine(chosen, marks, None, percent, clean)

    name = (passing_grade or "").strip()
    if not name:
        raise MarkingError("Choose the lowest passing grade.")
    if min_percent_of(clean, name) is None and (
        custom_min_percent is None
        or (isinstance(custom_min_percent, str) and not custom_min_percent.strip())
    ):
        # A custom passing grade names no percentage: it passes at the school's own pass
        # percentage, and the ladder is left as it is.
        custom = custom_grade_name(name)
        start = to_decimal(default_percent, what="pass percent")
        return PassLine(
            chosen, round2(total * start / HUNDRED), custom, round2(start), clean
        )
    own = with_custom_grade(clean, name, custom_min_percent)
    start = min_percent_of(own, name)
    # Keep the name the ladder spells it with ("d" typed, "D" on the ladder -> "D").
    spelled = next(r["grade"] for r in own if r["grade"].casefold() == name.casefold())
    marks = round2(total * start / HUNDRED)
    return PassLine(chosen, marks, spelled, start, own)


def is_pass(
    obtained: Decimal | None,
    total: Decimal,
    *,
    mode: str | None,
    passing_marks: Decimal | None,
    pass_percent: Decimal | None,
) -> bool | None:
    """`True` / `False` for a score, `None` for an absent student (neither pass nor fail).

    `marks` mode: `obtained >= passing_marks`. `grade` mode: the percentage reaches the
    passing grade's start - compared as `obtained * 100 >= pass_percent * total`, so
    nothing is divided and rounded before the question is asked.
    """
    if obtained is None:
        return None
    if (mode or MODE_MARKS) == MODE_GRADE and pass_percent is not None:
        return obtained * HUNDRED >= pass_percent * total
    if passing_marks is None:
        passing_marks = default_pass_marks(total)
    return obtained >= passing_marks
