"""Drop `user.contact_email` — the login email is now the real email.

Revision ID: d6f3e8b2c1a4
Revises: c8e4f2a9d1b7
Create Date: 2026-10-28

Why:
  `user.contact_email` existed to hold the person's real address while the login
  was a generated `stu.*` / `gau.*` address. Logins now use the email the form
  supplied directly, so the separate column is redundant and removed.

Downgrade re-adds the nullable column (no index is recreated on downgrade).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6f3e8b2c1a4"
down_revision: str | Sequence[str] | None = "c8e4f2a9d1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("ix_user_contact_email", table_name="user")
    op.drop_column("user", "contact_email")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user", sa.Column("contact_email", _AUTO_STR(), nullable=True)
    )
    op.create_index("ix_user_contact_email", "user", ["contact_email"], unique=False)
