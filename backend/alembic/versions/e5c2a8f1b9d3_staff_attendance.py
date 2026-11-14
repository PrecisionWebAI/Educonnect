"""Staff attendance: the daily register.

Revision ID: e5c2a8f1b9d3
Revises: d4b8e1a7c3f2
Create Date: 2026-11-12

Why
---
Phases 2-4 closed the staff file: qualifications, documents and KYC, then how full
a week is. None of them answers the question the office asks every morning - *who
is here today* - because `employee` says who is on the roll and `leaverequest` says
who is away, and neither records presence.

    staffattendancerecord  one row per person per day: `present` / `absent` /
                           `half_day`, plus who marked it and when. `on_leave` is
                           **derived** from an approved `leaverequest` and is
                           deliberately not a value this column may hold, so a
                           cancelled leave cannot leave a stale row behind.

`UNIQUE(school_id, employee_id, date)` is enforced here rather than in the service
alone: unlike `staffduty`, every column in the key is NOT NULL, so PostgreSQL
actually applies it and two callers marking the same day at once cannot both win.

No column is added to an existing table, so this revision is safe on a database
built by `create_missing()`: a boot stamps the schema at head without replaying
revisions, and `create_all` has already made this table from the models.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5c2a8f1b9d3"
down_revision: str | Sequence[str] | None = "d4b8e1a7c3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _create_attendance() -> None:
    if _has_table("staffattendancerecord"):
        return
    op.create_table(
        "staffattendancerecord",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        # The day being marked. A register is dated, never "current".
        sa.Column("date", sa.Date(), nullable=False),
        # `labels.ATTENDANCE_STATUSES` - text, like `staffduty.duty_type`: a fixed
        # vocabulary, not a state machine.
        sa.Column("status", _text(), nullable=False),
        sa.Column("remarks", _text(), nullable=True),
        sa.Column("marked_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "school_id",
            "employee_id",
            "date",
            name="uq_staffattendancerecord_employee_date",
        ),
    )


def upgrade() -> None:
    _create_attendance()


def downgrade() -> None:
    if _has_table("staffattendancerecord"):
        op.drop_table("staffattendancerecord")
