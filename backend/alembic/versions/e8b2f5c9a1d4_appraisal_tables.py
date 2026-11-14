"""Appraisal season: cycles, one appraisal per person per cycle, goals, training.

Revision ID: e8b2f5c9a1d4
Revises: c4e9b1d7f3a2
Create Date: 2026-11-14

Why
---
Phase 7 answered "who covers the class?". Phase 8 answers the question the year ends
with: **what did we say about each other, and can we prove it?** Four tables:

    appraisalcycle     the window ("2025-26 Annual", April-March) and its state;
    appraisal          one person inside one window, UNIQUE(school, cycle, employee);
    appraisalgoal      a measurable line inside that appraisal, judged or unjudged;
    trainingrecord     what somebody attended - the evidence a goal was worked on.

The rating is 1..5 twice (the person's, then the reviewer's) and `finalized_at` is the
lock: once the office signs it off, no write is accepted on that row, including the
reviewer's. That is a rule the schema cannot express, so it lives in
`appraisal/service.py` - but the unique key (`one appraisal per person per season`) is
in the schema, because PostgreSQL can enforce it and a screen cannot.

`teacherreview` is deliberately untouched: anonymous parent feedback and a signed
appraisal are different claims about the same teacher.

`_has_table` guards keep this re-runnable, for the reason Phase 6 and 7 record: a
database built by `create_missing()` is stamped at head and gets these tables from
`create_all` (see the operational notes in `backend/phase.md`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b2f5c9a1d4"
down_revision: str | Sequence[str] | None = "c4e9b1d7f3a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _create_cycles() -> None:
    if _has_table("appraisalcycle"):
        return
    op.create_table(
        "appraisalcycle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column("name", _text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        # Draft / Open / Closed - the vocabulary lives in `teachers/labels.py`.
        sa.Column("status", _text(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column(
            "created_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("school_id", "name", name="uq_appraisalcycle_school_name"),
    )


def _create_appraisals() -> None:
    if _has_table("appraisal"):
        return
    op.create_table(
        "appraisal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "cycle_id",
            sa.Uuid(),
            sa.ForeignKey("appraisalcycle.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", _text(), nullable=False),
        sa.Column("self_rating", sa.Integer(), nullable=True),
        sa.Column("self_note", _text(), nullable=True),
        sa.Column("reviewer_rating", sa.Integer(), nullable=True),
        sa.Column("reviewer_note", _text(), nullable=True),
        sa.Column(
            "reviewer_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        # The lock: set once, never cleared.
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        # One appraisal per person per season - a screen cannot enforce this, and a
        # second row would make "the rating" ambiguous.
        sa.UniqueConstraint(
            "school_id",
            "cycle_id",
            "employee_id",
            name="uq_appraisal_cycle_employee",
        ),
    )
    op.create_index("ix_appraisal_cycle_status", "appraisal", ["cycle_id", "status"])


def _create_goals() -> None:
    if _has_table("appraisalgoal"):
        return
    op.create_table(
        "appraisalgoal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "appraisal_id",
            sa.Uuid(),
            sa.ForeignKey("appraisal.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", _text(), nullable=False),
        # What "done" looks like, in the school's words.
        sa.Column("target", _text(), nullable=True),
        # NULL = nobody has judged it yet. Not the same as False.
        sa.Column("achieved", sa.Boolean(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def _create_training() -> None:
    if _has_table("trainingrecord"):
        return
    op.create_table(
        "trainingrecord",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", _text(), nullable=False),
        sa.Column("provider", _text(), nullable=True),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
    )
    op.create_index(
        "ix_trainingrecord_employee_date",
        "trainingrecord",
        ["employee_id", "on_date"],
    )


def upgrade() -> None:
    _create_cycles()
    _create_appraisals()
    _create_goals()
    _create_training()


def downgrade() -> None:
    for name in ("trainingrecord", "appraisalgoal", "appraisal", "appraisalcycle"):
        if _has_table(name):
            op.drop_table(name)

