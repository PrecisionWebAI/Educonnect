"""GenerationJob: nullable paper_id + config/result snapshot (stateless generate)

Revision ID: c4d8f2a1b9e3
Revises: a3c7e9f1b2d4
Create Date: 2026-09-25

Kya karta hai (teen chhote badlav — sab backward compatible):
  1. `generationjob.paper_id` → **NULLABLE**
     Kyun: stateless generate (`POST /exams/generate`) mein teacher ka blueprint
     DB mein save nahi hota, isliye job kisi paper se juda nahi hota.
  2. `config_snapshot` JSON NOT NULL DEFAULT '{}'
     Poora teacher config (Basics + Source + Blueprint + Coverage + part_b) job
     ke saath freeze — reproducible + audit-able, bina paperdraft row banaye.
  3. `result_snapshot` JSON NOT NULL DEFAULT '{}'
     Stateless flow ke generated questions + summary + quality + coverage report.

⚠️ NOT NULL column add karne ka safe pattern (`a3c7e9f1b2d4` se hi):
   pehle `server_default` ke saath add karo (purani rows ko default milega),
   phir default **hata do** — warna future `alembic autogenerate` har baar
   "default hataya ja raha hai" dikhata rehta hai.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d8f2a1b9e3"
down_revision: Union[str, Sequence[str], None] = "a3c7e9f1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_JSON_COLUMNS = ["config_snapshot", "result_snapshot"]


def upgrade() -> None:
    """Upgrade schema."""
    # ---- 1) paper_id nullable (stateless job ka koi paper nahi hota) ----
    op.alter_column(
        "generationjob",
        "paper_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # ---- 2) naye JSON columns: pehle default ke saath add ----
    for name in _JSON_COLUMNS:
        op.add_column(
            "generationjob",
            sa.Column(
                name,
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
        )

    # ---- 3) default hata do (model = source of truth) ----
    for name in _JSON_COLUMNS:
        op.alter_column("generationjob", name, server_default=None)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema — ulta kram (last added, first dropped)."""
    for name in reversed(_JSON_COLUMNS):
        op.drop_column("generationjob", name)

    # nullables ko wapas NOT NULL karna tab hi possible hai jab NULL rows hi na ho
    # (stateless jobs). Warna Postgres NotNullViolation dega — isliye pehle NULL
    # rows delete kar dete hain (downgrade ka matlab hi hai "stateless flow hatao").
    op.execute("DELETE FROM generationjob WHERE paper_id IS NULL")
    op.alter_column(
        "generationjob",
        "paper_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    # ### end Alembic commands ###
