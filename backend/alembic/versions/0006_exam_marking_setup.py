"""Exam module: family note, taken-by, pass/grading per paper, date-sheet publish.

Revision ID: 0006
Revises: 0005

What it adds (every column is nullable, so older exams, papers and marks read as before):

* `exam.family_note`                      - what guardians and students read (not a reschedule)
* `exam.datesheet_published_at/_by_user_id` - the class teacher's date-sheet publish
* `exam_paper.taken_by_employee_id`       - the teacher who takes the test
* `exam_paper.pass_mode / pass_percent`   - this paper's own pass line
* `exam_paper.grading_scale`              - this paper's own copy of the grading ladder
* `exam_paper.syllabus_text`              - the syllabus, in the teacher's own words
* `marks.enrollment_id`                   - the student's placement that session (backfilled)

Safe to run twice: each step checks what is already there. The backfill only fills rows
that are still empty, so a re-run changes nothing.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _add(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    # --- exam -----------------------------------------------------------------
    _add("exam", sa.Column("family_note", sa.String(), nullable=True))
    _add("exam", sa.Column("datesheet_published_at", sa.DateTime(), nullable=True))
    if "datesheet_published_by_user_id" not in _columns("exam"):
        op.add_column(
            "exam",
            sa.Column(
                "datesheet_published_by_user_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "app_user.id", name="fk_exam_datesheet_published_by_user_id"
                ),
                nullable=True,
            ),
        )

    # --- exam_paper -----------------------------------------------------------
    if "taken_by_employee_id" not in _columns("exam_paper"):
        op.add_column(
            "exam_paper",
            sa.Column(
                "taken_by_employee_id",
                sa.Uuid(),
                sa.ForeignKey("employee.id", name="fk_exam_paper_taken_by_employee_id"),
                nullable=True,
            ),
        )
    _add("exam_paper", sa.Column("pass_mode", sa.String(), nullable=True))
    _add(
        "exam_paper",
        sa.Column("pass_percent", sa.Numeric(5, 2), nullable=True),
    )
    _add("exam_paper", sa.Column("grading_scale", sa.JSON(), nullable=True))
    _add("exam_paper", sa.Column("syllabus_text", sa.String(), nullable=True))

    if "ix_exam_paper_taken_by_employee_id" not in _indexes("exam_paper"):
        op.create_index(
            "ix_exam_paper_taken_by_employee_id",
            "exam_paper",
            ["taken_by_employee_id"],
        )
    # The duplicate-test warning looks up "same section subject, same date".
    if "ix_exam_paper_subject_date" not in _indexes("exam_paper"):
        op.create_index(
            "ix_exam_paper_subject_date",
            "exam_paper",
            ["classroom_subject_id", "exam_date"],
        )

    # --- marks ----------------------------------------------------------------
    if "enrollment_id" not in _columns("marks"):
        op.add_column(
            "marks",
            sa.Column(
                "enrollment_id",
                sa.Uuid(),
                sa.ForeignKey("enrollment.id", name="fk_marks_enrollment_id"),
                nullable=True,
            ),
        )
    if "ix_marks_enrollment_id" not in _indexes("marks"):
        op.create_index("ix_marks_enrollment_id", "marks", ["enrollment_id"])

    # A mark belongs to the enrollment its student had in the exam's session year.
    # `(student, year)` is unique in `enrollment`, so there is at most one match; a mark
    # whose exam has no year, or whose student had no enrollment then, stays empty.
    op.execute(
        """
        UPDATE marks AS m
           SET enrollment_id = (
               SELECT en.id
                 FROM enrollment AS en
                 JOIN exam_paper AS ep ON ep.id = m.exam_paper_id
                 JOIN exam AS ex ON ex.id = ep.exam_id
                WHERE en.student_id = m.student_id
                  AND en.academic_year_id = ex.academic_year_id
                  AND en.school_id = m.school_id
                LIMIT 1
           )
         WHERE m.enrollment_id IS NULL
        """
    )


def downgrade() -> None:
    # Drops the new columns **and whatever they hold** (family notes, taken-by, per-paper
    # pass/grading, syllabus text, date-sheet publication, mark enrollment links).
    if "ix_marks_enrollment_id" in _indexes("marks"):
        op.drop_index("ix_marks_enrollment_id", table_name="marks")
    if "enrollment_id" in _columns("marks"):
        op.drop_constraint("fk_marks_enrollment_id", "marks", type_="foreignkey")
        op.drop_column("marks", "enrollment_id")

    for index in ("ix_exam_paper_subject_date", "ix_exam_paper_taken_by_employee_id"):
        if index in _indexes("exam_paper"):
            op.drop_index(index, table_name="exam_paper")
    if "taken_by_employee_id" in _columns("exam_paper"):
        op.drop_constraint(
            "fk_exam_paper_taken_by_employee_id", "exam_paper", type_="foreignkey"
        )
        op.drop_column("exam_paper", "taken_by_employee_id")
    for column in ("syllabus_text", "grading_scale", "pass_percent", "pass_mode"):
        if column in _columns("exam_paper"):
            op.drop_column("exam_paper", column)

    if "datesheet_published_by_user_id" in _columns("exam"):
        op.drop_constraint(
            "fk_exam_datesheet_published_by_user_id", "exam", type_="foreignkey"
        )
        op.drop_column("exam", "datesheet_published_by_user_id")
    for column in ("datesheet_published_at", "family_note"):
        if column in _columns("exam"):
            op.drop_column("exam", column)
