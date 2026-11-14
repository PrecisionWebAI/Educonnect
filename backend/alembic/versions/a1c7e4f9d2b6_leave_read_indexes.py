"""Indexes for the two reads every staff screen makes of `leaverequest`.

Revision ID: a1c7e4f9d2b6
Revises: f6d3b9c4e8a2
Create Date: 2026-11-14

Why
---
The month sheet (one person, one month) and the register (one day, everybody) both
asked `leaverequest` a question the table had no index for, so PostgreSQL scanned
every leave the school had ever filed to answer it. Against a database reached over
the network - this project's is a hosted Postgres - that showed up as a visible wait
when a month was opened, and it grew with every leave filed.

    ix_leaverequest_school_status_window     (school_id, status, from_date)
        "who is on leave on this day?" - range test on the approved rows.

    ix_leaverequest_school_requester_status  (school_id, requester_user_id, status)
        "how many days has this person taken?" - one person's month, and the
        balance SUM in `services/leave`.

The reads were already batched (no query per person); what was missing was the
index, and in `month()` the scope: it asked for **every** colleague's leave and then
kept one person's. Both are fixed here - the query narrows by `requester_user_id`,
and these indexes are what the narrowed query uses.

`IF NOT EXISTS` / `IF EXISTS` keep the revision re-runnable, for the same reason the
Phase 6 revision guards every `ADD COLUMN`: a database created by
`create_missing()` is stamped at head and gets these indexes from `create_all`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c7e4f9d2b6"
down_revision: str | Sequence[str] | None = "f6d3b9c4e8a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: name -> the columns, in the order the index stores them.
INDEXES: dict[str, tuple[str, ...]] = {
    "ix_leaverequest_school_status_window": ("school_id", "status", "from_date"),
    "ix_leaverequest_school_requester_status": (
        "school_id",
        "requester_user_id",
        "status",
    ),
}


def _indexed(name: str) -> bool:
    """Whether `leaverequest` already carries this index."""
    inspector = sa.inspect(op.get_bind())
    if "leaverequest" not in inspector.get_table_names():
        return True  # nothing to index; `create_all` owns that database
    return name in {index["name"] for index in inspector.get_indexes("leaverequest")}


def upgrade() -> None:
    for name, columns in INDEXES.items():
        if _indexed(name):
            continue
        op.create_index(name, "leaverequest", list(columns))


def downgrade() -> None:
    for name in INDEXES:
        if _indexed(name):
            op.drop_index(name, table_name="leaverequest")
