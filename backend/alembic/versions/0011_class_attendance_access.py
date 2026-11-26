"""Class attendance access: who takes a class's attendance when its class teacher is away.

Revision ID: 0011
Revises: 0010

One row per class-section per day names the teacher who may open that section and save its
daily attendance, plus whether the office has signed it off. It is a per-day grant of that
single right - not a role, not an assignment - so it vanishes with the day and never widens
what the person can do in any other class.

Adds a table only; changes nothing that exists. Safe to run twice.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "classattendanceaccess" in _tables():
        return
    op.create_table(
        "classattendanceaccess",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("class_teacher_id", sa.Uuid(), nullable=False),
        sa.Column("delegate_employee_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
        sa.ForeignKeyConstraint(["class_teacher_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["delegate_employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id",
            "classroom_id",
            "on_date",
            name="uq_classattendanceaccess_classroom_date",
        ),
    )
    op.create_index("ix_classattendanceaccess_school_id", "classattendanceaccess", ["school_id"])
    op.create_index(
        "ix_classattendanceaccess_classroom_id", "classattendanceaccess", ["classroom_id"]
    )
    op.create_index(
        "ix_classattendanceaccess_class_teacher_id", "classattendanceaccess", ["class_teacher_id"]
    )
    op.create_index(
        "ix_classattendanceaccess_delegate_employee_id",
        "classattendanceaccess",
        ["delegate_employee_id"],
    )


def downgrade() -> None:
    if "classattendanceaccess" in _tables():
        op.drop_table("classattendanceaccess")
