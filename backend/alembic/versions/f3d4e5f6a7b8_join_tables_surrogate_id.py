"""Give user_role and rolepermission an auto-increment `id`.

Revision ID: f3d4e5f6a7b8
Revises: f2c3d4e5f6a7
Create Date: 2026-11-02

Why:
  Every table should be addressable by an auto-increment `id` so rows can be
  linked by id / foreign key without relying on a composite natural key. The two
  RBAC join tables were the only tables without one (their composite key doubled
  as the uniqueness rule). This migration:

  * adds `id` (SERIAL, so existing rows are numbered too) and makes it the
    primary key, and
  * keeps the real rule as a UNIQUE constraint - `(user_id, role_id)` for
    `user_role`, `(role_id, permission_id)` for `rolepermission`.

  It also renames the two `rolepermission_new_*_fkey` foreign keys (left over
  from an earlier migration) to the plain convention, so autogenerate stops
  reporting them as drift.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "f2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the `id` primary keys and the uniqueness constraints."""
    # --- user_role ---------------------------------------------------------
    op.execute("ALTER TABLE user_role ADD COLUMN IF NOT EXISTS id SERIAL")
    op.execute("ALTER TABLE user_role DROP CONSTRAINT IF EXISTS user_role_pkey")
    op.execute("ALTER TABLE user_role ADD CONSTRAINT user_role_pkey PRIMARY KEY (id)")
    op.execute(
        "ALTER TABLE user_role ADD CONSTRAINT uq_user_role_user_role "
        "UNIQUE (user_id, role_id)"
    )

    # --- rolepermission ----------------------------------------------------
    op.execute("ALTER TABLE rolepermission ADD COLUMN IF NOT EXISTS id SERIAL")
    op.execute(
        "ALTER TABLE rolepermission DROP CONSTRAINT IF EXISTS rolepermission_new_pkey"
    )
    op.execute(
        "ALTER TABLE rolepermission DROP CONSTRAINT IF EXISTS rolepermission_pkey"
    )
    op.execute(
        "ALTER TABLE rolepermission ADD CONSTRAINT rolepermission_pkey "
        "PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE rolepermission ADD CONSTRAINT uq_rolepermission_role_permission "
        "UNIQUE (role_id, permission_id)"
    )
    # Tidy the misnamed foreign keys the earlier migration left behind.
    op.execute(
        "ALTER TABLE rolepermission RENAME CONSTRAINT "
        "rolepermission_new_role_id_fkey TO rolepermission_role_id_fkey"
    )
    op.execute(
        "ALTER TABLE rolepermission RENAME CONSTRAINT "
        "rolepermission_new_permission_id_fkey TO rolepermission_permission_id_fkey"
    )


def downgrade() -> None:
    """Put the composite primary keys back and drop the `id` columns."""
    # --- rolepermission ----------------------------------------------------
    op.execute(
        "ALTER TABLE rolepermission DROP CONSTRAINT IF EXISTS "
        "uq_rolepermission_role_permission"
    )
    op.execute(
        "ALTER TABLE rolepermission RENAME CONSTRAINT "
        "rolepermission_role_id_fkey TO rolepermission_new_role_id_fkey"
    )
    op.execute(
        "ALTER TABLE rolepermission RENAME CONSTRAINT "
        "rolepermission_permission_id_fkey TO rolepermission_new_permission_id_fkey"
    )
    op.execute("ALTER TABLE rolepermission DROP CONSTRAINT IF EXISTS rolepermission_pkey")
    op.execute(
        "ALTER TABLE rolepermission ADD CONSTRAINT rolepermission_new_pkey "
        "PRIMARY KEY (role_id, permission_id)"
    )
    op.execute("ALTER TABLE rolepermission DROP COLUMN IF EXISTS id")

    # --- user_role ---------------------------------------------------------
    op.execute(
        "ALTER TABLE user_role DROP CONSTRAINT IF EXISTS uq_user_role_user_role"
    )
    op.execute("ALTER TABLE user_role DROP CONSTRAINT IF EXISTS user_role_pkey")
    op.execute(
        "ALTER TABLE user_role ADD CONSTRAINT user_role_pkey "
        "PRIMARY KEY (user_id, role_id)"
    )
    op.execute("ALTER TABLE user_role DROP COLUMN IF EXISTS id")
