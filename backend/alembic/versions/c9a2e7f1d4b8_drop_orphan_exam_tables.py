"""Drop the orphaned legacy exam tables (examterm, exampaper, examresult)

Revision ID: c9a2e7f1d4b8
Revises: b7f1c3d5e8a2
Create Date: 2026-09-29

Why:
  These three tables belong to the first blueprint design (term -> paper ->
  result). The AI paper builder replaced that design with paperdraft,
  generationjob, examsource and questionusagelog. The SQLModel classes were
  deleted from `app/domains/exams/models.py`, but no migration ever dropped
  the tables, so they stayed in the database and made the schema ambiguous
  (to a reader, "exampaper" looked as real as "paperdraft").

Drop order matters because of foreign keys:
  examresult -> exampaper -> examterm

Two enum types were owned only by these tables and become unusable once the
tables are gone, so they are dropped as well:
  `resultstatus`    - examresult.status
  `exampaperstatus` - exampaper.status

Data note: this permanently destroys 1 row in examterm and 1 row in exampaper
(legacy test data). examresult is empty. downgrade() recreates the empty
tables only - it cannot restore the deleted rows.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a2e7f1d4b8"
down_revision: str | Sequence[str] | None = "b7f1c3d5e8a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    # Children first: an existing foreign key would block the parent drop.
    op.drop_table("examresult")
    op.drop_table("exampaper")
    op.drop_table("examterm")

    # Unused enum types - keeping them would leave dead types in the catalog.
    postgresql.ENUM("entered", "approved", "published", name="resultstatus").drop(
        op.get_bind()
    )
    postgresql.ENUM("draft", "in_review", "approved", name="exampaperstatus").drop(
        op.get_bind()
    )


def downgrade() -> None:
    """Downgrade schema.

    Recreates the three tables exactly as migrations `8a84d5ed6a1f`
    (initial setup) and `e08a27be1a21` (audit log) had left them, so a
    rollback restores the old shape - but empty.
    """
    resultstatus = postgresql.ENUM(
        "entered", "approved", "published", name="resultstatus"
    )
    resultstatus.create(op.get_bind())
    exampaperstatus = postgresql.ENUM(
        "draft", "in_review", "approved", name="exampaperstatus"
    )
    exampaperstatus.create(op.get_bind())

    op.create_table(
        "examterm",
        sa.Column("name", _AUTO_STR(), nullable=False),
        sa.Column("grade_class_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["grade_class_id"], ["gradeclass.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exampaper",
        sa.Column("exam_term_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "in_review",
                "approved",
                name="exampaperstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["exam_term_id"], ["examterm.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["subject.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "examresult",
        sa.Column("exam_paper_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("marks_obtained", sa.Float(), nullable=False),
        sa.Column("ai_feedback", _AUTO_STR(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "entered",
                "approved",
                "published",
                name="resultstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("entered_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("published_by_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["exam_paper_id"], ["exampaper.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["studentprofile.id"]),
        sa.ForeignKeyConstraint(["entered_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["published_by_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
