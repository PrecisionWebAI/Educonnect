"""`user` -> `app_user`: a reserved word is not a table name.

Revision ID: f2c7a4e9b6d1
Revises: e5b9c3a7f1d2
Create Date: 2026-11-14

Why
---
Rule 6 (and Q2's answer): rename `user` to `app_user`. `user` is a keyword in
PostgreSQL; quoting it everywhere works but is the kind of convention that survives
until somebody writes one query by hand. About thirty tables carry a foreign key to
it, so the rename has to be *only* a rename: `ALTER TABLE ... RENAME TO` keeps every
foreign key, index and constraint pointing at the same relation (PostgreSQL resolves
them by OID), and the models were updated in the same change - every
`foreign_key="user.id"` is `"app_user.id"` now.

Constraint **names** keep the old word (`user_pkey`, `uq_user_school_email`,
`fk_..._user_id`). Renaming them would be churn with a real risk of a missed
reference in a migration that runs later; the identifiers that matter to code are the
table and the columns, and those move.

Also note `create_missing()` reads `SQLModel.metadata`, so a fresh database now gets
`app_user` from `create_all` - the two paths (migration and boot) agree.

Downgrade renames the table back. Nothing else moves: the FKs follow the name in both
directions.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2c7a4e9b6d1"
down_revision: str | Sequence[str] | None = "e5b9c3a7f1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    names = _tables()
    if "user" in names and "app_user" not in names:
        op.execute('ALTER TABLE "user" RENAME TO app_user')


def downgrade() -> None:
    names = _tables()
    if "app_user" in names and "user" not in names:
        op.execute('ALTER TABLE app_user RENAME TO "user"')
