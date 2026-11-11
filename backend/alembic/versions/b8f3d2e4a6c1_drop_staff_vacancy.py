"""Drop the staff vacancy table - hiring is now a candidate pipeline.

Revision ID: b8f3d2e4a6c1
Revises: a7e2c9f1d4b3
Create Date: 2026-10-31

Why:
  The Operations > Staff Hiring screen used to track posts separately in
  `staffvacancy` (role + openings + Open/Closed) and its "Open Vacancies" tile
  counted the unfilled seats. The screen is now a candidate pipeline plus an
  employee directory (`staffprofile`), so `staffvacancy` is dead weight: it has
  no writer, no reader other than that one tile, and zero rows in every school.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f3d2e4a6c1"
down_revision: str | Sequence[str] | None = "a7e2c9f1d4b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Drop the now-unused vacancy table."""
    op.drop_index("ix_staffvacancy_role", table_name="staffvacancy")
    op.drop_table("staffvacancy")


def downgrade() -> None:
    """Recreate the table, matching the schema as it was last seen."""
    op.create_table(
        "staffvacancy",
        sa.Column("role", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("openings", sa.Integer(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staffvacancy_role"), "staffvacancy", ["role"], unique=False)