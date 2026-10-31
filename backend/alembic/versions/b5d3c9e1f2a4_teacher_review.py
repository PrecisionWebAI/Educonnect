"""Teacher review table (Tab 9.4 — Performance & Review).

Revision ID: b5d3c9e1f2a4
Revises: a7b2c9d1e3f4
Create Date: 2026-10-28

Why:
  The Teachers > Performance & Review screen answered with hard-coded ratings
  (\"P. Menon 4.6, 12 reviews\") because the database had nowhere to store the
  anonymous star ratings the screen collects. This adds `teacherreview` — one
  row per anonymous rating — and the service aggregates it into the per-teacher
  summary (average rating, review count, trend, score).

Downgrade drops the table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5d3c9e1f2a4"
down_revision: str | Sequence[str] | None = "a7b2c9d1e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "teacherreview",
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reviewer_role", _AUTO_STR(), nullable=False, server_default="Parent"),
        sa.Column("comment", _AUTO_STR(), nullable=True),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teacherprofile.id"]),
    )
    op.create_index("ix_teacherreview_school_id", "teacherreview", ["school_id"])
    op.create_foreign_key(
        "teacherreview_school_id_fkey",
        "teacherreview",
        "school",
        ["school_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("teacherreview_school_id_fkey", "teacherreview", type_="foreignkey")
    op.drop_index("ix_teacherreview_school_id", table_name="teacherreview")
    op.drop_table("teacherreview")
