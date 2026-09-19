"""Add paper context columns to paperdraft (Phase 2 — AI prompt fuel)

Revision ID: a3c7e9f1b2d4
Revises: f7d9a1b2c3e4
Create Date: 2026-09-18

Kya karta hai: `paperdraft` table mein 10 naye columns add karta hai jo AI ko
context dete hain (class/subject/board/exam type/language/chapters) aur
frontend ke Steps ka data store karte hain (sources/instructions/scope/constraints).

Purani tables/columns ko chhedta nahi — sirf ADD COLUMN (backward compatible).

⚠️ PRODUCTION LESSON — "NOT NULL column add karna existing table pe":
   Table mein pehle se rows hain. Agar seedha `nullable=False` column add karo to
   Postgres ko purani rows ke liye value nahi pata → migration FAIL:
       psycopg2.errors.NotNullViolation: column "class_name" contains null values
   Solution = 2 step:
       1) `server_default` ke saath add karo (purani rows ko default mil jayega)
       2) phir `server_default` hata do (schema ko model ke saath match rakho —
          warna future `alembic autogenerate` "default hataya ja raha hai" dikhayega)
   Ye pattern har NOT NULL column addition pe yaad rakhna.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "a3c7e9f1b2d4"
down_revision: Union[str, Sequence[str], None] = "f7d9a1b2c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Naye columns: (name, type, server_default)
# server_default sirf add karne ke waqt chahiye — neeche hata diya jata hai.
_TEXT_COLUMNS = [
    ("class_name", sqlmodel.sql.sqltypes.AutoString(), ""),
    ("subject", sqlmodel.sql.sqltypes.AutoString(), ""),
    ("board", sqlmodel.sql.sqltypes.AutoString(), ""),
    ("exam_type", sqlmodel.sql.sqltypes.AutoString(), ""),
    ("language", sqlmodel.sql.sqltypes.AutoString(), "English"),
]

_JSON_COLUMNS = [
    ("chapters", "[]"),
    ("sources", "[]"),
    ("instructions", "[]"),
    ("scope", "{}"),
    ("constraints", "{}"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # ---- Step 1: server_default ke saath add (purani rows safe) ----
    for name, col_type, default in _TEXT_COLUMNS:
        op.add_column(
            "paperdraft",
            sa.Column(name, col_type, nullable=False, server_default=default),
        )

    for name, default in _JSON_COLUMNS:
        op.add_column(
            "paperdraft",
            sa.Column(
                name,
                sa.JSON(),
                nullable=False,
                server_default=sa.text(f"'{default}'::json"),
            ),
        )

    # ---- Step 2: server_default hata do (model = source of truth) ----
    for name, _, _ in _TEXT_COLUMNS:
        op.alter_column("paperdraft", name, server_default=None)

    for name, _ in _JSON_COLUMNS:
        op.alter_column("paperdraft", name, server_default=None)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema — ulta kram (last added, first dropped)."""
    for name, _ in reversed(_JSON_COLUMNS):
        op.drop_column("paperdraft", name)

    for name, _, _ in reversed(_TEXT_COLUMNS):
        op.drop_column("paperdraft", name)
    # ### end Alembic commands ###
