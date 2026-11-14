"""Money columns to `numeric(12,2)` - six columns, no float left in the money path.

Revision ID: d3a8e6b1c4f9
Revises: c1f6d2b8e4a7
Create Date: 2026-11-14

Why
---
Rule 4: money is `numeric(12,2)`, never float. Six columns held floats, which means
₹1,00,000.10 could round-trip as 100000.09999999999 and a register's total could
disagree with the sum of its rows by a paisa:

    feestructure.amount                     a fee head's amount
    feetransaction.amount_paid              what a family actually paid
    employeesalary.salary_monthly            a person's current salary
    salarypayment.gross / deductions / net   the monthly register

The `USING <column>::numeric(12,2)` cast is what makes this safe on existing rows:
PostgreSQL converts in place and rounds to two places exactly once. The API keeps
serving `float` (the wire format the screens already do arithmetic with); only the
**storage** becomes exact - see the note in the models.

Downgrade casts back to `double precision`, which loses nothing that was stored
(two decimal places survive a float round-trip at these magnitudes) but does put the
column back to a type that can be inexact - which is the point of the upgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3a8e6b1c4f9"
down_revision: str | Sequence[str] | None = "c1f6d2b8e4a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(12, 2)

#: table -> the columns that hold money.
COLUMNS: dict[str, tuple[str, ...]] = {
    "feestructure": ("amount",),
    "feetransaction": ("amount_paid",),
    "employeesalary": ("salary_monthly",),
    "salarypayment": ("gross", "deductions", "net"),
    "employee": ("previous_employer_monthly_salary",),
}


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns_of(table: str) -> set[str]:
    if not _has_table(table):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        present = _columns_of(table)
        for column in columns:
            if column not in present:
                continue
            op.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                f'TYPE numeric(12,2) USING "{column}"::numeric(12,2)'
            )


def downgrade() -> None:
    for table, columns in COLUMNS.items():
        present = _columns_of(table)
        for column in columns:
            if column not in present:
                continue
            op.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                f'TYPE double precision USING "{column}"::double precision'
            )
