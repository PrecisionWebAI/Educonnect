"""Add teachersubject (many subjects per teacher), drop employee.subject_id.

Revision ID: f5a6b7c8d9e0
Revises: f4e5f6a7b8c9
Create Date: 2026-11-02

Why:
  A teacher usually teaches more than one subject, but the employee row could
  only name one (`employee.subject_id`). The subject list belongs in its own
  table, so this migration:

  * creates `teachersubject` (`UNIQUE(teacher_id, subject_id)`),
  * copies every existing `employee.subject_id` into it, and
  * drops the single-value column.

  `teachersubject` is the teacher's *own* subject list. `teacherassignment`
  (class + section + subject) stays what it was: where they actually teach.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "f4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create teachersubject, back-fill it, then drop the single-subject column."""
    inspector = sa.inspect(op.get_bind())
    if "teachersubject" not in inspector.get_table_names():
        op.create_table(
            "teachersubject",
            sa.Column("teacher_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.ForeignKeyConstraint(["teacher_id"], ["employee.id"]),
            sa.ForeignKeyConstraint(["subject_id"], ["subject.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "teacher_id", "subject_id", name="uq_teachersubject_teacher_subject"
            ),
        )
        op.create_index("ix_teachersubject_school_id", "teachersubject", ["school_id"])
        op.create_index(
            "ix_teachersubject_subject_id", "teachersubject", ["subject_id"]
        )

    columns = {column["name"] for column in inspector.get_columns("employee")}
    if "subject_id" in columns:
        op.execute(
            """
            INSERT INTO teachersubject (teacher_id, subject_id, school_id)
            SELECT e.id, e.subject_id, e.school_id
            FROM employee e
            WHERE e.subject_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM teachersubject t
                  WHERE t.teacher_id = e.id AND t.subject_id = e.subject_id
              )
            """
        )
        op.drop_column("employee", "subject_id")


def downgrade() -> None:
    """Restore the single-subject column (the lowest subject id) and drop the table."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employee")}
    if "subject_id" not in columns:
        op.add_column("employee", sa.Column("subject_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "employee_subject_id_fkey",
            "employee",
            "subject",
            ["subject_id"],
            ["id"],
        )
        op.execute(
            """
            UPDATE employee e
            SET subject_id = (
                SELECT MIN(t.subject_id) FROM teachersubject t
                WHERE t.teacher_id = e.id
            )
            """
        )

    if "teachersubject" in inspector.get_table_names():
        op.drop_index("ix_teachersubject_subject_id", table_name="teachersubject")
        op.drop_index("ix_teachersubject_school_id", table_name="teachersubject")
        op.drop_table("teachersubject")
