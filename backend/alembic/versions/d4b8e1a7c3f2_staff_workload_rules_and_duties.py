"""Staff workload: what a full week is, and what else fills it.

Revision ID: d4b8e1a7c3f2
Revises: c7a4f9b2e6d1
Create Date: 2026-11-12

Why
---
Phase 3 closed the staff file (documents, KYC masking, the audit trail). Phase 4
answers the question the workload matrix could not:

    staffworkloadrule  one row per school. The number the utilisation figure is a
                       percentage *of*, plus the two thresholds the badge uses.
                       Without it the matrix divided by however many slots the
                       timetable happened to contain, so "80% utilised" changed
                       meaning the day somebody added a period to Class 6.
    staffduty          the work that is neither a period nor leave - exam
                       invigilation, a gate, assembly, the library desk, a bus
                       route. A weekly day **or** a single date, and a standing
                       duty may have neither.

Neither table adds a column to an existing table, which is why this revision is
safe on a database that was built by `create_missing()`: a boot stamps the schema
at head without replaying revisions, so a revision that only *creates* tables has
nothing left to do there - `create_all` already made them from the models.
(Revisions that `ADD COLUMN` are the ones that need care; see the operational note
in `backend/phase.md`.)
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8e1a7c3f2"
down_revision: str | Sequence[str] | None = "c7a4f9b2e6d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _id() -> sa.Column:
    """The row's uuid - `UUIDMixin`, declared first in the models for a reason."""
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _school() -> sa.Column:
    """The tenant column: `TenantMixin` (nullable, indexed, FK to `school`)."""
    return sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True)


def _employee() -> sa.Column:
    return sa.Column(
        "employee_id",
        sa.Uuid(),
        sa.ForeignKey("employee.id"),
        nullable=False,
        index=True,
    )


def _user(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("user.id"), nullable=True)


def _created_at() -> sa.Column:
    """`utcnow()` is the model's Python default, so the column needs no server one."""
    return sa.Column("created_at", sa.DateTime(), nullable=False)


def _create_rule() -> None:
    if _has_table("staffworkloadrule"):
        return
    op.create_table(
        "staffworkloadrule",
        _id(),
        _school(),
        # NULL is "the office has not stated a capacity", not zero: the matrix
        # falls back to the timetable's own slots and says so.
        sa.Column("weekly_periods", sa.Integer(), nullable=True),
        sa.Column("overload_percent", sa.Integer(), nullable=False),
        sa.Column("underload_percent", sa.Integer(), nullable=False),
        _user("updated_by_user_id"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("school_id", name="uq_staffworkloadrule_school"),
    )


def _create_duty() -> None:
    if _has_table("staffduty"):
        return
    op.create_table(
        "staffduty",
        _id(),
        _school(),
        _employee(),
        sa.Column("duty_type", _text(), nullable=False),
        sa.Column("title", _text(), nullable=True),
        # Weekly **or** dated; the schema refuses both at once, and neither means
        # a standing duty with no fixed slot.
        sa.Column("day_of_week", _text(), nullable=True),
        sa.Column("on_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("note", _text(), nullable=True),
        _user("created_by_user_id"),
        _created_at(),
    )


def upgrade() -> None:
    _create_rule()
    _create_duty()


def downgrade() -> None:
    for name in ("staffduty", "staffworkloadrule"):
        if _has_table(name):
            op.drop_table(name)
