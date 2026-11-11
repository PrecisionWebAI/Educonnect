"""Drop the two columns only the development database ever had.

`employee.date_of_birth` and `pipeline_hiring_table.referred_by` exist in the
local database but in **no model and no migration**: they were added by hand
while the forms were being built, nothing in `app/` reads or writes them, and a
database created from this chain never has them. `scripts/check_schema.py`
therefore reported them as drift - the code and the database disagreed, which is
exactly what must not be true when a second database (Supabase) is supposed to
look the same as the first.

Dropping them here makes every environment converge on the schema the code
declares. `IF EXISTS` matters: a fresh database (base -> head) has never had
these columns, and this revision still has to apply cleanly there.

The 483 employee birthdays were exported to `employee_date_of_birth.csv`
(outside the repo, next to the other dumps) before this ran, so nothing is lost
silently.

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE employee DROP COLUMN IF EXISTS date_of_birth")
    op.execute("ALTER TABLE pipeline_hiring_table DROP COLUMN IF EXISTS referred_by")


def downgrade() -> None:
    # Best effort: the columns come back empty, because their values came from the
    # hand-written shape, not from anything this chain writes.
    op.execute("ALTER TABLE employee ADD COLUMN IF NOT EXISTS date_of_birth date")
    op.execute(
        "ALTER TABLE pipeline_hiring_table "
        "ADD COLUMN IF NOT EXISTS referred_by character varying"
    )
