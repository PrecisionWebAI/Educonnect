"""Drop `markdispute` - the Marks-dispute tab is gone.

Revision ID: f9e0f1a2b3d0
Revises: f9e0f1a2b3cf
Create Date: 2026-11-03

The mark-dispute screen and the endpoints behind it were removed, so the table
they wrote to is dead weight: nothing reads it or writes it any more.
`check_schema.py` compares the tables the models declare against the ones the
database has, so leaving it behind is exactly the drift it exists to catch.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3d0"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `IF EXISTS`, so a database that never had the table - or already dropped it -
    # is fine rather than an error.
    op.execute("DROP TABLE IF EXISTS markdispute")


def downgrade() -> None:
    """Recreate the table the removed feature wrote to (structure, not data)."""
    op.create_table(
        "markdispute",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id")),
        sa.Column(
            "student_id", sa.Uuid(), sa.ForeignKey("studentprofile.id"), nullable=False
        ),
        sa.Column("exam_id", sa.Uuid(), sa.ForeignKey("exam.id"), nullable=False),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subject.id"), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="Open"),
        sa.Column("raised_by", sa.Uuid(), sa.ForeignKey("user.id")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_markdispute_student_id", "markdispute", ["student_id"])
    op.create_index("ix_markdispute_exam_id", "markdispute", ["exam_id"])
