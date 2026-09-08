"""Sync roleenum with RoleEnum model

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-08

The initial migration created the PostgreSQL enum type `roleenum` with a
stale set of values. The `RoleEnum` model has since gained several roles
(class_teacher, subject_teacher, guardian, librarian, transport, staff) that
were never added to the DB type, so inserting any user with those roles
(including the demo seed data) fails with:

    invalid input value for enum roleenum: "class_teacher"

This migration adds the missing values so seed data and new users work.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Values present in app.domains.users.models.RoleEnum but missing from the
# DB enum type created by the initial migration (8688cdb7b555).
MISSING_ROLES = (
    'class_teacher',
    'subject_teacher',
    'guardian',
    'librarian',
    'transport',
    'staff',
)


def upgrade() -> None:
    """Add missing role values to the roleenum enum type."""
    for role in MISSING_ROLES:
        # IF NOT EXISTS keeps this idempotent for databases that were
        # recreated with a newer snapshot of the type.
        op.execute(f"ALTER TYPE roleenum ADD VALUE IF NOT EXISTS '{role}'")


def downgrade() -> None:
    """No-op: PostgreSQL cannot remove values from an enum type without
    recreating it. The extra values are harmless to older revisions."""
    pass
