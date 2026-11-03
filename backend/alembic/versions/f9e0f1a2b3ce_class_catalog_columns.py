"""Revision marker for the class/section columns revision that was reverted in code.

Revision ID: f9e0f1a2b3ce
Revises: f9e0f1a2b3cd
Create Date: 2026-11-03

Why this file exists at all
---------------------------
This revision id once carried a migration that added a handful of class/section
id columns. The code for it was reverted and the file deleted, **but a database
that ran it still reports this id in `alembic_version`** - and Alembic cannot
resolve a revision whose file is gone, so `alembic upgrade head` fails and the
API never starts. The id is restored here as a no-op marker so the chain
resolves again.

The columns that revision added are owned by `f9e0f1a2b3cf` (the global
`classname` / `section` catalogs): that revision creates them where they are
missing and re-points them where they already exist, so both a fresh database
and the one that ran the reverted revision end up identical.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3ce"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The columns the reverted revision added, per table.
REVERTED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("student_admission_form", "applied_class_id"),
    ("student_admission_form", "applied_section_id"),
    ("student_admission_form", "current_class_id"),
    ("student_admission_form", "previous_class_id"),
    ("student_admission_form", "separation_class_id"),
    ("questionusagelog", "classroom_id"),
    ("educationreport", "classroom_id"),
)


def _has_table(table: str) -> bool:
    found = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table"
        ),
        {"table": table},
    )
    return found.first() is not None


def upgrade() -> None:
    """Nothing to do - `f9e0f1a2b3cf` owns every column this id once added."""
    print("[class] revision marker: f9e0f1a2b3cf owns the class/section columns")


def downgrade() -> None:
    """Drop what the reverted revision had added (a fresh database has none of it)."""
    for table, column in REVERTED_COLUMNS:
        if _has_table(table):
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
