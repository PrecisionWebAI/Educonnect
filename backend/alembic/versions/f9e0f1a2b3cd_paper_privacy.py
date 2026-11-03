"""`paperdraft.section_id` + `generationjob.created_by` - an exam is private.

Revision ID: f9e0f1a2b3cd
Revises: f9e0f1a2b3cc
Create Date: 2026-11-03

Why:
  1. `generationjob.created_by` - a job's output is the paper's questions. A
     stateless run (`POST /exams/generate`) saves no paper, so `paper_id` alone
     could not say whose output it is. Every paper/job route now answers 404 to
     anyone but the person who started it, which needs an owner on the job.
  2. `paperdraft.section_id` - the builder now opens inside a class-section, so a
     paper can be for Class 10-A rather than Class 10. `class_name` stays the
     class number, so the AI prompt and the source library keep matching.

  Both columns are nullable: every existing row stays valid (an old job inherits
  the owner of the paper it was generated for). Guarded, so re-running is a
  no-op.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3cd"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (table, column, parent table)
NEW_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("paperdraft", "section_id", "section"),
    ("generationjob", "created_by", '"user"'),
)


def _has_column(table: str, column: str) -> bool:
    found = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return found.first() is not None


def upgrade() -> None:
    """Add the two columns (idempotent)."""
    for table, column, parent in NEW_COLUMNS:
        if _has_column(table, column):
            continue
        op.execute(f"ALTER TABLE {table} ADD COLUMN {column} uuid")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_{column}_fkey "
            f"FOREIGN KEY ({column}) REFERENCES {parent} (id)"
        )
        op.execute(f"CREATE INDEX ix_{table}_{column} ON {table} ({column})")
        print(f"[exams] {table}.{column} is ready")


def downgrade() -> None:
    """Drop the two columns (nothing else depends on them)."""
    for table, column, _ in NEW_COLUMNS:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{column}")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
