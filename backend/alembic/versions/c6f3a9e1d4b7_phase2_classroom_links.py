"""Phase 2 (3/3): the two classroom links and the register's new columns.

* `classlog.timetableperiod_id` - a log entry written against a period. The table
  has always held one row per class-section per day; the workload tab's "periods
  completed this week" needs the period when the school logs per period.
* `syllabusprogress` gets `teacher_id`, `academic_year_id` and
  `planned_completion` - who owns the syllabus, which session the plan is for, and
  the date it was supposed to finish. All nullable: rows written before this
  revision have no plan, and the tab reports "no plan" instead of 0%.
* `staffattendancerecord` gets `check_in_time`, `check_out_time` and
  `leave_request_id`, plus a check on the status vocabulary. `on_leave` is *not*
  in that vocabulary on purpose: an approved leave is derived from `leaverequest`,
  so a stored copy could survive a cancellation and mark somebody on-leave for ever
  (see `people/teachers/staff_attendance/models.py`).

The status check is created only when no existing row would violate it - a legacy
value keeps the constraint off rather than failing the deployment.

Revision ID: c6f3a9e1d4b7
Revises: b5e2f8d0c3a6
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6f3a9e1d4b7"
down_revision: str | Sequence[str] | None = "b5e2f8d0c3a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _check_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table)
        if constraint["name"]
    }


def upgrade() -> None:
    # --- classlog.timetableperiod_id ---------------------------------------
    if "timetableperiod_id" not in _columns("classlog"):
        op.add_column(
            "classlog", sa.Column("timetableperiod_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_classlog_timetableperiod_id",
            "classlog",
            "timetableperiod",
            ["timetableperiod_id"],
            ["id"],
        )
        op.create_index(
            "ix_classlog_timetableperiod_id", "classlog", ["timetableperiod_id"]
        )

    # --- syllabusprogress: owner, session, plan ----------------------------
    columns = _columns("syllabusprogress")
    if "teacher_id" not in columns:
        op.add_column(
            "syllabusprogress", sa.Column("teacher_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_syllabusprogress_teacher_id",
            "syllabusprogress",
            "employee",
            ["teacher_id"],
            ["id"],
        )
        op.create_index(
            "ix_syllabusprogress_teacher_id", "syllabusprogress", ["teacher_id"]
        )
    if "academic_year_id" not in columns:
        op.add_column(
            "syllabusprogress", sa.Column("academic_year_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_syllabusprogress_academic_year_id",
            "syllabusprogress",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_syllabusprogress_academic_year_id",
            "syllabusprogress",
            ["academic_year_id"],
        )
    if "planned_completion" not in columns:
        op.add_column(
            "syllabusprogress", sa.Column("planned_completion", sa.Date(), nullable=True)
        )


    # --- staffattendancerecord: times, leave link, status vocabulary -------
    columns = _columns("staffattendancerecord")
    if "check_in_time" not in columns:
        op.add_column(
            "staffattendancerecord", sa.Column("check_in_time", sa.Time(), nullable=True)
        )
    if "check_out_time" not in columns:
        op.add_column(
            "staffattendancerecord",
            sa.Column("check_out_time", sa.Time(), nullable=True),
        )
    if "leave_request_id" not in columns:
        op.add_column(
            "staffattendancerecord",
            sa.Column("leave_request_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_staffattendancerecord_leave_request_id",
            "staffattendancerecord",
            "leaverequest",
            ["leave_request_id"],
            ["id"],
        )
        op.create_index(
            "ix_staffattendancerecord_leave_request_id",
            "staffattendancerecord",
            ["leave_request_id"],
        )

    invalid = (
        op.get_bind()
        .exec_driver_sql(
            "SELECT count(*) FROM staffattendancerecord"
            " WHERE status NOT IN ('present', 'absent', 'half_day')"
        )
        .scalar_one()
    )
    if invalid == 0 and "ck_staffattendancerecord_status" not in _check_names(
        "staffattendancerecord"
    ):
        op.create_check_constraint(
            "ck_staffattendancerecord_status",
            "staffattendancerecord",
            "status IN ('present', 'absent', 'half_day')",
        )
    else:  # pragma: no cover - only on a database with an older vocabulary
        print(
            f"[phase2] {invalid} staffattendancerecord row(s) hold an unknown "
            "status; ck_staffattendancerecord_status was not created"
        )


def downgrade() -> None:
    columns = _columns("staffattendancerecord")
    if "ck_staffattendancerecord_status" in _check_names("staffattendancerecord"):
        op.drop_constraint(
            "ck_staffattendancerecord_status",
            "staffattendancerecord",
            type_="check",
        )
    if "leave_request_id" in columns:
        op.drop_index(
            "ix_staffattendancerecord_leave_request_id",
            table_name="staffattendancerecord",
        )
        op.drop_constraint(
            "fk_staffattendancerecord_leave_request_id",
            "staffattendancerecord",
            type_="foreignkey",
        )
        op.drop_column("staffattendancerecord", "leave_request_id")
    if "check_out_time" in columns:
        op.drop_column("staffattendancerecord", "check_out_time")
    if "check_in_time" in columns:
        op.drop_column("staffattendancerecord", "check_in_time")

    columns = _columns("syllabusprogress")
    if "planned_completion" in columns:
        op.drop_column("syllabusprogress", "planned_completion")
    if "academic_year_id" in columns:
        op.drop_index(
            "ix_syllabusprogress_academic_year_id", table_name="syllabusprogress"
        )
        op.drop_constraint(
            "fk_syllabusprogress_academic_year_id",
            "syllabusprogress",
            type_="foreignkey",
        )
        op.drop_column("syllabusprogress", "academic_year_id")
    if "teacher_id" in columns:
        op.drop_index("ix_syllabusprogress_teacher_id", table_name="syllabusprogress")
        op.drop_constraint(
            "fk_syllabusprogress_teacher_id", "syllabusprogress", type_="foreignkey"
        )
        op.drop_column("syllabusprogress", "teacher_id")

    if "timetableperiod_id" in _columns("classlog"):
        op.drop_index("ix_classlog_timetableperiod_id", table_name="classlog")
        op.drop_constraint(
            "fk_classlog_timetableperiod_id", "classlog", type_="foreignkey"
        )
        op.drop_column("classlog", "timetableperiod_id")
