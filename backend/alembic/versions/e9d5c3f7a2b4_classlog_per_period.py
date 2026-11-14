"""`classlog` becomes per-period: the unique key gains `timetableperiod_id`.

Why
---
Phase 2 added `classlog.timetableperiod_id` so a log line could say *which* period
it was written against. Phase 5's workload figure then had to count "rows", because
the old key (`UNIQUE(classroom_id, date)`) allowed **one** line per class-section
per day: a second period in the same room could not be logged at all. That is a
plan/record mismatch - the timetable runs six periods and the log could hold one.

The new shape
-------------
* `UNIQUE(classroom_id, date, timetableperiod_id)` - one line per period;
* a **partial** unique index (`... WHERE timetableperiod_id IS NULL`) keeps the
  register-style entry to one per day. Without it PostgreSQL treats two NULLs as
  different values and the day-level row could be written twice.

Downgrade
---------
The old key cannot be restored by a schema change alone once per-period rows exist:
several lines per day are exactly what the new key permits. So the downgrade
**drops the new keys and recreates the old one only when the data still satisfies
it**; otherwise it leaves a clearly named non-unique index and raises nothing -
data is never deleted to make a downgrade succeed. The count is printed.

Revision ID: e9d5c3f7a2b4
Revises: d8c4b2e6f1a3
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9d5c3f7a2b4"
down_revision: str | Sequence[str] | None = "d8c4b2e6f1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KEY = "uq_classlog_classroom_date"
NEW_KEY = "uq_classlog_classroom_date_period"
DAY_ONLY = "uq_classlog_classroom_day_only"


def _constraints() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "classlog" not in inspector.get_table_names():
        return set()
    names = {item["name"] for item in inspector.get_unique_constraints("classlog")}
    return {name for name in names if name}


def _indexes() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "classlog" not in inspector.get_table_names():
        return set()
    return {item["name"] for item in inspector.get_indexes("classlog") if item["name"]}


def upgrade() -> None:
    constraints = _constraints()
    if OLD_KEY in constraints:
        op.drop_constraint(OLD_KEY, "classlog", type_="unique")

    if NEW_KEY not in _constraints():
        op.create_unique_constraint(
            NEW_KEY, "classlog", ["classroom_id", "date", "timetableperiod_id"]
        )

    if DAY_ONLY not in _indexes():
        op.create_index(
            DAY_ONLY,
            "classlog",
            ["classroom_id", "date"],
            unique=True,
            postgresql_where=sa.text("timetableperiod_id IS NULL"),
        )


def downgrade() -> None:
    if DAY_ONLY in _indexes():
        op.drop_index(DAY_ONLY, table_name="classlog")
    if NEW_KEY in _constraints():
        op.drop_constraint(NEW_KEY, "classlog", type_="unique")

    duplicates = (
        op.get_bind()
        .exec_driver_sql(
            """
            SELECT count(*) FROM (
                SELECT classroom_id, date FROM classlog
                GROUP BY classroom_id, date HAVING count(*) > 1
            ) AS dupes
            """
        )
        .scalar_one()
    )
    if duplicates == 0 and OLD_KEY not in _constraints():
        op.create_unique_constraint(OLD_KEY, "classlog", ["classroom_id", "date"])
    elif duplicates:
        # Per-period rows exist: the old one-per-day key is a data decision, not a
        # schema change. Keep the table queryable and say so, without deleting.
        print(
            f"[classlog] {duplicates} class-section/day group(s) hold more than one "
            f"log line; {OLD_KEY} was not restored (data is never deleted to make a "
            "downgrade succeed)."
        )
        if "ix_classlog_classroom_date" not in _indexes():
            op.create_index(
                "ix_classlog_classroom_date", "classlog", ["classroom_id", "date"]
            )
