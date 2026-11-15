"""The Course plan: `chapter` + `chapter_progress`, teacher history, and the mirror gone.

Why
---
`subjectteacher` held **one** teacher per (class-section, subject): a change overwrote
history, so "who taught this before" and "how much of it did they finish" were both
unanswerable. `syllabusprogress` held two counters (`chapters_done`, `chapters_total`)
that had to be kept in step with the plan by hand - and by the time Phase 5 started the
table was empty, so nothing was ever kept in step.

What changes
------------
* `chapter` - the plan: one row per chapter per (class, subject, session), with a
  `sequence` and an optional `planned_date`;
* `chapter_progress` - how far one class-section has got: `status`, `completed_on`,
  `completed_by_employee_id`, unique per (chapter, classroom);
* `subjectteacher` gains `academic_year_id`, `effective_from` (NOT NULL, defaulting to
  today) and `effective_to`; the old `UNIQUE(classroom_id, subject_id)` becomes
  `UNIQUE(classroom_id, subject_id, effective_from)` so a teacher change is a **new
  row**, not an overwrite;
* **`syllabusprogress` is dropped** (owner decision, 15 Nov 2026). The row count is
  checked first and the migration **aborts printing the count** if it is not zero.

Downgrade
---------
Recreates `syllabusprogress` **empty** with its original shape (the columns the dropped
table had, plus its unique key) and reverses the rest. The chapters and the progress rows
are kept: a downgrade returns the schema to "no plan table", not to "no plan".

Revision ID: d3f1a8c5e2b7
Revises: c8e2f5a1d7b3
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f1a8c5e2b7"
down_revision: str | Sequence[str] | None = "c8e2f5a1d7b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_TEACHER_KEY = "uq_subjectteacher_classroom_subject"
NEW_TEACHER_KEY = "uq_subjectteacher_classroom_subject_from"


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _constraints(table: str) -> set[str]:
    names = {
        item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints(table)
    }
    return {name for name in names if name}


def _refuse_non_empty(_table: str = "syllabusprogress") -> None:
    """Stop - printing the count - if the table we are about to drop holds rows."""
    if not _has_table(_table):
        return
    rows = int(
        op.get_bind().execute(sa.text(f'SELECT count(*) FROM "{_table}"')).scalar_one()
    )
    print(f"[{_table}] {rows} row(s)")
    if rows:
        raise RuntimeError(
            f"[{_table}] refusing to drop it: {rows} row(s) are still in the table. "
            "Nothing was changed - move them into chapter/chapter_progress first."
        )


def _create_chapter() -> None:
    op.create_table(
        "chapter",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column(
            "class_id", sa.Uuid(), sa.ForeignKey("classname.class_id"), nullable=False
        ),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subject.id"), nullable=False),
        sa.Column(
            "academic_year_id",
            sa.Uuid(),
            sa.ForeignKey("academic_year.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.UniqueConstraint(
            "school_id",
            "class_id",
            "subject_id",
            "academic_year_id",
            "sequence",
            name="uq_chapter_school_class_subject_year_sequence",
        ),
    )
    op.create_index("ix_chapter_school_id", "chapter", ["school_id"])
    op.create_index("ix_chapter_class_id", "chapter", ["class_id"])
    op.create_index("ix_chapter_subject_id", "chapter", ["subject_id"])
    op.create_index("ix_chapter_academic_year_id", "chapter", ["academic_year_id"])


def _create_chapter_progress() -> None:
    op.create_table(
        "chapterprogress",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), sa.ForeignKey("chapter.id"), nullable=False),
        sa.Column(
            "classroom_id", sa.Uuid(), sa.ForeignKey("classroom.id"), nullable=False
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column(
            "completed_by_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "chapter_id", "classroom_id", name="uq_chapterprogress_chapter_classroom"
        ),
    )
    op.create_index("ix_chapterprogress_school_id", "chapterprogress", ["school_id"])
    op.create_index("ix_chapterprogress_chapter_id", "chapterprogress", ["chapter_id"])
    op.create_index(
        "ix_chapterprogress_classroom_id", "chapterprogress", ["classroom_id"]
    )
    op.create_index(
        "ix_chapterprogress_completed_by_employee_id",
        "chapterprogress",
        ["completed_by_employee_id"],
    )


def _teacher_history_columns() -> None:
    """`subjectteacher` becomes a timeline instead of a pointer."""
    if not _has_table("subjectteacher"):
        return
    columns = _columns("subjectteacher")
    if "academic_year_id" not in columns:
        op.add_column(
            "subjectteacher", sa.Column("academic_year_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_subjectteacher_academic_year_id",
            "subjectteacher",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_subjectteacher_academic_year_id", "subjectteacher", ["academic_year_id"]
        )
    if "effective_from" not in columns:
        # NOT NULL because it is part of the new key; the default fills any row that
        # already exists (0 today) and keeps `SubjectTeacher(...)` callers working.
        op.add_column(
            "subjectteacher",
            sa.Column(
                "effective_from",
                sa.Date(),
                nullable=False,
                server_default=sa.text("CURRENT_DATE"),
            ),
        )
    if "effective_to" not in columns:
        op.add_column(
            "subjectteacher", sa.Column("effective_to", sa.Date(), nullable=True)
        )

    constraints = _constraints("subjectteacher")
    if OLD_TEACHER_KEY in constraints:
        op.drop_constraint(OLD_TEACHER_KEY, "subjectteacher", type_="unique")
    if NEW_TEACHER_KEY not in _constraints("subjectteacher"):
        op.create_unique_constraint(
            NEW_TEACHER_KEY,
            "subjectteacher",
            ["classroom_id", "subject_id", "effective_from"],
        )


def upgrade() -> None:
    if not _has_table("chapter"):
        _create_chapter()
    if not _has_table("chapterprogress"):
        _create_chapter_progress()

    _teacher_history_columns()

    # The owner's decision: the mirror goes, after refusing to destroy data.
    _refuse_non_empty()
    if _has_table("syllabusprogress"):
        op.drop_table("syllabusprogress")
        print("[syllabusprogress] dropped - chapter_progress is the only source now.")


def downgrade() -> None:
    if not _has_table("syllabusprogress"):
        op.create_table(
            "syllabusprogress",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=True
            ),
            sa.Column(
                "classroom_id", sa.Uuid(), sa.ForeignKey("classroom.id"), nullable=False
            ),
            sa.Column(
                "subject_id", sa.Uuid(), sa.ForeignKey("subject.id"), nullable=False
            ),
            sa.Column(
                "teacher_id", sa.Uuid(), sa.ForeignKey("employee.id"), nullable=True
            ),
            sa.Column(
                "academic_year_id",
                sa.Uuid(),
                sa.ForeignKey("academic_year.id"),
                nullable=True,
            ),
            sa.Column("planned_completion", sa.Date(), nullable=True),
            sa.Column(
                "chapters_total", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "chapters_done", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "classroom_id",
                "subject_id",
                name="uq_syllabusprogress_classroom_subject",
            ),
        )
        op.create_index(
            "ix_syllabusprogress_school_id", "syllabusprogress", ["school_id"]
        )
        op.create_index(
            "ix_syllabusprogress_teacher_id", "syllabusprogress", ["teacher_id"]
        )
        op.create_index(
            "ix_syllabusprogress_academic_year_id",
            "syllabusprogress",
            ["academic_year_id"],
        )
        print("[syllabusprogress] recreated empty.")

    if _has_table("subjectteacher"):
        constraints = _constraints("subjectteacher")
        if NEW_TEACHER_KEY in constraints:
            op.drop_constraint(NEW_TEACHER_KEY, "subjectteacher", type_="unique")
        if OLD_TEACHER_KEY not in _constraints("subjectteacher"):
            op.create_unique_constraint(
                OLD_TEACHER_KEY, "subjectteacher", ["classroom_id", "subject_id"]
            )
        columns = _columns("subjectteacher")
        for name in ("effective_to", "effective_from", "academic_year_id"):
            if name in columns:
                op.drop_column("subjectteacher", name)

    for table in ("chapterprogress", "chapter"):
        if _has_table(table):
            op.drop_table(table)
