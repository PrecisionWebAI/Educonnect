"""Drop employee.role_codename - roles now live only in user_role.

Revision ID: f4e5f6a7b8c9
Revises: f3d4e5f6a7b8
Create Date: 2026-11-02

Why:
  A single `role_codename` column can only describe one role, but a person may
  hold several (a principal who also teaches, a teacher who also runs the
  library). The roles a person holds are the rows in `user_role` - which is also
  where permissions resolve from - so keeping a second copy on `employee` was
  both redundant and the thing that stopped multi-role from working.

  Before the column is dropped, any role it still names is written into
  `user_role` (idempotently), so no existing employee loses their role.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "f3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Back-fill user_role from the column, then drop it."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employee")}
    if "role_codename" not in columns:
        return

    # Every employee's role becomes a user_role row unless they already hold it.
    op.execute(
        """
        INSERT INTO user_role (user_id, role_id, is_primary, assigned_at)
        SELECT e.user_id, r.id, TRUE, now()
        FROM employee e
        JOIN role r ON r.codename = e.role_codename
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role ur
            WHERE ur.user_id = e.user_id AND ur.role_id = r.id
        )
        """
    )

    op.drop_column("employee", "role_codename")


def downgrade() -> None:
    """Put the column back (filled from the primary role where one exists)."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employee")}
    if "role_codename" in columns:
        return

    op.add_column(
        "employee",
        sa.Column(
            "role_codename", sa.String(), nullable=False, server_default="staff"
        ),
    )
    op.execute(
        """
        UPDATE employee e
        SET role_codename = r.codename
        FROM user_role ur
        JOIN role r ON r.id = ur.role_id
        WHERE ur.user_id = e.user_id AND ur.is_primary
        """
    )
    op.alter_column("employee", "role_codename", server_default=None)
