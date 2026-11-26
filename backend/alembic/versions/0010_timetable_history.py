"""Timetable history: who held each slot, and for which dates.

Revision ID: 0010
Revises: 0009

`timetableperiod` only ever holds today's week - an edit overwrites a slot and a clear
deletes it - so it cannot say who taught a class last month. `timetableperiodhistory` is
an append-only ledger kept by model events (`timetable/history.py`): every change of
teacher, room, subject or weekday closes the open stretch (`valid_to`) and opens a new one
(`valid_from`). The Teachers > Course tab reads it to count a teacher's classes for the
whole session, one day at a time.

Existing periods get one open stretch each, starting on the first day of their school's
current academic year (today when the school has none): nothing earlier was ever recorded,
so the current week is the best honest account of the session so far.

The table has no foreign keys on purpose - the period, room or teacher may be deleted later
and the record of a past week has to survive that. Adds a table only; changes nothing that
exists. Safe to run twice.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "timetableperiodhistory"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if TABLE in _tables():
        return
    op.create_table(
        "timetableperiodhistory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_subject_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.String(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(f"ix_{TABLE}_school_id", TABLE, ["school_id"])
    op.create_index(f"ix_{TABLE}_period_id", TABLE, ["period_id"])
    op.create_index(f"ix_{TABLE}_teacher_id", TABLE, ["teacher_id"])

    op.execute(
        f"""
        INSERT INTO {TABLE}
            (id, school_id, period_id, classroom_id, classroom_subject_id, teacher_id,
             day_of_week, start_time, end_time, valid_from, valid_to)
        SELECT gen_random_uuid(), tp.school_id, tp.id, tp.classroom_id,
               tp.classroom_subject_id, tp.teacher_id,
               CAST(tp.day_of_week AS TEXT), tp.start_time, tp.end_time,
               COALESCE(
                   (SELECT ay.start_date
                      FROM academic_year AS ay
                     WHERE ay.school_id = tp.school_id AND ay.is_current
                     LIMIT 1),
                   CURRENT_DATE
               ),
               NULL
          FROM timetableperiod AS tp
        """
    )


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
