"""Exam paper: how the Grade column of its marks sheet works.

Revision ID: 0009
Revises: 0008

* `exam_paper.grade_mode` is `na` (no grade is shown - the default), `auto` (the grade
  comes from the paper's ladder) or `manual` (the teacher types each grade, stored in
  `marks.grade`);
* `exam_paper.syllabus_by_employee_id` - who is to write the subject's syllabus (NULL =
  the assigned teacher);
* `exam.archived_at` - an archived date sheet is hidden from the list (never deleted).

Safe to run twice.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "grade_mode" not in _columns("exam_paper"):
        op.add_column(
            "exam_paper",
            sa.Column("grade_mode", sa.String(), nullable=False, server_default="na"),
        )
    if "syllabus_by_employee_id" not in _columns("exam_paper"):
        op.add_column(
            "exam_paper",
            sa.Column("syllabus_by_employee_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_exam_paper_syllabus_by_employee",
            "exam_paper",
            "employee",
            ["syllabus_by_employee_id"],
            ["id"],
        )
        op.create_index(
            "ix_exam_paper_syllabus_by_employee_id",
            "exam_paper",
            ["syllabus_by_employee_id"],
        )
    if "archived_at" not in _columns("exam"):
        op.add_column("exam", sa.Column("archived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if "archived_at" in _columns("exam"):
        op.drop_column("exam", "archived_at")
    if "syllabus_by_employee_id" in _columns("exam_paper"):
        op.drop_index("ix_exam_paper_syllabus_by_employee_id", table_name="exam_paper")
        op.drop_constraint(
            "fk_exam_paper_syllabus_by_employee", "exam_paper", type_="foreignkey"
        )
        op.drop_column("exam_paper", "syllabus_by_employee_id")
    if "grade_mode" in _columns("exam_paper"):
        op.drop_column("exam_paper", "grade_mode")
