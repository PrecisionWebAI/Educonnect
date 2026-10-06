"""Impersonation audit trail: one row per "admin viewed another account" session.

Revision ID: b4e7f1a2c9d3
Revises: a2c5e8b1d4f7
Create Date: 2026-10-04

Why:
  The platform administrator can switch the session to another account ("view
  as"), and the switched token records who did it in an `act` claim. A token is
  not an audit trail though - it lives in a browser and expires - so this table
  keeps the pair (actor, target) and when the switch started and ended. That is
  what makes "who looked at whose account" answerable after the fact, which is
  the whole point of having impersonation in a school system.

  No foreign key to `role`: `users.impersonate` is the permission that gates the
  feature (seeded from `auth/permissions.py`), and grants are data, so only the
  platform-admin role needs it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e7f1a2c9d3"
down_revision: str | Sequence[str] | None = "a2c5e8b1d4f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "impersonationlog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("reason", _AUTO_STR(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_impersonationlog_actor_user_id"),
        "impersonationlog",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_impersonationlog_target_user_id"),
        "impersonationlog",
        ["target_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_impersonationlog_target_user_id"), table_name="impersonationlog"
    )
    op.drop_index(
        op.f("ix_impersonationlog_actor_user_id"), table_name="impersonationlog"
    )
    op.drop_table("impersonationlog")
