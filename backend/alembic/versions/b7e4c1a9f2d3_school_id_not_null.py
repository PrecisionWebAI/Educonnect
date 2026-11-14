"""`school_id` NOT NULL (after a parent-based backfill) + the two missing indexes.

Revision ID: b7e4c1a9f2d3
Revises: e8b2f5c9a1d4
Create Date: 2026-11-14

Why
---
Rule 2 says every school-level table carries `school_id NOT NULL`. The column is
nullable in the models on purpose (`TenantMixin`) because `before_flush` stamps it
from the session, and because the platform admin legitimately has no school - so
"NOT NULL everywhere" had never been applied at the database either.

This revision measured the gap on the live database and closes it where it can:

    staffauditlog           3 rows with school_id NULL
    staffattendancerecord   3 rows with school_id NULL
    attendancerecord       15 rows with school_id NULL

Every one of those resolves through its parent (`employee` / `student`), and this
revision backfills them before tightening the column. If a row could **not** be
resolved, the column is left nullable and the migration does not pretend otherwise -
a boot that refuses to start is worse than a column that stays loose.

`user.school_id` stays nullable: the platform admin (`system_admin`) has no school by
design (`tenancy.SCHOOL_LESS_ROLES`), and making it NOT NULL would delete that role's
existence from the schema's point of view.

Also creates the two indexes `securitylog` and `chatfile` never got - they were added
by a revision that created their tables without the tenant index.

Downgrade drops NOT NULL and the two indexes. It does **not** re-introduce NULLs: the
backfilled value is the correct value, and putting the old gaps back would be a
deliberate data regression.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4c1a9f2d3"
down_revision: str | Sequence[str] | None = "e8b2f5c9a1d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: table -> (parent table, foreign-key column on the child)
BACKFILL: dict[str, tuple[str, str]] = {
    "staffauditlog": ("employee", "employee_id"),
    "staffattendancerecord": ("employee", "employee_id"),
    "attendancerecord": ("student", "student_id"),
}

#: The tenant indexes these two tables are missing.
MISSING_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_securitylog_school_id", "securitylog"),
    ("ix_chatfile_school_id", "chatfile"),
)


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _null_count(table: str) -> int:
    return int(
        op.get_bind()
        .execute(sa.text(f'SELECT count(*) FROM "{table}" WHERE school_id IS NULL'))
        .scalar_one()
    )


def upgrade() -> None:
    for table, (parent, key) in BACKFILL.items():
        if not (_has_table(table) and _has_table(parent)):
            continue
        op.execute(
            f'UPDATE "{table}" t SET school_id = p.school_id '
            f'FROM "{parent}" p WHERE t."{key}" = p.id AND t.school_id IS NULL'
        )
        # Only tighten what is actually complete; a leftover NULL keeps it nullable
        # and stays visible in the next audit rather than failing the boot.
        if _null_count(table) == 0:
            op.alter_column(table, "school_id", existing_type=sa.Uuid(), nullable=False)

    for name, table in MISSING_INDEXES:
        if _has_table(table):
            op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" (school_id)')


def downgrade() -> None:
    for name, table in MISSING_INDEXES:
        if _has_table(table):
            op.execute(f'DROP INDEX IF EXISTS {name}')

    for table in BACKFILL:
        if _has_table(table):
            op.alter_column(
                table, "school_id", existing_type=sa.Uuid(), nullable=True
            )
