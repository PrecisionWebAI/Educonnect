"""Admission form: add `student_email` column.

Revision ID: c8e4f2a9d1b7
Revises: b5d3c9e1f2a4
Create Date: 2026-10-28

Why:
  The admission form now collects the student's own email (previously only the
  father / mother / guardian had email fields). The promotion step then uses
  that address as the student's login, so a student signs in with their real
  email instead of a generated `stu.*` address.

Downgrade drops the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e4f2a9d1b7"
down_revision: str | Sequence[str] | None = "b5d3c9e1f2a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "admissionapplication",
        sa.Column("student_email", _AUTO_STR(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("admissionapplication", "student_email")
