"""Add `classroom.stage` - the model had it, the database never did.

Revision ID: e1c4b7a9f2d3
Revises: c3e8a1f6d2b9
Create Date: 2026-10-21

Why:
  `ClassroomBase.stage` groups the classes for reporting - pre_primary, primary,
  middle, secondary, senior_secondary - and `app/domains/academics/seed.py` writes
  it for all 15 classes. No migration ever created the column, so every seed that
  touched a classroom died with:

      psycopg2.errors.UndefinedColumn: column "stage" of relation "classroom"
      does not exist

  The column is added NOT NULL with a server default (so the existing rows get a
  value in the same statement), the real stage is backfilled per class, and the
  server default is then dropped - the model has a Python-side default only, and
  leaving a server default behind would be reported as drift by `--autogenerate`.

Downgrade drops the column; no other table is touched.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1c4b7a9f2d3"
down_revision: str | Sequence[str] | None = "c3e8a1f6d2b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: What the existing rows get while the column is being added.
DEFAULT_STAGE = "primary"

#: The real stage for every class the seed creates, applied during the upgrade so
#: an already-populated database is correct without waiting for the seed to run.
STAGE_BY_CLASS: dict[str, str] = {
    "Nursery": "pre_primary",
    "LKG": "pre_primary",
    "UKG": "pre_primary",
    "Class 1": "primary",
    "Class 2": "primary",
    "Class 3": "primary",
    "Class 4": "primary",
    "Class 5": "primary",
    "Class 6": "middle",
    "Class 7": "middle",
    "Class 8": "middle",
    "Class 9": "secondary",
    "Class 10": "secondary",
    "Class 11": "senior_secondary",
    "Class 12": "senior_secondary",
}


def _column_exists() -> bool:
    """True when `classroom.stage` is already there (guarded, so re-running is safe)."""
    found = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'classroom' AND column_name = 'stage'"
            )
        )
        .first()
    )
    return found is not None


def upgrade() -> None:
    if not _column_exists():
        op.add_column(
            "classroom",
            sa.Column(
                "stage", sa.String(), nullable=False, server_default=DEFAULT_STAGE
            ),
        )

    # Backfill the truthful stage per class, then drop the server default so the
    # column matches the model (Python-side default only).
    conn = op.get_bind()
    for class_name, stage in STAGE_BY_CLASS.items():
        conn.execute(
            sa.text("UPDATE classroom SET stage = :stage WHERE name = :name"),
            {"stage": stage, "name": class_name},
        )
    op.alter_column("classroom", "stage", server_default=None)


def downgrade() -> None:
    op.drop_column("classroom", "stage")
