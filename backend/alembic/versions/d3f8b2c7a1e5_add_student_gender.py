"""Add gender to studentprofile (class matrix needs real boys/girls counts)

Revision ID: d3f8b2c7a1e5
Revises: c9a2e7f1d4b8
Create Date: 2026-09-29

Why:
  `GET /academics/class-matrix` returned hardcoded rows with `boys` / `girls`
  numbers. To compute those from the database instead, a student's gender has
  to be stored - there was no column for it, so the split was invented in code.

The column is nullable: existing rows keep working (their gender is simply
unknown, so they count towards `strength` but not towards boys or girls).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f8b2c7a1e5"
down_revision: str | Sequence[str] | None = "c9a2e7f1d4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("studentprofile", sa.Column("gender", _AUTO_STR(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("studentprofile", "gender")
