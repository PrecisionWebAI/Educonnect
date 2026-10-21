"""Make `classroom` and `section` global catalogs (no longer per school).

Revision ID: c7d4b8e2f6a9
Revises: a4e8f1c2d5b9
Create Date: 2026-10-21

Why:
  `classroom` and `section` held the *same* Nursery..Class 12 / A-J rows in every
  school, so they grew with the number of schools. They are catalog data, exactly
  like `role` and `permission` - one set for the whole platform - while a school's
  boundary lives on the data rows (students, attendance, timetable) through their
  own `school_id`.

  This merges the duplicated rows into one global set and drops `school_id` from
  both tables, then restores the global unique index on `classroom.name`.

  `subject` is deliberately left per-school: its names and codes genuinely differ
  between schools.

Upgrade dedupes by name, so the pre-existing "15 classes per school" seed data
collapses cleanly into a single 15. Downgrade restores the nullable columns and
the per-school unique index (rows stay merged - the split cannot be recovered).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d4b8e2f6a9"
down_revision: str | Sequence[str] | None = "a4e8f1c2d5b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND table_schema = current_schema()"
        ),
        {"t": table},
    )
    return {row[0] for row in rows}


def _indexes(table: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text("SELECT indexname FROM pg_indexes WHERE tablename = :t"), {"t": table}
    )
    return {row[0] for row in rows}


def _dedupe_catalog_rows() -> None:
    """Collapse per-school copies of the same class/section into one row each.

    Only safe while `classroom`/`section` hold pure seed data - a student or an
    attendance row still pointing at a to-be-deleted id would make the DELETE fail
    loudly (FK) instead of corrupting anything.
    """
    conn = op.get_bind()

    # Repoint sections off the duplicate classrooms, then drop the duplicates.
    conn.execute(
        sa.text(
            """
            UPDATE section s
            SET classroom_id = keep.keep_id
            FROM classroom old
            JOIN (
                SELECT name, MIN(id) AS keep_id FROM classroom GROUP BY name
            ) keep ON keep.name = old.name
            WHERE s.classroom_id = old.id AND s.classroom_id <> keep.keep_id
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM classroom "
            "WHERE id NOT IN (SELECT MIN(id) FROM classroom GROUP BY name)"
        )
    )

    # The A-J sections are now duplicated per class as well; keep one each.
    conn.execute(
        sa.text(
            "DELETE FROM section "
            "WHERE id NOT IN (SELECT MIN(id) FROM section GROUP BY classroom_id, name)"
        )
    )


def upgrade() -> None:
    _dedupe_catalog_rows()

    if "uq_classroom_school_name" in _indexes("classroom"):
        op.drop_index("uq_classroom_school_name", table_name="classroom")
    if "ix_classroom_name" in _indexes("classroom"):
        op.drop_index("ix_classroom_name", table_name="classroom")
    if "school_id" in _columns("classroom"):
        op.drop_constraint("classroom_school_id_fkey", "classroom", type_="foreignkey")
        op.drop_index("ix_classroom_school_id", table_name="classroom")
        op.drop_column("classroom", "school_id")
    op.create_index("ix_classroom_name", "classroom", ["name"], unique=True)

    if "school_id" in _columns("section"):
        op.drop_constraint("section_school_id_fkey", "section", type_="foreignkey")
        op.drop_index("ix_section_school_id", table_name="section")
        op.drop_column("section", "school_id")


def downgrade() -> None:
    op.drop_index("ix_classroom_name", table_name="classroom")
    op.create_index("ix_classroom_name", "classroom", ["name"])

    op.add_column("classroom", sa.Column("school_id", sa.Integer(), nullable=True))
    op.create_index("ix_classroom_school_id", "classroom", ["school_id"])
    op.create_foreign_key(
        "classroom_school_id_fkey", "classroom", "school", ["school_id"], ["id"]
    )
    op.create_index(
        "uq_classroom_school_name", "classroom", ["school_id", "name"], unique=True
    )

    op.add_column("section", sa.Column("school_id", sa.Integer(), nullable=True))
    op.create_index("ix_section_school_id", "section", ["school_id"])
    op.create_foreign_key(
        "section_school_id_fkey", "section", "school", ["school_id"], ["id"]
    )
