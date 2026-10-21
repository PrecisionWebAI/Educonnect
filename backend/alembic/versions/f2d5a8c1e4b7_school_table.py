"""Add the `school` table and `user.school_id` - the tenant boundary.

Revision ID: f2d5a8c1e4b7
Revises: e1c4b7a9f2d3
Create Date: 2026-10-21

Why:
  There was no school record at all - `info/db_design.md` listed the multi-school
  `school_id` as "not built yet" - so every account belonged to nothing and a
  `school_admin` had no boundary to be confined to.

  * `school` - the registration record: name, `code` (the slug logins are built
    from, `abc` -> `admin@abc`), contact email, phone, address, active flag.
  * `user.school_id` - which school an account belongs to. NULL for the platform
    roles (`system_admin`, `owner`), which are not scoped to a school.

  No existing row is touched: the column is nullable, so all current accounts keep
  working as platform-level users.

Downgrade drops the column and then the table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2d5a8c1e4b7"
down_revision: str | Sequence[str] | None = "e1c4b7a9f2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def _school_table_exists() -> bool:
    found = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'school' AND table_schema = current_schema()"
            )
        )
        .first()
    )
    return found is not None


def _column_exists() -> bool:
    found = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'user' AND column_name = 'school_id'"
            )
        )
        .first()
    )
    return found is not None


def upgrade() -> None:
    if not _school_table_exists():
        op.create_table(
            "school",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", _AUTO_STR(), nullable=False),
            sa.Column("code", _AUTO_STR(), nullable=False),
            sa.Column("email", _AUTO_STR(), nullable=False),
            sa.Column("phone", _AUTO_STR(), nullable=True),
            sa.Column("address", _AUTO_STR(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        # `unique=True, index=True` on the model means one unique index per column,
        # which is what `--autogenerate` compares against.
        op.create_index("ix_school_name", "school", ["name"], unique=True)
        op.create_index("ix_school_code", "school", ["code"], unique=True)
        op.create_index("ix_school_email", "school", ["email"], unique=True)

    if not _column_exists():
        op.add_column("user", sa.Column("school_id", sa.Integer(), nullable=True))
        op.create_index("ix_user_school_id", "user", ["school_id"])
        op.create_foreign_key(
            "user_school_id_fkey", "user", "school", ["school_id"], ["id"]
        )


def downgrade() -> None:
    if _column_exists():
        op.drop_constraint("user_school_id_fkey", "user", type_="foreignkey")
        op.drop_index("ix_user_school_id", table_name="user")
        op.drop_column("user", "school_id")
    if _school_table_exists():
        op.drop_index("ix_school_email", table_name="school")
        op.drop_index("ix_school_code", table_name="school")
        op.drop_index("ix_school_name", table_name="school")
        op.drop_table("school")
