"""A student may exist without a login.

Revision ID: f9e0f1a2b3d1
Revises: f9e0f1a2b3d0
Create Date: 2026-11-03

Logins are no longer invented. An admission form that carries no student email
creates the student **without** a login (the guardian still gets one, from their
email or phone), so `studentprofile.user_id` has to allow `NULL`.

The student's own name used to live only on the login (`user.full_name`), which a
student without a login does not have - so it is copied onto the profile here and
backfilled for every student that already exists.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3d1"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE studentprofile ADD COLUMN IF NOT EXISTS full_name varchar")
    # Every student that already exists keeps their name: it is read from the login
    # they were created with.
    op.execute(
        'UPDATE studentprofile sp SET full_name = u.full_name '
        'FROM "user" u WHERE u.id = sp.user_id AND sp.full_name IS NULL'
    )
    op.execute("ALTER TABLE studentprofile ALTER COLUMN user_id DROP NOT NULL")


def downgrade() -> None:
    # A student without a login cannot be represented by the old shape; the rows that
    # would break the constraint are removed rather than left half-migrated.
    op.execute("DELETE FROM studentprofile WHERE user_id IS NULL")
    op.execute("ALTER TABLE studentprofile ALTER COLUMN user_id SET NOT NULL")
    op.execute("ALTER TABLE studentprofile DROP COLUMN IF EXISTS full_name")
