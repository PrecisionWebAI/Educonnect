"""RAG: examsource library columns + questionusagelog (anti-repeat)

Revision ID: e5f7b9c2d4a6
Revises: c4d8f2a1b9e3
Create Date: 2026-09-25

Do kaam:
  1. `examsource` — content library ka source row RAG ke liye tayyar:
       · `grade_class_id` / `subject_id` → **nullable** (frontend class/subject
         ke naam bhejta hai, IDs nahi — Phase 1 mein mapping endpoint nahi hai)
       · naye columns: class_name, subject, board, teacher_name, kind, strictness,
         tags, status, chunk_count, error, updated_at
         (`status`/`chunk_count`/`error` = ingestion ka per-source status, taaki
         background ingest fail hone par teacher ko asli wajah dikhe)
  2. `questionusagelog` — naya table: "kaun sa question kis paper mein use hua",
     jisse purane questions dobara na aayein (blueprint §1.2.1 anti-repeat).

⚠️ NOT NULL columns ko `server_default` ke saath add karke phir default hata dete
hain (wahi pattern jo `a3c7e9f1b2d4` mein use hua) — warna purani rows par
NotNullViolation aata hai, aur autogenerate baad mein "default hata raha hai"
dikhata rehta hai.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "e5f7b9c2d4a6"
down_revision: Union[str, Sequence[str], None] = "c4d8f2a1b9e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (name, server_default) — AutoString columns
_TEXT_COLUMNS = [
    ("class_name", ""),
    ("subject", ""),
    ("board", ""),
    ("teacher_name", ""),
    ("kind", "knowledge"),
    ("strictness", "Strict"),
    ("status", "pending"),
]

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    # ---- 1a) FK columns nullable (frontend IDs nahi bhejta) ----
    op.alter_column(
        "examsource",
        "grade_class_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "examsource",
        "subject_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # ---- 1b) naye text columns (default ke saath, phir default hata do) ----
    for name, default in _TEXT_COLUMNS:
        op.add_column(
            "examsource",
            sa.Column(name, _AUTO_STR(), nullable=False, server_default=default),
        )
    for name, _ in _TEXT_COLUMNS:
        op.alter_column("examsource", name, server_default=None)

    # ---- 1c) tags (JSON) ----
    op.add_column(
        "examsource",
        sa.Column(
            "tags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.alter_column("examsource", "tags", server_default=None)

    # ---- 1d) chunk_count / error / updated_at ----
    op.add_column(
        "examsource",
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("examsource", "chunk_count", server_default=None)

    op.add_column("examsource", sa.Column("error", _AUTO_STR(), nullable=True))

    op.add_column(
        "examsource",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.alter_column("examsource", "updated_at", server_default=None)

    # ---- 2) questionusagelog (anti-repeat ledger) ----
    op.create_table(
        "questionusagelog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", _AUTO_STR(), nullable=False),
        sa.Column("text", _AUTO_STR(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=True),
        sa.Column("class_name", _AUTO_STR(), nullable=False, server_default=""),
        sa.Column("subject", _AUTO_STR(), nullable=False, server_default=""),
        sa.Column("chapter", _AUTO_STR(), nullable=False, server_default=""),
        sa.Column("topic", _AUTO_STR(), nullable=False, server_default=""),
        sa.Column("qtype", _AUTO_STR(), nullable=False, server_default=""),
        sa.Column("marks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["paperdraft.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_questionusagelog_fingerprint", "questionusagelog", ["fingerprint"]
    )
    op.create_index("ix_questionusagelog_paper_id", "questionusagelog", ["paper_id"])
    op.create_index("ix_questionusagelog_class_name", "questionusagelog", ["class_name"])
    op.create_index("ix_questionusagelog_subject", "questionusagelog", ["subject"])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema — ulta kram (last added, first dropped)."""
    op.drop_index("ix_questionusagelog_subject", table_name="questionusagelog")
    op.drop_index("ix_questionusagelog_class_name", table_name="questionusagelog")
    op.drop_index("ix_questionusagelog_paper_id", table_name="questionusagelog")
    op.drop_index("ix_questionusagelog_fingerprint", table_name="questionusagelog")
    op.drop_table("questionusagelog")

    for name in ("updated_at", "error", "chunk_count", "tags"):
        op.drop_column("examsource", name)
    for name, _ in reversed(_TEXT_COLUMNS):
        op.drop_column("examsource", name)

    # NOT NULL wapas karna tab hi safe hai jab NULL rows na ho
    op.execute("DELETE FROM examsource WHERE grade_class_id IS NULL")
    op.alter_column(
        "examsource", "grade_class_id", existing_type=sa.Integer(), nullable=False
    )
    op.execute("DELETE FROM examsource WHERE subject_id IS NULL")
    op.alter_column(
        "examsource", "subject_id", existing_type=sa.Integer(), nullable=False
    )
    # ### end Alembic commands ###
