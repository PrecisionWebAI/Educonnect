"""Substitution: the absence, and who stood in for it.

Revision ID: c4e9b1d7f3a2
Revises: a1c7e4f9d2b6
Create Date: 2026-11-14

Why
---
Phase 6 made an approved leave true. Phase 7 answers the question the timetable asks
the moment it is: *somebody is away - who covers their periods?* Two tables:

    substitutionrequest      one person, one day, and why their periods need cover
                             (`UNIQUE(school_id, employee_id, on_date)`);
    substitutionassignment   one period on one date, covered by that person, and how
                             far it is signed (`UNIQUE(school_id, period_id,
                             on_date)`).

The second key is the rule the feature turns on - one adult per room at a given
hour - and every part of it is NOT NULL, so PostgreSQL enforces it. A withdrawn
cover is deleted rather than marked cancelled, which is what frees the slot for the
replacement; the `staffauditlog` row is the history.

No timetable, leave or teacher-subject data is copied: the board derives the affected
periods from `timetableperiod` for that weekday, the absences from `leaverequest`,
and the candidates from `teachersubject`. So a period moved at 08:00 moves the cover
list with it, and a leave cancelled at 08:05 removes the ask.

`_has_table` guards keep this re-runnable: a database built by `create_missing()` is
stamped at head without replaying revisions and gets both tables from `create_all`
(see the operational notes in `backend/phase.md`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e9b1d7f3a2"
down_revision: str | Sequence[str] | None = "a1c7e4f9d2b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _create_requests() -> None:
    if _has_table("substitutionrequest"):
        return
    op.create_table(
        "substitutionrequest",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "employee_id", sa.Uuid(), sa.ForeignKey("employee.id"), index=True
        ),
        sa.Column("on_date", sa.Date(), nullable=False),
        # The leave type, or "Training" / "Official duty" - prose, so it keeps case.
        sa.Column("reason", _text(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        # NULL for an absence that is not a leave: not every absence is an entitlement.
        sa.Column(
            "leave_request_id",
            sa.Uuid(),
            sa.ForeignKey("leaverequest.id"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "school_id",
            "employee_id",
            "on_date",
            name="uq_substitutionrequest_employee_date",
        ),
    )
    op.create_index(
        "ix_substitutionrequest_employee_date",
        "substitutionrequest",
        ["employee_id", "on_date"],
    )


def _create_assignments() -> None:
    if _has_table("substitutionassignment"):
        return
    op.create_table(
        "substitutionassignment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "request_id",
            sa.Uuid(),
            sa.ForeignKey("substitutionrequest.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "period_id",
            sa.Uuid(),
            sa.ForeignKey("timetableperiod.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column(
            "absent_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "substitute_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", _text(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column(
            "assigned_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column(
            "decided_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        # One adult per room per hour - the constraint the whole feature turns on.
        sa.UniqueConstraint(
            "school_id",
            "period_id",
            "on_date",
            name="uq_substitutionassignment_period_date",
        ),
    )
    op.create_index(
        "ix_substitutionassignment_period_date",
        "substitutionassignment",
        ["period_id", "on_date"],
    )
    op.create_index(
        "ix_substitutionassignment_substitute_date",
        "substitutionassignment",
        ["substitute_employee_id", "on_date"],
    )


def upgrade() -> None:
    _create_requests()
    _create_assignments()


def downgrade() -> None:
    for name in ("substitutionassignment", "substitutionrequest"):
        if _has_table(name):
            op.drop_table(name)
