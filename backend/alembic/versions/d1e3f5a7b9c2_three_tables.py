"""Restructure hiring into three tables: pipeline, employee, salary.

Revision ID: d1e3f5a7b9c2
Revises: c5d7e9f1a2b3
Create Date: 2026-10-31

Why:
  The module settles into three tables, matching what the screen actually does:

  * `pipeline_hiring_table` (was `hiringcandidate`) - interview pipeline.
  * `employee` (was `staffprofile`) - the single employee record the form fills,
    holding the employee id (EMP-####). Teaching staff live here too, so the
    separate `teacherprofile` table (which duplicated department/qualification/
    joining_date) is removed and the teaching FKs now point at `employee`.
  * `salarypayment` - the salary register (unchanged).

  Every table is empty at this point, so the migration is purely structural.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e3f5a7b9c2"
down_revision: str | Sequence[str] | None = "c5d7e9f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tables whose `teacher_id` pointed at `teacherprofile` and now point at `employee`.
_TEACHER_FK_TABLES = (
    "classdiary",
    "classteacherassignment",
    "homeworkassignment",
    "teacherassignment",
    "teacherreview",
    "timetableperiod",
)


def upgrade() -> None:
    """Rename the pipeline + employee tables and merge `teacherprofile` in."""
    # 1. pipeline
    op.rename_table("hiringcandidate", "pipeline_hiring_table")

    # 2. stop `staffprofile` pointing at `teacherprofile`, so both can move.
    op.drop_constraint(
        "staffprofile_teacher_profile_id_fkey", "staffprofile", type_="foreignkey"
    )
    op.drop_column("staffprofile", "teacher_profile_id")

    # 3. the employee table (this was `staffprofile`).
    op.rename_table("staffprofile", "employee")

    # 4. teaching FKs now point at `employee` (a teacher is an employee).
    for table in _TEACHER_FK_TABLES:
        op.drop_constraint(f"{table}_teacher_id_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            f"{table}_teacher_id_fkey", table, "employee", ["teacher_id"], ["id"]
        )

    # 5. `teacherprofile` is gone - its columns live on `employee`.
    op.drop_table("teacherprofile")


def downgrade() -> None:
    """Recreate `teacherprofile`, split the employee table back out."""
    import sqlalchemy as sa
    import sqlmodel

    _AUTO_STR = sqlmodel.sql.sqltypes.AutoString

    # 1. bring `teacherprofile` back.
    op.create_table(
        "teacherprofile",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("qualification", _AUTO_STR(), nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. teaching FKs point back at `teacherprofile`.
    for table in _TEACHER_FK_TABLES:
        op.drop_constraint(f"{table}_teacher_id_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            f"{table}_teacher_id_fkey", table, "teacherprofile", ["teacher_id"], ["id"]
        )

    # 3. employee back to `staffprofile`, with the teacher link restored.
    op.rename_table("employee", "staffprofile")
    op.add_column(
        "staffprofile", sa.Column("teacher_profile_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "staffprofile_teacher_profile_id_fkey",
        "staffprofile",
        "teacherprofile",
        ["teacher_profile_id"],
        ["id"],
    )

    # 4. pipeline back to `hiringcandidate`.
    op.rename_table("pipeline_hiring_table", "hiringcandidate")