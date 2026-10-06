"""Drop the redundant unique constraint on `permission.codename`

Revision ID: f1a2b3c4d5e6
Revises: e9b4c1a7d2f6
Create Date: 2026-10-04

Why:
  `permission.codename` carries **two** uniqueness guarantees in the live
  database:

    * the unique index `ix_permission_codename` - what the SQLModel class
      declares (`unique=True, index=True`), and
    * a leftover unique *constraint* `permission_codename_key` from the RBAC
      migrations.

  The SQLModel classes are the source of truth for the schema (section 22 of
  `info/db_design.md`), and the index already enforces the same rule, so the
  constraint is dropped to bring the database back in step with the models -
  it was the one change every `--autogenerate` run kept proposing.

  Nothing changes behaviourally: inserting a duplicate codename still fails on
  the unique index.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e9b4c1a7d2f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("permission_codename_key", "permission", type_="unique")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint("permission_codename_key", "permission", ["codename"])
