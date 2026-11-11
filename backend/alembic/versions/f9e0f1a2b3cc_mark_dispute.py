"""`markdispute` - a mark a family is challenging.

Revision ID: f9e0f1a2b3cc
Revises: f9e0f1a2b3cb
Create Date: 2026-11-03

Why:
  The Academics screen has always had a "Marks Dispute" tab and **no table behind
  it**, so a challenge could never be recorded. This adds the one table it needs:
  one row per challenge, naming the student, the exam and the subject it is about,
  the reason, and where it has got to (`Open` -> `Under Review` -> `Resolved`).

  The row names the exam and subject rather than a `marks` row, so a challenge can
  be raised before the mark is entered - and still be answered after the mark was
  corrected.

  Guarded, so running it twice (or on a database that already has the table) is a
  no-op.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3cc"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (constraint name, the table it points at, the column it uses)
FOREIGN_KEYS: tuple[tuple[str, str, str], ...] = (
    ("school_id", "school", "school_id"),
    ("student_id", "studentprofile", "student_id"),
    ("exam_id", "exam", "exam_id"),
    ("subject_id", "subject", "subject_id"),
    ("raised_by", '"user"', "raised_by"),
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
    """Create the dispute table (idempotent)."""
    if _has_table("markdispute"):
        return

    op.execute(
        """
        CREATE TABLE markdispute (
            id uuid NOT NULL,
            school_id uuid,
            student_id uuid NOT NULL,
            exam_id uuid NOT NULL,
            subject_id uuid NOT NULL,
            reason varchar NOT NULL,
            status varchar NOT NULL DEFAULT 'Open',
            raised_by uuid,
            resolved_at timestamp without time zone,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            CONSTRAINT markdispute_pkey PRIMARY KEY (id)
        )
        """
    )
    for column, parent, target in FOREIGN_KEYS:
        op.execute(
            f"ALTER TABLE markdispute ADD CONSTRAINT markdispute_{column}_fkey "
            f"FOREIGN KEY ({target}) REFERENCES {parent} (id)"
        )
    op.execute("CREATE INDEX ix_markdispute_student_id ON markdispute (student_id)")
    op.execute("CREATE INDEX ix_markdispute_exam_id ON markdispute (exam_id)")

    print("[marks] markdispute is ready")


def downgrade() -> None:
    """Drop the dispute table (nothing else depends on it)."""
    op.execute("DROP TABLE IF EXISTS markdispute")
