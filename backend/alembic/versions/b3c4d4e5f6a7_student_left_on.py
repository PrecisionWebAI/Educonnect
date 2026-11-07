"""The day a student left the roll.

Revision ID: b3c4d4e5f6a7
Revises: a1f2b3c4d5e6
Create Date: 2026-11-06

Why
---
A student who leaves is **deactivated, not deleted** (`students/lifecycle.py`): the
registers, marks and fees of the years they were here have to stay readable, and their
login is never switched off - a child who left is still a child here, and the account
that usually signs in belongs to their guardian anyway.

`student.deactivated_at` (already there) says when the school pressed the button.
`left_on` says the day the office says they left, which can be **back-dated**: a child
who stopped coming in April is recorded as having left in April, even when the office
only gets round to it in July. `employee` carries both already - this brings the student
row level with it, so the two screens answer "when did they leave?" the same way.

Nothing is backfilled: `NULL` means "still on the roll", which is what every existing row
is.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d4e5f6a7"
down_revision: str | None = "a1f2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("student", sa.Column("left_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("student", "left_on")
