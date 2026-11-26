"""Exam paper: the lowest passing grade.

Revision ID: 0007
Revises: 0006

A paper's pass line is stated either as a number of marks or as a passing grade
(`exam_paper.pass_mode` = `marks` / `grade`). `passing_grade` holds the grade in the
second case. Nullable, so every existing paper reads as before. Safe to run twice.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "passing_grade" not in _columns("exam_paper"):
        op.add_column(
            "exam_paper", sa.Column("passing_grade", sa.String(), nullable=True)
        )


def downgrade() -> None:
    # Drops the column and the passing grades stored in it.
    if "passing_grade" in _columns("exam_paper"):
        op.drop_column("exam_paper", "passing_grade")
