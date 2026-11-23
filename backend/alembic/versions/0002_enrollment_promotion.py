"""Enrollment promotion status and next-year outcome.

Revision ID: 0002
Revises: 0001

`promotion_status` says how a record came to be (NEW_ADMISSION / PROMOTED / RETAINED /
COMPLETED) and is separate from `status` (active / left ...). `next_year_outcome` is
written on the **older** record ("Promoted to Class 4"); empty means Pending. The link
back to the original class is the existing `previous_enrollment_id`.

Existing rows: PROMOTED when they already point at a previous enrollment, otherwise
NEW_ADMISSION. Nothing is deleted.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("enrollment")}


def upgrade() -> None:
    have = _columns()
    if "promotion_status" not in have:
        op.add_column(
            "enrollment",
            sa.Column(
                "promotion_status",
                sa.String(),
                nullable=False,
                server_default="NEW_ADMISSION",
            ),
        )
        op.execute(
            "UPDATE enrollment SET promotion_status = 'PROMOTED' "
            "WHERE previous_enrollment_id IS NOT NULL"
        )
        op.create_check_constraint(
            "ck_enrollment_promotion_status",
            "enrollment",
            "promotion_status IN ('NEW_ADMISSION', 'PROMOTED', 'RETAINED', 'COMPLETED')",
        )
    if "next_year_outcome" not in have:
        op.add_column(
            "enrollment", sa.Column("next_year_outcome", sa.String(), nullable=True)
        )


def downgrade() -> None:
    op.drop_constraint("ck_enrollment_promotion_status", "enrollment", type_="check")
    op.drop_column("enrollment", "next_year_outcome")
    op.drop_column("enrollment", "promotion_status")
