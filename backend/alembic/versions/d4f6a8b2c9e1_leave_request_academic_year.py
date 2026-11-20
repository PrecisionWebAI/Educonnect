"""Leave requests carry the academic year they start in.

Revision ID: d4f6a8b2c9e1
Revises: c9e3a5b7d1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4f6a8b2c9e1"
down_revision: str | Sequence[str] | None = "c9e3a5b7d1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "leaverequest" not in tables:
        return
    if "academic_year_id" not in _columns("leaverequest"):
        op.add_column(
            "leaverequest",
            sa.Column("academic_year_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_leaverequest_academic_year",
            "leaverequest",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_leaverequest_academic_year_id",
            "leaverequest",
            ["academic_year_id"],
        )

    if "academic_year" in tables:
        op.execute(
            """
            UPDATE leaverequest AS l
               SET academic_year_id = a.id
              FROM academic_year AS a
             WHERE a.school_id = l.school_id
               AND l.from_date BETWEEN a.start_date AND a.end_date
               AND l.academic_year_id IS NULL
            """
        )

        if "holiday" in tables:
            op.execute(
                """
                UPDATE holiday AS h
                   SET academic_year_id = a.id
                  FROM academic_year AS a
                 WHERE a.school_id = h.school_id
                   AND h.on_date BETWEEN a.start_date AND a.end_date
                   AND h.academic_year_id IS NULL
                """
            )

        if "exam" in tables:
            op.execute(
                """
                UPDATE exam AS e
                   SET academic_year_id = a.id
                  FROM academic_year AS a
                 WHERE a.school_id = e.school_id
                   AND COALESCE(e.start_date, e.end_date)
                       BETWEEN a.start_date AND a.end_date
                   AND e.academic_year_id IS NULL
                """
            )


def downgrade() -> None:
    if "academic_year_id" not in _columns("leaverequest"):
        return
    op.drop_index("ix_leaverequest_academic_year_id", table_name="leaverequest")
    op.drop_constraint(
        "fk_leaverequest_academic_year", "leaverequest", type_="foreignkey"
    )
    op.drop_column("leaverequest", "academic_year_id")
