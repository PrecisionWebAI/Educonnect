"""Rename the reserved-word columns: `user`/`when` were SQL keywords used as names.

Revision ID: e5b9c3a7f1d2
Revises: d3a8e6b1c4f9
Create Date: 2026-11-14

Why
---
Rule 6: do not use reserved words as names. Three columns broke it, and every read of
them needed quoting - which is the kind of thing that works until somebody writes a
query by hand:

    securitylog.user   -> actor_email     (the login the event is about)
    securitylog.when   -> occurred_at     (it is a timestamp, not "when")
    chatfile.when      -> shared_at

The names are also better than the originals: "user" did not say *which* user, and
"when" is not a type. The values are unchanged; only the labels move.

`ALTER TABLE ... RENAME COLUMN` keeps every index and constraint attached, so this is
a metadata change with no rewrite and no data movement.

Downgrade renames them back - the only case in this project where a downgrade restores
a worse name, because the alternative is a schema that no longer matches the models.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b9c3a7f1d2"
down_revision: str | Sequence[str] | None = "d3a8e6b1c4f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: table -> [(old, new)]
RENAMES: dict[str, tuple[tuple[str, str], ...]] = {
    "securitylog": (("user", "actor_email"), ("when", "occurred_at")),
    "chatfile": (("when", "shared_at"),),
}


def _columns_of(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    for table, pairs in RENAMES.items():
        present = _columns_of(table)
        for old, new in pairs:
            if old in present and new not in present:
                op.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')


def downgrade() -> None:
    for table, pairs in RENAMES.items():
        present = _columns_of(table)
        for old, new in pairs:
            if new in present and old not in present:
                op.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{new}" TO "{old}"')
