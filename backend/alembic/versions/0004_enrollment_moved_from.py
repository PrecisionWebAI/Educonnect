"""Remember where a student sat before they were moved one class down.

Revision ID: 0004
Revises: 0003

`enrollment.moved_from_classroom_id` lets Undo put the child back in the same
class-section. Nullable, no backfill: existing rows were never moved.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    have = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("enrollment")}
    if "moved_from_classroom_id" in have:
        return
    op.add_column(
        "enrollment", sa.Column("moved_from_classroom_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_enrollment_moved_from_classroom_id"),
        "enrollment",
        ["moved_from_classroom_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_enrollment_moved_from_classroom_id",
        "enrollment",
        "classroom",
        ["moved_from_classroom_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_enrollment_moved_from_classroom_id", "enrollment", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_enrollment_moved_from_classroom_id"), table_name="enrollment"
    )
    op.drop_column("enrollment", "moved_from_classroom_id")
