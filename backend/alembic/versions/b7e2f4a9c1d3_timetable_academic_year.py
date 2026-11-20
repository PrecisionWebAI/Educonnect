"""Timetable periods belong to an academic year.

Revision ID: b7e2f4a9c1d3
Revises: f4b1c2d3e4f5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2f4a9c1d3"
down_revision: str | Sequence[str] | None = "f4b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEACHER_SLOT = "uq_timetableperiod_teacher_slot"
CLASS_SLOT = "uq_timetableperiod_class_slot"


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _unique_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {
        row["name"]
        for row in inspector.get_unique_constraints(table)
        if row.get("name")
    }


def _index_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {
        row["name"]
        for row in inspector.get_indexes(table)
        if row.get("name")
    }


def upgrade() -> None:
    if "timetableperiod" not in sa.inspect(op.get_bind()).get_table_names():
        return

    if "academic_year_id" not in _columns("timetableperiod"):
        op.add_column(
            "timetableperiod",
            sa.Column("academic_year_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_timetableperiod_academic_year",
            "timetableperiod",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_timetableperiod_academic_year_id",
            "timetableperiod",
            ["academic_year_id"],
        )

    # Existing weeks were built before the year existed; they belong to the
    # school's current year, which is the only year they could have meant.
    if "academic_year" in sa.inspect(op.get_bind()).get_table_names():
        op.execute(
            """
            UPDATE timetableperiod AS t
               SET academic_year_id = a.id
              FROM academic_year AS a
             WHERE a.school_id = t.school_id
               AND a.is_current = true
               AND t.academic_year_id IS NULL
            """
        )

    names = _unique_names("timetableperiod")
    if TEACHER_SLOT in names:
        op.drop_constraint(TEACHER_SLOT, "timetableperiod", type_="unique")
    if CLASS_SLOT in names:
        op.drop_constraint(CLASS_SLOT, "timetableperiod", type_="unique")
    # On the live schema the old teacher key exists as an **index** with this
    # exact name, not as a pg_constraint. Dropping only constraints made the
    # replacement fail with `relation ... already exists`.
    indexes = _index_names("timetableperiod")
    if TEACHER_SLOT in indexes:
        op.drop_index(TEACHER_SLOT, table_name="timetableperiod")
    if CLASS_SLOT in indexes:
        op.drop_index(CLASS_SLOT, table_name="timetableperiod")
    op.create_unique_constraint(
        TEACHER_SLOT,
        "timetableperiod",
        ["school_id", "academic_year_id", "teacher_id", "day_of_week", "start_time"],
    )
    op.create_unique_constraint(
        CLASS_SLOT,
        "timetableperiod",
        ["school_id", "academic_year_id", "classroom_id", "day_of_week", "start_time"],
    )


def downgrade() -> None:
    if "timetableperiod" not in sa.inspect(op.get_bind()).get_table_names():
        return
    names = _unique_names("timetableperiod")
    if TEACHER_SLOT in names:
        op.drop_constraint(TEACHER_SLOT, "timetableperiod", type_="unique")
    if CLASS_SLOT in names:
        op.drop_constraint(CLASS_SLOT, "timetableperiod", type_="unique")
    op.create_unique_constraint(
        TEACHER_SLOT,
        "timetableperiod",
        ["school_id", "teacher_id", "day_of_week", "start_time"],
    )
    op.create_unique_constraint(
        CLASS_SLOT,
        "timetableperiod",
        ["school_id", "classroom_id", "day_of_week", "start_time"],
    )
    if "academic_year_id" in _columns("timetableperiod"):
        op.drop_index(
            "ix_timetableperiod_academic_year_id", table_name="timetableperiod"
        )
        op.drop_constraint(
            "fk_timetableperiod_academic_year", "timetableperiod", type_="foreignkey"
        )
        op.drop_column("timetableperiod", "academic_year_id")
