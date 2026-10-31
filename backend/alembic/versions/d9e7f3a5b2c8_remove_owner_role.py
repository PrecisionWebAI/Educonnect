"""Remove the `owner` role - it is no longer a platform or school role.

Revision ID: d9e7f3a5b2c8
Revises: c7d4b8e2f6a9
Create Date: 2026-10-21

Why:
  `owner` duplicated `school_admin` (both held "everything except impersonation"),
  and the platform side is already covered by `system_admin`. Keeping it meant two
  roles that meant the same thing, so it is dropped.

  The role was DATA (seeded by `role_catalog.py`), so the app-level seed stops
  recreating it; this migration removes the rows an already-seeded database has.
  No user is expected to hold `owner` (the seed only mints `school_admin`), but
  `user_role` rows are removed first just in case.

Downgrade recreates the role and restores its grants (all permissions except
`users.impersonate`), matching the removed `OWNER_PERMISSIONS`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e7f3a5b2c8"
down_revision: str | Sequence[str] | None = "c7d4b8e2f6a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _owner_role_id() -> int | None:
    return (
        op.get_bind()
        .execute(sa.text("SELECT id FROM role WHERE codename = 'owner'"))
        .scalar()
    )


def upgrade() -> None:
    owner_id = _owner_role_id()
    if owner_id is None:
        return
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM rolepermission WHERE role_id = :rid"), {"rid": owner_id})
    conn.execute(sa.text("DELETE FROM user_role WHERE role_id = :rid"), {"rid": owner_id})
    conn.execute(sa.text("DELETE FROM role WHERE id = :rid"), {"rid": owner_id})


def downgrade() -> None:
    if _owner_role_id() is not None:
        return
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO role (codename, label, description, is_system) "
            "VALUES ('owner', 'Owner', 'Proprietor of the school; sees everything.', true)"
        )
    )
    owner_id = _owner_role_id()
    conn.execute(
        sa.text(
            """
            INSERT INTO rolepermission (role_id, permission_id)
            SELECT :rid, p.id FROM permission p
            WHERE p.codename <> 'users.impersonate'
            """
        ),
        {"rid": owner_id},
    )
