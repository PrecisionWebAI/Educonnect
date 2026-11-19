"""Holiday ranges and the person who added them.

The calendar needs two facts the `holiday` table did not keep:

* **the last day of a range** - "winter break, 24 Dec - 2 Jan" is one row, so the school
  edits one entry instead of nine, and a range may cross a month boundary;
* **who added it** - the list prints a name beside each holiday.

Nothing is backfilled: an existing row has no `end_date` (it is a single day, which is
exactly what `coalesce(end_date, on_date)` reads) and no `created_by_id` (the calendar
prints "—"). Both columns are nullable on purpose - inventing an author or an end date
for history would be a guess.

The weekly off days are **not** in this migration: they are one row in `school_setting`
(`attendance.weekly_off_days`), seeded with "6" by `settings/values.py`.

Revision ID: a9c4e1f7b3d6
Revises: d2a7f4c9e1b8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9c4e1f7b3d6"
down_revision: str | Sequence[str] | None = "d2a7f4c9e1b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("holiday")}


def upgrade() -> None:
    columns = _columns()

    if "end_date" not in columns:
        op.add_column("holiday", sa.Column("end_date", sa.Date(), nullable=True))

    if "created_by_id" not in columns:
        op.add_column("holiday", sa.Column("created_by_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "holiday_created_by_id_fkey",
            "holiday",
            "app_user",
            ["created_by_id"],
            ["id"],
        )
        op.create_index("ix_holiday_created_by_id", "holiday", ["created_by_id"])


def downgrade() -> None:
    columns = _columns()

    if "created_by_id" in columns:
        op.drop_index("ix_holiday_created_by_id", table_name="holiday")
        op.drop_constraint("holiday_created_by_id_fkey", "holiday", type_="foreignkey")
        op.drop_column("holiday", "created_by_id")

    if "end_date" in columns:
        op.drop_column("holiday", "end_date")
