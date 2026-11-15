"""A notification gains its event, its subject and its dedupe key.

Why
---
The bell worked but nothing said *why* a row existed, and "one message per event per
person" was a promise in a service rather than a rule in the database: two saves of the
same attendance day could send two "your child is absent" messages.

What changes
------------
* `notification.event_type` (+ index), `entity_type`, `entity_id`, `dedupe_key`,
  `channel` (default `in_app` - the only delivery implemented today);
* a **partial** unique index `(user_id, dedupe_key) WHERE dedupe_key IS NOT NULL`:
  rows that name a key are unique per person, rows that do not are free to repeat;
* `(school_id, user_id, created_at)` - the bell reads this person's newest rows.

The guard prints the counts it checks. Existing rows all carry a NULL key, so a
duplicate is impossible on day one; the check exists so a re-run on a database where
somebody *did* write keys by hand stops instead of failing halfway.

Downgrade
---------
Drops the indexes and the columns; every existing message stays readable (`title`,
`body`, `kind`, `read`, `created_at` are untouched).

Revision ID: c8e2f5a1d7b3
Revises: b7c1d4e9a3f2
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e2f5a1d7b3"
down_revision: str | Sequence[str] | None = "b7c1d4e9a3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine, bool], ...] = (
    ("event_type", sa.String(), True),
    ("entity_type", sa.String(), True),
    ("entity_id", sa.Uuid(), True),
    ("dedupe_key", sa.String(), True),
    ("channel", sa.String(), False),
)

DEDUPE_INDEX = "uq_notification_user_dedupe_key"
BELL_INDEX = "ix_notification_school_user_created"
EVENT_INDEX = "ix_notification_event_type"


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table)
        if item.get("name")
    }


def _assert_no_duplicates() -> None:
    """Print - and refuse - if two rows already share a person and a key."""
    if not _has_table("notification"):
        return
    duplicates = int(
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT count(*) FROM (
                    SELECT user_id, dedupe_key
                    FROM notification
                    WHERE dedupe_key IS NOT NULL
                    GROUP BY user_id, dedupe_key
                    HAVING count(*) > 1
                ) AS dupes
                """
            )
        )
        .scalar_one()
    )
    print(f"[notification] {duplicates} duplicate (user_id, dedupe_key) group(s)")
    if duplicates:
        raise RuntimeError(
            f"[notification] refusing to add {DEDUPE_INDEX}: {duplicates} "
            "(user_id, dedupe_key) group(s) hold more than one row. Nothing was "
            "changed - merge them, then run this again."
        )


def upgrade() -> None:
    if not _has_table("notification"):
        return

    columns = _columns("notification")

    for name, type_, nullable in NEW_COLUMNS:
        if name in columns:
            continue
        if name == "channel":
            # Existing rows need a delivery value; the server default is what fills
            # them, and it stays as the column's default for inserts that omit it.
            op.add_column(
                "notification",
                sa.Column(
                    name, type_, nullable=False, server_default=sa.text("'in_app'")
                ),
            )
        else:
            op.add_column("notification", sa.Column(name, type_, nullable=nullable))

    # Only now can the key be scanned - and only now does the scan mean anything.
    _assert_no_duplicates()

    indexes = _indexes("notification")
    if DEDUPE_INDEX not in indexes:
        op.create_index(
            DEDUPE_INDEX,
            "notification",
            ["user_id", "dedupe_key"],
            unique=True,
            postgresql_where=sa.text("dedupe_key IS NOT NULL"),
            sqlite_where=sa.text("dedupe_key IS NOT NULL"),
        )
    if BELL_INDEX not in indexes:
        op.create_index(
            BELL_INDEX, "notification", ["school_id", "user_id", "created_at"]
        )
    if EVENT_INDEX not in indexes:
        op.create_index(EVENT_INDEX, "notification", ["event_type"])


def downgrade() -> None:
    if not _has_table("notification"):
        return

    indexes = _indexes("notification")
    for name in (DEDUPE_INDEX, BELL_INDEX, EVENT_INDEX):
        if name in indexes:
            op.drop_index(name, table_name="notification")

    columns = _columns("notification")
    for name, _, _ in reversed(NEW_COLUMNS):
        if name in columns:
            op.drop_column("notification", name)
