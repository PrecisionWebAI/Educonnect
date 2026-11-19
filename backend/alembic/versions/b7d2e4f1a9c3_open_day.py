"""The one date a school reopens although a rule closes it.

A weekly off (every Sunday, "the 2nd Saturday") and a holiday row close a day for the whole
school. Sometimes the school opens on one of those dates anyway - an exam, a make-up class -
and the calendar has to say so without unsaving the rule: toggling "Sunday off" off and on
again would reopen every Sunday of the year.

`school_open_day` is that answer, one row per date, and it beats every other rule for that
date only (`admin/settings/calendar.closures` reads it first). Nothing is backfilled and no
existing row changes: a school with no overrides reads exactly as it did before.

Revision ID: b7d2e4f1a9c3
Revises: a9c4e1f7b3d6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d2e4f1a9c3"
down_revision: str | Sequence[str] | None = "a9c4e1f7b3d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "school_open_day" in _tables():
        return

    op.create_table(
        "school_open_day",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "on_date", name="uq_open_day_school_date"),
    )
    op.create_index("ix_school_open_day_school_id", "school_open_day", ["school_id"])
    op.create_index("ix_school_open_day_on_date", "school_open_day", ["on_date"])
    op.create_index(
        "ix_school_open_day_created_by_id", "school_open_day", ["created_by_id"]
    )


def downgrade() -> None:
    if "school_open_day" not in _tables():
        return

    op.drop_index("ix_school_open_day_created_by_id", table_name="school_open_day")
    op.drop_index("ix_school_open_day_on_date", table_name="school_open_day")
    op.drop_index("ix_school_open_day_school_id", table_name="school_open_day")
    op.drop_table("school_open_day")
