"""Attendance rows point at the student's enrollment.

Revision ID: 0003
Revises: 0002

`attendancerecord.enrollment_id` links a day to the enrollment of the session it
belongs to, so the row's year is read through the enrollment instead of a second year
column. Existing rows are matched by student and the session whose dates contain the
day; rows with no matching enrollment stay NULL. Nothing is deleted.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    have = {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("attendancerecord")
    }
    if "enrollment_id" in have:
        return
    op.add_column(
        "attendancerecord", sa.Column("enrollment_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_attendancerecord_enrollment_id"),
        "attendancerecord",
        ["enrollment_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_attendancerecord_enrollment_id",
        "attendancerecord",
        "enrollment",
        ["enrollment_id"],
        ["id"],
    )
    op.execute(
        """
        UPDATE attendancerecord AS a
           SET enrollment_id = e.id
          FROM enrollment AS e
          JOIN academic_year AS y ON y.id = e.academic_year_id
         WHERE e.student_id = a.student_id
           AND a.date BETWEEN y.start_date AND y.end_date
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_attendancerecord_enrollment_id", "attendancerecord", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_attendancerecord_enrollment_id"), table_name="attendancerecord"
    )
    op.drop_column("attendancerecord", "enrollment_id")
