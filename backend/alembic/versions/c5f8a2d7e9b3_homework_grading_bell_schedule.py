"""Homework: when a submission arrived, whether it was late, and what it earned.

Why
---
`homeworksubmission` could say *pending / submitted / graded* and nothing else. So the
board's "Submitted" column had nothing to print (the service wrote an empty string), a
child who handed work in two days late looked exactly like one who was on time, and a
teacher had nowhere to put a score or a remark. The service also already upserted on
`(homework_id, student_id)` - one row per child per assignment - but no key said so, so
two requests could create two rows and the child would appear twice.

`classlog` had the same kind of gap: a log line said what the class did, never **which
subject** it was done in, so the diary could not be read by subject.

The timetable's day shape (six periods with two breaks) lived only in the frontend, as a
hardcoded array in `TimetablePanel.tsx`. `bell_schedule` gives each school its own day:
periods and breaks, in order, seeded once on first read.

What changes
------------
* `homeworksubmission` gains `submitted_at`, `is_late`, `graded_at`,
  `marks_awarded numeric(6,2)` and `UNIQUE (homework_id, student_id)`;
* `classlog` gains `subject_id` (nullable - a day-level line may cover no single
  subject; the existing period keys stay exactly as they are);
* `bell_schedule` - one row per slot of the school day: `period_no`, `start_time`,
  `end_time`, `is_break`, `UNIQUE (school_id, period_no)`;
* `timetableperiod` gains `UNIQUE (school_id, classroom_id, day_of_week, start_time)`,
  **in addition to** the teacher slot that is already there. A teacher in two rooms is a
  clash; so is one room holding two periods at the same hour.

Guards
------
Both new keys are added only after counting the rows that would break them. A count
above zero **aborts and prints it** - that means something already wrote the shape this
migration is trying to make impossible, and stopping is better than deleting a school's
data.

Downgrade
---------
Drops the two keys, the four submission columns, `classlog.subject_id` and
`bell_schedule`. Submissions, log lines and periods are **kept**: a downgrade returns the
schema to "no grade, no timestamps", not to "no homework".

Revision ID: c5f8a2d7e9b3
Revises: e4b7c2d9a1f6
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5f8a2d7e9b3"
down_revision: str | Sequence[str] | None = "e4b7c2d9a1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The unique key that makes one child one row per assignment.
SUBMISSION_KEY = "uq_homeworksubmission_homework_student"

#: The unique key that makes one room hold one period per slot.
CLASS_SLOT_KEY = "uq_timetableperiod_class_slot"

#: Rows that would break `SUBMISSION_KEY` - one child with two rows on one assignment.
DUPLICATE_SUBMISSIONS = (
    "SELECT count(*) FROM ("
    "  SELECT homework_id, student_id FROM homeworksubmission"
    "  GROUP BY homework_id, student_id HAVING count(*) > 1"
    ") AS duplicates"
)

#: Rows that would break `CLASS_SLOT_KEY` - one room with two periods in one slot.
DUPLICATE_CLASS_SLOTS = (
    "SELECT count(*) FROM ("
    "  SELECT school_id, classroom_id, day_of_week, start_time FROM timetableperiod"
    "  GROUP BY school_id, classroom_id, day_of_week, start_time HAVING count(*) > 1"
    ") AS duplicates"
)


def _count(sql: str) -> int:
    return int(op.get_bind().execute(sa.text(sql)).scalar() or 0)


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. A submission that knows when it arrived, and what it earned
    # ------------------------------------------------------------------
    op.add_column(
        "homeworksubmission", sa.Column("submitted_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "homeworksubmission",
        sa.Column(
            "is_late", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "homeworksubmission", sa.Column("graded_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "homeworksubmission",
        sa.Column("marks_awarded", sa.Numeric(6, 2), nullable=True),
    )

    duplicates = _count(DUPLICATE_SUBMISSIONS)
    if duplicates:
        raise RuntimeError(
            "homeworksubmission already holds "
            f"{duplicates} duplicated (homework_id, student_id) pair(s); "
            f"{SUBMISSION_KEY} cannot be created. Nothing was changed."
        )
    op.create_unique_constraint(
        SUBMISSION_KEY,
        "homeworksubmission",
        ["homework_id", "student_id"],
    )
    print(
        "homeworksubmission rows after: "
        f"{_count('SELECT count(*) FROM homeworksubmission')}"
    )

    # ------------------------------------------------------------------
    # 2. A log line names its subject
    # ------------------------------------------------------------------
    op.add_column("classlog", sa.Column("subject_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_classlog_subject_id",
        "classlog",
        "subject",
        ["subject_id"],
        ["id"],
    )

    # ------------------------------------------------------------------
    # 3. The school's own day shape
    # ------------------------------------------------------------------
    if not _has_table("bellschedule"):
        op.create_table(
            "bellschedule",
            sa.Column("period_no", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column(
                "is_break",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.ForeignKeyConstraint(
                ["school_id"], ["school.id"], name="bellschedule_school_id_fkey"
            ),
            sa.PrimaryKeyConstraint("id", name="bellschedule_pkey"),
            sa.UniqueConstraint(
                "school_id", "period_no", name="uq_bellschedule_school_period"
            ),
        )
        op.create_index("ix_bellschedule_school_id", "bellschedule", ["school_id"])

    # ------------------------------------------------------------------
    # 4. One room, one period per slot
    # ------------------------------------------------------------------
    duplicates = _count(DUPLICATE_CLASS_SLOTS)
    if duplicates:
        raise RuntimeError(
            "timetableperiod already holds "
            f"{duplicates} clashing (class-section, day, start) slot(s); "
            f"{CLASS_SLOT_KEY} cannot be created. Nothing was changed."
        )
    op.create_unique_constraint(
        CLASS_SLOT_KEY,
        "timetableperiod",
        ["school_id", "classroom_id", "day_of_week", "start_time"],
    )
    print(
        f"timetableperiod rows after: {_count('SELECT count(*) FROM timetableperiod')}"
    )


def downgrade() -> None:
    """Undo in reverse order - keys first, then columns, then the table."""
    op.drop_constraint(CLASS_SLOT_KEY, "timetableperiod", type_="unique")

    if _has_table("bellschedule"):
        op.drop_index("ix_bellschedule_school_id", table_name="bellschedule")
        op.drop_table("bellschedule")

    op.drop_constraint("fk_classlog_subject_id", "classlog", type_="foreignkey")
    op.drop_column("classlog", "subject_id")

    op.drop_constraint(SUBMISSION_KEY, "homeworksubmission", type_="unique")
    for column in ("marks_awarded", "graded_at", "is_late", "submitted_at"):
        op.drop_column("homeworksubmission", column)

    print(
        "after downgrade: "
        f"homeworksubmission={_count('SELECT count(*) FROM homeworksubmission')} rows, "
        f"timetableperiod={_count('SELECT count(*) FROM timetableperiod')} rows (kept)"
    )
