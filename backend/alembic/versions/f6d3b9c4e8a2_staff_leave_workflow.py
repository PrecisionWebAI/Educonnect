"""Leave workflow: the school's policy, one person's override, and the decision.

Revision ID: f6d3b9c4e8a2
Revises: e5c2a8f1b9d3
Create Date: 2026-11-12

Why
---
Phases 5 made the register read `On Leave` from `leaverequest`, which meant the
product finally depended on that table being **true** - while `leaverequest` itself
had no way to be maintained: the leave screens could only list rows somebody else
had seeded, `status` was whatever a row happened to say, and `balance` was a column
of dashes because no table held an entitlement.

    leavepolicy     how many days of one type the school grants in a year.
    leavebalance    one person's **override** for one type and one year - not a
                    running total. Days used are summed from the approved requests
                    every time a balance is read, so a rejected or cancelled leave
                    gives its days back without an update, and no counter can drift
                    away from the requests it is supposed to describe.

Three columns are added to `leaverequest` so a decision can explain itself:

    decided_by_user_id   who approved / rejected / cancelled it;
    decided_at           when - the screen prints it beside the badge;
    decision_note        the office's own words with that decision.

`ADD COLUMN` is why this revision guards every column with `_has_column`: a database
built by `create_missing()` is stamped at head without replaying revisions and gets
these columns from `create_all`, so the ALTERs here must be a no-op there (see the
operational note in `backend/phase.md`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6d3b9c4e8a2"
down_revision: str | Sequence[str] | None = "e5c2a8f1b9d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(name: str) -> set[str]:
    if not _has_table(name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(name)}


def _create_policy() -> None:
    if _has_table("leavepolicy"):
        return
    op.create_table(
        "leavepolicy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        # The leave type's own spelling ("Casual"): the screen prints it.
        sa.Column("leave_type", _text(), nullable=False),
        sa.Column("annual_days", sa.Integer(), nullable=False),
        sa.Column(
            "updated_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "school_id", "leave_type", name="uq_leavepolicy_school_type"
        ),
    )


def _create_balance() -> None:
    if _has_table("leavebalance"):
        return
    op.create_table(
        "leavebalance",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("leave_type", _text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        # The entitlement this person has **instead of** the policy's number.
        sa.Column("entitled_days", sa.Integer(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column(
            "updated_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "school_id",
            "employee_id",
            "leave_type",
            "year",
            name="uq_leavebalance_employee_type_year",
        ),
    )


def _add_decision_columns() -> None:
    """Add the three decision columns to `leaverequest`, idempotently."""
    existing = _columns("leaverequest")
    if not existing:  # pragma: no cover - the table is ancient
        return
    if "decided_by_user_id" not in existing:
        op.add_column(
            "leaverequest",
            sa.Column(
                "decided_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
            ),
        )
    if "decided_at" not in existing:
        op.add_column(
            "leaverequest", sa.Column("decided_at", sa.DateTime(), nullable=True)
        )
    if "decision_note" not in existing:
        op.add_column(
            "leaverequest", sa.Column("decision_note", _text(), nullable=True)
        )


def upgrade() -> None:
    _create_policy()
    _create_balance()
    _add_decision_columns()


def downgrade() -> None:
    existing = _columns("leaverequest")
    for column in ("decision_note", "decided_at", "decided_by_user_id"):
        if column in existing:
            op.drop_column("leaverequest", column)
    for name in ("leavebalance", "leavepolicy"):
        if _has_table(name):
            op.drop_table(name)
