"""Bring a database that ran the abandoned id-based class refactor back in line.

Revision ID: f9e0f1a2b3cb
Revises: f9e0f1a2b3c7
Create Date: 2026-11-03

Why:
  An experiment replaced the admission form's class/section *text* columns with
  foreign keys (`applied_class_id` / `current_class_id` -> `classname`,
  `applied_section_id` -> `section`), moved the wording of a class into a new
  platform-wide `classname` table and left `classroom` holding nothing but
  `class_id`. That experiment was abandoned - the application code stores the
  wording again (`applied_for_class_level`, `current_class_or_last_class`,
  `applied_section_preference`, `separation_dropped_class`) and reads a class from
  `classroom.name`.

  A database that ran those three revisions therefore disagrees with the code it
  now serves: every read of `student_admission_form` fails with

      psycopg2.errors.UndefinedColumn:
      column student_admission_form.applied_for_class_level does not exist

  which is what this revision repairs. The wording is carried back out of the ids
  (`classname.name`, `section.name`) before the id columns are dropped, so no row
  loses the class or section it was filed for.

  Every step is guarded, so on a database built from the migrations that are in
  the repository today - where none of these columns or the `classname` table
  exist - this revision does nothing at all.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3cb"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (text column, the id column it was replaced by) on the admission form.
ADMISSION_TEXT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("applied_for_class_level", "applied_class_id"),
    ("current_class_or_last_class", "current_class_id"),
)


def _bind():
    return op.get_bind()


def _has_table(table: str) -> bool:
    found = _bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table"
        ),
        {"table": table},
    )
    return found.first() is not None


def _has_column(table: str, column: str) -> bool:
    found = _bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return found.first() is not None


def _restore_admission_text_columns() -> None:
    """Put the class/section wording back on the admission form, then drop the ids.

    `applied_for_class_level` and `current_class_or_last_class` hold the *name* of
    a class ("Class 6") in the code's schema; the experiment pointed them at
    `classname`, and `applied_section_id` / `separation_section_id` at `section`.
    The names are read back out of those rows first, so no application loses the
    class-section it was filed for.
    """
    if not _has_table("student_admission_form"):
        return
    if not _has_column("student_admission_form", "applied_class_id"):
        # Already the text schema - this database never ran the experiment.
        return

    for column in (
        "applied_for_class_level",
        "current_class_or_last_class",
        "applied_section_preference",
        "separation_dropped_class",
    ):
        if not _has_column("student_admission_form", column):
            op.execute(f"ALTER TABLE student_admission_form ADD COLUMN {column} varchar")

    bind = _bind()
    for text_column, id_column in ADMISSION_TEXT_COLUMNS:
        if _has_column("student_admission_form", id_column):
            bind.execute(
                sa.text(
                    f"UPDATE student_admission_form a SET {text_column} = m.name "
                    f"FROM classname m WHERE m.id = a.{id_column}"
                )
            )

    if _has_column("student_admission_form", "applied_section_id"):
        bind.execute(
            sa.text(
                "UPDATE student_admission_form a SET applied_section_preference = s.name "
                "FROM section s WHERE s.id = a.applied_section_id"
            )
        )

    if _has_column("student_admission_form", "separation_section_id"):
        bind.execute(
            sa.text(
                "UPDATE student_admission_form a SET separation_dropped_class = m.name "
                "FROM section s "
                "JOIN classroom c ON c.id = s.classroom_id "
                "JOIN classname m ON m.id = c.class_id "
                "WHERE s.id = a.separation_section_id"
            )
        )

    # The ids go away - and with them their foreign keys and indexes. Naming the
    # class-section is the text column's job again.
    for column in (
        "applied_class_id",
        "current_class_id",
        "applied_section_id",
        "separation_section_id",
    ):
        if _has_column("student_admission_form", column):
            op.execute(f"ALTER TABLE student_admission_form DROP COLUMN {column}")


def _restore_classroom_text_columns() -> None:
    """Give `classroom` its own `name` / `level` / `stage` back.

    The experiment moved the wording to `classname` and left the school's row
    holding only a `class_id`, but the code reads `classroom.name` (the class a
    section belongs to, the label on a class card). The wording is copied back out
    of the catalog row it points at before `class_id` is dropped.
    """
    if not _has_table("classroom") or not _has_column("classroom", "class_id"):
        return

    for column, column_type in (
        ("name", "varchar"),
        ("level", "integer"),
        ("stage", "varchar"),
    ):
        if not _has_column("classroom", column):
            op.execute(f"ALTER TABLE classroom ADD COLUMN {column} {column_type}")

    _bind().execute(
        sa.text(
            "UPDATE classroom c SET name = m.name, level = m.level, stage = m.stage "
            "FROM classname m WHERE m.id = c.class_id"
        )
    )
    # A row the catalog does not know still needs a value: NOT NULL is what the
    # code's model expects.
    op.execute("UPDATE classroom SET name = coalesce(name, '') WHERE name IS NULL")
    op.execute("UPDATE classroom SET level = coalesce(level, 0) WHERE level IS NULL")
    op.execute(
        "UPDATE classroom SET stage = coalesce(stage, 'primary') WHERE stage IS NULL"
    )

    op.execute("ALTER TABLE classroom ALTER COLUMN name SET NOT NULL")
    op.execute("ALTER TABLE classroom ALTER COLUMN level SET NOT NULL")
    op.execute("ALTER TABLE classroom ALTER COLUMN stage SET NOT NULL")

    # One row per (school, name) again - the rule the code and the seeder rely on -
    # and `class_id` itself goes away.
    op.execute(
        "ALTER TABLE classroom DROP CONSTRAINT IF EXISTS uq_classroom_school_class"
    )
    op.execute("DROP INDEX IF EXISTS uq_classroom_school_class")
    op.execute("DROP INDEX IF EXISTS ix_classroom_class_id")
    op.execute("ALTER TABLE classroom DROP COLUMN class_id")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_classroom_school_name "
        "ON classroom (school_id, name)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_classroom_name ON classroom (name)")


def upgrade() -> None:
    """Undo the abandoned id-based class refactor, keeping every row's class."""
    _restore_admission_text_columns()
    _restore_classroom_text_columns()

    # The platform-wide class list only existed to hold that refactor's ids.
    if _has_table("classname"):
        op.execute("DROP TABLE classname")

    print("[class] the admission form and classroom carry the class wording again")


def downgrade() -> None:
    """Intentionally empty.

    This revision only *removes* the columns and the table the abandoned refactor
    added. Re-creating them would re-introduce a design the code does not serve, so
    there is nothing to undo; `alembic downgrade` to an earlier revision still
    works.
    """
