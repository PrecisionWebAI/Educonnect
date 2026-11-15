"""The attendance register gets its keys, its leave link, and `school_setting`.

Why
---
`attendancerecord` had **no** uniqueness: pressing Save twice wrote two rows for the
same child, the same day and the same subject, and every total after that counted the
day twice. The service now reads-then-writes, which is right for one user; these keys
are what make it right for two.

What changes
------------
* **Guard:** a group-by duplicate scan on both keys, aborting with the count when any
  group holds more than one row (0 today). A non-empty result means something still
  writes the old way - the migration stops instead of inventing a winner.
* `attendancerecord.leave_request_id` (nullable FK `leaverequest.id`) + index.
* `UNIQUE(school_id, student_id, date, subject_id)`.
* a **partial** unique index `(school_id, student_id, date) WHERE subject_id IS NULL`,
  because PostgreSQL treats two NULLs as different values - without it the day-level
  row could still be written twice.
* `school_setting` - the school's own policy numbers (`attendance.absence_threshold`,
  `attendance.consecutive_days`, the exam keys), `UNIQUE(school_id, key)`.
* `attendanceauditlog.school_id` backfilled from its parent register row, then NOT NULL.

Downgrade
---------
Reverses each step and **keeps the data**: the rows this migration did not create
(marks, audit history) are untouched, so a downgrade returns the schema to "no keys, no
link", not to "no register".

Revision ID: b7c1d4e9a3f2
Revises: e9d5c3f7a2b4
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d4e9a3f2"
down_revision: str | Sequence[str] | None = "e9d5c3f7a2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REGISTER_KEY = "uq_attendancerecord_school_student_date_subject"
DAY_KEY = "uq_attendancerecord_school_student_date_day"
LEAVE_COLUMN = "leave_request_id"
LEAVE_INDEX = "ix_attendancerecord_leave_request_id"
LEAVE_FK = "fk_attendancerecord_leave_request_id"


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _constraints(table: str) -> set[str]:
    names = {
        item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints(table)
    }
    return {name for name in names if name}


def _indexes(table: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table)
        if item.get("name")
    }


def _foreign_key(table: str, column: str) -> str | None:
    for item in sa.inspect(op.get_bind()).get_foreign_keys(table):
        if column in (item.get("constrained_columns") or []):
            return item.get("name")
    return None


def _null_count(table: str) -> int:
    return int(
        op.get_bind()
        .execute(sa.text(f'SELECT count(*) FROM "{table}" WHERE school_id IS NULL'))
        .scalar_one()
    )


def _refuse_duplicates() -> None:
    """Stop - printing the count - if the table already holds duplicates."""
    if not _has_table("attendancerecord"):
        return
    bind = op.get_bind()
    by_subject = int(
        bind.execute(
            sa.text(
                """
                SELECT count(*) FROM (
                    SELECT school_id, student_id, date, subject_id
                    FROM attendancerecord
                    GROUP BY school_id, student_id, date, subject_id
                    HAVING count(*) > 1
                ) AS dupes
                """
            )
        ).scalar_one()
    )
    day_level = int(
        bind.execute(
            sa.text(
                """
                SELECT count(*) FROM (
                    SELECT school_id, student_id, date
                    FROM attendancerecord
                    WHERE subject_id IS NULL
                    GROUP BY school_id, student_id, date
                    HAVING count(*) > 1
                ) AS dupes
                """
            )
        ).scalar_one()
    )
    if by_subject or day_level:
        raise RuntimeError(
            f"[attendancerecord] refusing to add the register keys: {by_subject} "
            f"student/day/subject group(s) and {day_level} day-level group(s) hold more "
            "than one row. Nothing was changed - merge them, then run this again."
        )
    print("[attendancerecord] 0 duplicate groups on both keys - safe to add them.")


def upgrade() -> None:
    _refuse_duplicates()

    if _has_table("attendancerecord"):
        if LEAVE_COLUMN not in _columns("attendancerecord"):
            op.add_column(
                "attendancerecord",
                sa.Column(LEAVE_COLUMN, sa.Uuid(), nullable=True),
            )
            op.create_foreign_key(
                LEAVE_FK,
                "attendancerecord",
                "leaverequest",
                [LEAVE_COLUMN],
                ["id"],
            )
        if LEAVE_INDEX not in _indexes("attendancerecord"):
            op.create_index(LEAVE_INDEX, "attendancerecord", [LEAVE_COLUMN])

        if REGISTER_KEY not in _constraints("attendancerecord"):
            op.create_unique_constraint(
                REGISTER_KEY,
                "attendancerecord",
                ["school_id", "student_id", "date", "subject_id"],
            )
        if DAY_KEY not in _indexes("attendancerecord"):
            op.create_index(
                DAY_KEY,
                "attendancerecord",
                ["school_id", "student_id", "date"],
                unique=True,
                postgresql_where=sa.text("subject_id IS NULL"),
                sqlite_where=sa.text("subject_id IS NULL"),
            )

    if not _has_table("school_setting"):
        op.create_table(
            "school_setting",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False
            ),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("value", sa.String(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "school_id", "key", name="uq_school_setting_school_key"
            ),
        )
        op.create_index("ix_school_setting_school_id", "school_setting", ["school_id"])
        op.create_index("ix_school_setting_key", "school_setting", ["key"])

    if _has_table("attendanceauditlog") and _has_table("attendancerecord"):
        op.execute(
            'UPDATE "attendanceauditlog" t SET school_id = p.school_id '
            'FROM "attendancerecord" p '
            "WHERE t.attendance_record_id = p.id AND t.school_id IS NULL"
        )
        if _null_count("attendanceauditlog") == 0:
            op.alter_column(
                "attendanceauditlog",
                "school_id",
                existing_type=sa.Uuid(),
                nullable=False,
            )


def downgrade() -> None:
    if _has_table("attendanceauditlog"):
        op.alter_column(
            "attendanceauditlog", "school_id", existing_type=sa.Uuid(), nullable=True
        )

    if _has_table("school_setting"):
        op.drop_table("school_setting")

    if _has_table("attendancerecord"):
        if DAY_KEY in _indexes("attendancerecord"):
            op.drop_index(DAY_KEY, table_name="attendancerecord")
        if REGISTER_KEY in _constraints("attendancerecord"):
            op.drop_constraint(REGISTER_KEY, "attendancerecord", type_="unique")

        if LEAVE_COLUMN in _columns("attendancerecord"):
            name = _foreign_key("attendancerecord", LEAVE_COLUMN)
            if name is not None:
                op.drop_constraint(name, "attendancerecord", type_="foreignkey")
            if LEAVE_INDEX in _indexes("attendancerecord"):
                op.drop_index(LEAVE_INDEX, table_name="attendancerecord")
            op.drop_column("attendancerecord", LEAVE_COLUMN)
