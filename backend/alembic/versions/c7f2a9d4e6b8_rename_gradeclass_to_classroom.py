"""Rename gradeclass -> classroom (the product's word is "class")

The schema and the UI now use one vocabulary: `classroom` (Nursery ... Class 12)
with `classroom_id` foreign keys, matching `info/db_mapping.txt`.

A pure rename - no rows move - so it can be reviewed and rolled back on its own.
Constraint, index and column names are renamed too: if the database kept the old
names, `alembic revision --autogenerate` would keep reporting drift against the
renamed models.

Revision ID: c7f2a9d4e6b8
Revises: b4e7f1a2c9d3
Create Date: 2026-04-10
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f2a9d4e6b8"
down_revision = "b4e7f1a2c9d3"
branch_labels = None
depends_on = None

#: every table holding a FK column that points at the class table
CHILD_TABLES = (
    "section",
    "feestructure",
    "homeworkassignment",
    "studentprofile",
    "timetableperiod",
    "attendancerecord",
    "classteacherassignment",
    "teacherassignment",
    "paperdraft",
    "examsource",
)


def upgrade() -> None:
    """gradeclass/grade_class_id -> classroom/classroom_id everywhere."""
    op.rename_table("gradeclass", "classroom")
    op.execute("ALTER INDEX ix_gradeclass_name RENAME TO ix_classroom_name")
    op.execute(
        "ALTER TABLE classroom RENAME CONSTRAINT gradeclass_pkey TO classroom_pkey"
    )
    # The id sequence keeps its old name otherwise ("gradeclass_id_seq" next to
    # a table called "classroom"), and the two FK indexes below are named after
    # the column they index - Postgres does not follow a column rename.
    op.execute("ALTER SEQUENCE gradeclass_id_seq RENAME TO classroom_id_seq")
    op.execute(
        "ALTER INDEX ix_examsource_grade_class_id RENAME TO ix_examsource_classroom_id"
    )
    op.execute(
        "ALTER INDEX ix_paperdraft_grade_class_id RENAME TO ix_paperdraft_classroom_id"
    )

    for table in CHILD_TABLES:
        op.alter_column(table, "grade_class_id", new_column_name="classroom_id")
        op.execute(
            f"ALTER TABLE {table} RENAME CONSTRAINT "
            f"{table}_grade_class_id_fkey TO {table}_classroom_id_fkey"
        )

    op.execute(
        "ALTER TABLE section RENAME CONSTRAINT "
        "uq_section_grade_name TO uq_section_classroom_name"
    )


def downgrade() -> None:
    """Back to the grade wording, names included."""
    op.execute(
        "ALTER TABLE section RENAME CONSTRAINT "
        "uq_section_classroom_name TO uq_section_grade_name"
    )

    for table in reversed(CHILD_TABLES):
        op.execute(
            f"ALTER TABLE {table} RENAME CONSTRAINT "
            f"{table}_classroom_id_fkey TO {table}_grade_class_id_fkey"
        )
        op.alter_column(table, "classroom_id", new_column_name="grade_class_id")

    op.execute(
        "ALTER INDEX ix_paperdraft_classroom_id RENAME TO ix_paperdraft_grade_class_id"
    )
    op.execute(
        "ALTER INDEX ix_examsource_classroom_id RENAME TO ix_examsource_grade_class_id"
    )
    op.execute("ALTER SEQUENCE classroom_id_seq RENAME TO gradeclass_id_seq")
    op.execute(
        "ALTER TABLE classroom RENAME CONSTRAINT classroom_pkey TO gradeclass_pkey"
    )
    op.execute("ALTER INDEX ix_classroom_name RENAME TO ix_gradeclass_name")
    op.rename_table("classroom", "gradeclass")
