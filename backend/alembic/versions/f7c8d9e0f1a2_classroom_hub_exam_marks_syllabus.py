"""Classroom hub: diary link, exams, marks and syllabus progress.

Revision ID: f7c8d9e0f1a2
Revises: f6b7c8d9e0f1
Create Date: 2026-11-02

Why:
  The classroom becomes the table everything hangs off, so the four things that
  were missing are added here:

  * `classdiary.classroom_id` / `section_id` - a diary entry could only be found
    through its student; the class it was written for is now stored (back-filled
    from the student's placement).
  * `exam` - a named exam ("Mid-Term") to hang marks on.
  * `marks` - the school had **no** marks/results table at all. Classroom and
    section are deliberately not copied: they come from the student's placement.
  * `syllabusprogress` - the "course complete %" a class card shows had no
    source of truth; it now lives per (section, subject).

  Every table carries its own auto-increment `id` and its `school_id` (the
  tenant column), like the rest of the schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "f6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Add the diary link, then the exam / marks / syllabus-progress tables."""
    inspector = sa.inspect(op.get_bind())

    # --- 1. classdiary: reachable from the classroom ------------------------
    diary_columns = {c["name"] for c in inspector.get_columns("classdiary")}
    if "classroom_id" not in diary_columns:
        op.add_column(
            "classdiary", sa.Column("classroom_id", sa.Integer(), nullable=True)
        )
        op.add_column("classdiary", sa.Column("section_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "classdiary_classroom_id_fkey",
            "classdiary",
            "classroom",
            ["classroom_id"],
            ["id"],
        )
        op.create_foreign_key(
            "classdiary_section_id_fkey",
            "classdiary",
            "section",
            ["section_id"],
            ["id"],
        )
        op.create_index("ix_classdiary_classroom_id", "classdiary", ["classroom_id"])
        op.create_index("ix_classdiary_section_id", "classdiary", ["section_id"])
        # Existing entries get the class of the student they were written for.
        op.execute(
            """
            UPDATE classdiary d
            SET classroom_id = s.classroom_id,
                section_id = s.section_id
            FROM studentprofile s
            WHERE s.id = d.student_id
            """
        )

    # --- 2. exam ------------------------------------------------------------
    if "exam" not in inspector.get_table_names():
        op.create_table(
            "exam",
            sa.Column("name", _AUTO_STR(), nullable=False),
            sa.Column("term", _AUTO_STR(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("status", _AUTO_STR(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_exam_school_id", "exam", ["school_id"])

    # --- 3. marks -----------------------------------------------------------
    if "marks" not in inspector.get_table_names():
        op.create_table(
            "marks",
            sa.Column("exam_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("marks_obtained", sa.Float(), nullable=False),
            sa.Column("max_marks", sa.Float(), nullable=False),
            sa.Column("grade", _AUTO_STR(), nullable=True),
            sa.Column("entered_by", sa.Integer(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["exam_id"], ["exam.id"]),
            sa.ForeignKeyConstraint(["student_id"], ["studentprofile.id"]),
            sa.ForeignKeyConstraint(["subject_id"], ["subject.id"]),
            sa.ForeignKeyConstraint(["entered_by"], ["user.id"]),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "exam_id",
                "student_id",
                "subject_id",
                name="uq_marks_exam_student_subject",
            ),
        )
        op.create_index("ix_marks_exam_id", "marks", ["exam_id"])
        op.create_index("ix_marks_student_id", "marks", ["student_id"])
        op.create_index("ix_marks_school_id", "marks", ["school_id"])

    # --- 4. syllabusprogress ------------------------------------------------
    if "syllabusprogress" not in inspector.get_table_names():
        op.create_table(
            "syllabusprogress",
            sa.Column("section_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("chapters_total", sa.Integer(), nullable=False),
            sa.Column("chapters_done", sa.Integer(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["section_id"], ["section.id"]),
            sa.ForeignKeyConstraint(["subject_id"], ["subject.id"]),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "section_id",
                "subject_id",
                name="uq_syllabusprogress_section_subject",
            ),
        )
        op.create_index(
            "ix_syllabusprogress_school_id", "syllabusprogress", ["school_id"]
        )


def downgrade() -> None:
    """Drop the three tables and the diary's classroom link."""
    inspector = sa.inspect(op.get_bind())

    if "syllabusprogress" in inspector.get_table_names():
        op.drop_index("ix_syllabusprogress_school_id", table_name="syllabusprogress")
        op.drop_table("syllabusprogress")

    if "marks" in inspector.get_table_names():
        op.drop_index("ix_marks_school_id", table_name="marks")
        op.drop_index("ix_marks_student_id", table_name="marks")
        op.drop_index("ix_marks_exam_id", table_name="marks")
        op.drop_table("marks")

    if "exam" in inspector.get_table_names():
        op.drop_index("ix_exam_school_id", table_name="exam")
        op.drop_table("exam")

    diary_columns = {c["name"] for c in inspector.get_columns("classdiary")}
    if "classroom_id" in diary_columns:
        op.drop_index("ix_classdiary_section_id", table_name="classdiary")
        op.drop_index("ix_classdiary_classroom_id", table_name="classdiary")
        op.drop_constraint("classdiary_section_id_fkey", "classdiary", type_="foreignkey")
        op.drop_constraint(
            "classdiary_classroom_id_fkey", "classdiary", type_="foreignkey"
        )
        op.drop_column("classdiary", "section_id")
        op.drop_column("classdiary", "classroom_id")
