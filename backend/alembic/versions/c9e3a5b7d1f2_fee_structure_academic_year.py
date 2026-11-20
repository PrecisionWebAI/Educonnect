"""Fee heads belong to an academic year.

Revision ID: c9e3a5b7d1f2
Revises: b7e2f4a9c1d3
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9e3a5b7d1f2"
down_revision: str | Sequence[str] | None = "b7e2f4a9c1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "feestructure" not in tables:
        return

    if "academic_year_id" not in _columns("feestructure"):
        op.add_column(
            "feestructure",
            sa.Column("academic_year_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_feestructure_academic_year",
            "feestructure",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_feestructure_academic_year_id",
            "feestructure",
            ["academic_year_id"],
        )

    if "academic_year" in tables:
        op.execute(
            """
            UPDATE feestructure AS f
               SET academic_year_id = a.id
              FROM academic_year AS a
             WHERE a.school_id = f.school_id
               AND a.is_current = true
               AND f.academic_year_id IS NULL
            """
        )


def downgrade() -> None:
    if "academic_year_id" not in _columns("feestructure"):
        return
    op.drop_index("ix_feestructure_academic_year_id", table_name="feestructure")
    op.drop_constraint(
        "fk_feestructure_academic_year", "feestructure", type_="foreignkey"
    )
    op.drop_column("feestructure", "academic_year_id")
