"""Unique keys the models declare but the database never got, + no teacher double-booking.

Revision ID: c1f6d2b8e4a7
Revises: b7e4c1a9f2d3
Create Date: 2026-11-14

Why
---
`School.code`, `.name` and `.email` are declared `unique=True` in the model, and
`employee.employee_code` is declared unique too - but the live database only carries
**plain** indexes for the three school keys and a *global* unique index for the employee
code. So the schema was weaker than the code believed:

* two schools could share a login slug and the app would happily create both;
* two schools could never reuse `EMP-0001` - which is the real business case the
  composite key exists for.

This revision makes the database say what the models say, per school where that is the
rule:

    uq_school_code                     school (code)
    uq_school_name                     school (name)
    uq_school_email                    school (email)
    uq_employee_school_code            employee (school_id, employee_code)
    uq_timetableperiod_teacher_slot    timetableperiod (school_id, teacher_id,
                                                      day_of_week, start_time)

The last one is the "one teacher cannot be in two rooms at 09:00" rule. It is an
index rather than a constraint because the school_id is part of the key exactly the
way the tenant filter reads it.

Checked before writing: 0 duplicate rows and 0 NULLs for every key above, and 0
double-booked slots in `timetableperiod` - so this applies to the current data
without a cleanup step (a migration that deletes rows is not a migration, it is a
decision somebody has to make).

Downgrade drops the five indexes and restores the four it replaced, including the
**global** unique employee code - i.e. the old (weaker for schools, stricter for
employees) shape.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f6d2b8e4a7"
down_revision: str | Sequence[str] | None = "b7e4c1a9f2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (index name, table, columns) - the keys this revision adds.
CREATE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("uq_school_code", "school", ("code",)),
    ("uq_school_name", "school", ("name",)),
    ("uq_school_email", "school", ("email",)),
    ("uq_employee_school_code", "employee", ("school_id", "employee_code")),
    (
        "uq_timetableperiod_teacher_slot",
        "timetableperiod",
        ("school_id", "teacher_id", "day_of_week", "start_time"),
    ),
)

#: The indexes this revision retires (non-unique school keys, global employee code).
REPLACED: tuple[str, ...] = (
    "ix_school_code",
    "ix_school_name",
    "ix_school_email",
    "ix_employee_employee_code",
)


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    for name, table, columns in CREATE:
        if _has_table(table):
            joined = ", ".join(f'"{column}"' for column in columns)
            op.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{name}" ON "{table}" ({joined})'
            )
    for name in REPLACED:
        op.execute(f'DROP INDEX IF EXISTS "{name}"')


def downgrade() -> None:
    for name, _table, _columns in reversed(CREATE):
        op.execute(f'DROP INDEX IF EXISTS "{name}"')

    if _has_table("school"):
        op.execute('CREATE INDEX IF NOT EXISTS "ix_school_code" ON "school" (code)')
        op.execute('CREATE INDEX IF NOT EXISTS "ix_school_name" ON "school" (name)')
        op.execute('CREATE INDEX IF NOT EXISTS "ix_school_email" ON "school" (email)')
    if _has_table("employee"):
        # Back to the global rule this revision replaced.
        op.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS "ix_employee_employee_code" '
            'ON "employee" (employee_code)'
        )
