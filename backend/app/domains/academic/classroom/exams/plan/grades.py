"""Grades and ranks - the two numbers a result card **derives**, never stores.

* **The grade ladder is data**: `grade_scale` rows, read here, so a school that calls 90
  "A+" and one that calls it "A1" both get their answer without a code change.
* **A rank is computed from the scores in front of it**, with competition ranking
  (`1, 2, 2, 4`): two children on 92% share first place and nobody is third. A student
  who did not sit a paper is not ranked at all - an absence is not a zero.
"""

from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.exams.models import GradeScale

#: The ladder a school starts with (the common Indian school scale). A school that wants
#: its own writes `grade_scale` rows and this is never consulted again.
DEFAULT_LADDER: tuple[tuple[str, str], ...] = (
    ("90", "A1"),
    ("80", "A2"),
    ("70", "B1"),
    ("60", "B2"),
    ("50", "C1"),
    ("40", "C2"),
    ("33", "D"),
    ("0", "E"),
)


def ladder(session: Session) -> list[tuple[Decimal, str]]:
    """(minimum percentage, grade) for this school, highest boundary first."""
    rows = session.exec(
        select(GradeScale).order_by(GradeScale.min_percent.desc())
    ).all()
    if rows:
        return [(Decimal(str(row.min_percent)), row.grade) for row in rows]
    return [(Decimal(minimum), grade) for minimum, grade in DEFAULT_LADDER]


def grade_for(session: Session, percent: Decimal | float | None) -> str | None:
    """The grade this percentage earns, or `None` when there is no percentage."""
    if percent is None:
        return None
    value = Decimal(str(percent))
    for minimum, grade in ladder(session):
        if value >= minimum:
            return grade
    return None


def competition_ranks(scores: dict[UUID, Decimal]) -> dict[UUID, int]:
    """`{student: rank}` where equal scores share the better rank and the next skips.

    `{a: 92, b: 92, c: 80}` -> `{a: 1, b: 1, c: 3}`. Students with no score are simply
    absent from the input and get no rank.
    """
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ranks: dict[UUID, int] = {}
    previous: Decimal | None = None
    previous_rank = 0
    for position, (student_id, score) in enumerate(ordered, start=1):
        if previous is not None and score == previous:
            ranks[student_id] = previous_rank
        else:
            ranks[student_id] = position
            previous_rank = position
            previous = score
    return ranks
