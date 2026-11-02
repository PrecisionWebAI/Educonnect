"""Rename employee.previous_salary_monthly to previous_employer_monthly_salary.

Revision ID: f1b2c3d4e5f6
Revises: d1e3f5a7b9c2
Create Date: 2026-11-02

Why:
  The hire form collects the applicant's salary at their *previous employer*.
  The column was created as `previous_salary_monthly`, which says neither whose
  salary nor when - and the Python model had drifted to a misspelled
  `previous_empoyer_monthly_salary`, so every `employee` SELECT failed with
  "column employee.previous_empoyer_monthly_salary does not exist". This
  migration makes the database column the correct
  `previous_employer_monthly_salary`, which is the name the model now uses.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d1e3f5a7b9c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename the column (idempotent: skipped when already renamed)."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employee")}
    if (
        "previous_salary_monthly" in columns
        and "previous_employer_monthly_salary" not in columns
    ):
        op.alter_column(
            "employee",
            "previous_salary_monthly",
            new_column_name="previous_employer_monthly_salary",
        )


def downgrade() -> None:
    """Put the old column name back."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employee")}
    if (
        "previous_employer_monthly_salary" in columns
        and "previous_salary_monthly" not in columns
    ):
        op.alter_column(
            "employee",
            "previous_employer_monthly_salary",
            new_column_name="previous_salary_monthly",
        )
