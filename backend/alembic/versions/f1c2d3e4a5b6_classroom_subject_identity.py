"""Classroom subjects own their name (M1).

Revision ID: f1c2d3e4a5b6
Revises: e5a7b9c1d3f4

What this migration does
------------------------
* adds `classroomsubject.name` and `code`, and backfills them from the legacy
  school-wide `subject` row;
* refuses to continue when two **active** subjects in one classroom/year differ
  only by case or whitespace;
* makes the legacy `classroomsubject.subject_id` nullable, because a subject
  created after this phase has no school-wide row;
* makes `subjectteacher.subject_id` nullable for the same reason;
* adds the active-name partial unique index and the school/classroom/year lookup
  index.

It never creates a `classroomsubject` row. Existing rows are the only source.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1c2d3e4a5b6"
down_revision: str | Sequence[str] | None = "e5a7b9c1d3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_NAME_INDEX = "uq_classroomsubject_active_name"
YEAR_INDEX = "ix_classroomsubject_school_classroom_year"


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {row["name"] for row in inspector.get_indexes(table) if row.get("name")}


def _duplicate_names() -> list[tuple]:
    """Active names that collide after trimming, collapsing spaces and lowercasing."""
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        expression = "lower(btrim(regexp_replace(name, '\\s+', ' ', 'g')))"
    else:
        expression = "lower(trim(name))"
    return list(
        op.get_bind()
        .execute(
            sa.text(
                f"""
                SELECT classroom_id, academic_year_id, {expression} AS name_key,
                       count(*) AS rows
                  FROM classroomsubject
                 WHERE status = 'Active'
                 GROUP BY classroom_id, academic_year_id, {expression}
                HAVING count(*) > 1
                """
            )
        )
        .all()
    )


def upgrade() -> None:
    if "classroomsubject" not in sa.inspect(op.get_bind()).get_table_names():
        return

    columns = _columns("classroomsubject")
    if "name" not in columns:
        op.add_column("classroomsubject", sa.Column("name", sa.String(), nullable=True))
    if "code" not in columns:
        op.add_column("classroomsubject", sa.Column("code", sa.String(), nullable=True))

    # Backfill only from the legacy row. A row with no subject_id cannot be named
    # automatically and is reported below instead of being guessed.
    op.execute(
        """
        UPDATE classroomsubject
           SET name = (SELECT name FROM subject WHERE id = subject_id),
               code = (SELECT code FROM subject WHERE id = subject_id)
         WHERE name IS NULL
           AND subject_id IS NOT NULL
        """
    )

    duplicates = _duplicate_names()
    if duplicates:
        detail = ", ".join(
            f"{row[0]}/{row[1]}:{row[2]} x{row[3]}" for row in duplicates
        )
        raise RuntimeError(
            "Cannot create the active subject-name index; resolve these duplicates "
            f"first: {detail}"
        )

    missing = op.get_bind().execute(
        sa.text("SELECT count(*) FROM classroomsubject WHERE name IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError(
            f"{missing} classroomsubject row(s) have no name and no legacy subject "
            "to copy it from. Resolve them before running this migration."
        )

    op.alter_column("classroomsubject", "name", existing_type=sa.String(), nullable=False)

    # New subjects do not point at the old school-wide table.
    op.alter_column(
        "classroomsubject",
        "subject_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    if "subjectteacher" in sa.inspect(op.get_bind()).get_table_names():
        op.alter_column(
            "subjectteacher",
            "subject_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )

    if YEAR_INDEX not in _indexes("classroomsubject"):
        op.create_index(
            YEAR_INDEX,
            "classroomsubject",
            ["school_id", "classroom_id", "academic_year_id"],
        )

    _create_active_name_index()


def _create_active_name_index() -> None:
    if ACTIVE_NAME_INDEX in _indexes("classroomsubject"):
        return
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            f"""
            CREATE UNIQUE INDEX {ACTIVE_NAME_INDEX}
                ON classroomsubject (
                    classroom_id,
                    academic_year_id,
                    lower(btrim(regexp_replace(name, '\\s+', ' ', 'g')))
                )
             WHERE status = 'Active'
            """
        )
    else:
        op.execute(
            f"""
            CREATE UNIQUE INDEX {ACTIVE_NAME_INDEX}
                ON classroomsubject (
                    classroom_id,
                    academic_year_id,
                    lower(trim(name))
                )
             WHERE status = 'Active'
            """
        )


def downgrade() -> None:
    if "classroomsubject" not in sa.inspect(op.get_bind()).get_table_names():
        return
    bind = op.get_bind()
    nulls = bind.execute(
        sa.text("SELECT count(*) FROM classroomsubject WHERE subject_id IS NULL")
    ).scalar_one()
    if nulls:
        raise RuntimeError(
            "Cannot downgrade M1 while classroom subjects without a legacy subject_id "
            f"exist ({nulls} row(s)). Restore a pre-M1 backup or remove those rows first."
        )

    if ACTIVE_NAME_INDEX in _indexes("classroomsubject"):
        op.drop_index(ACTIVE_NAME_INDEX, table_name="classroomsubject")
    if YEAR_INDEX in _indexes("classroomsubject"):
        op.drop_index(YEAR_INDEX, table_name="classroomsubject")
    op.alter_column(
        "classroomsubject",
        "subject_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    if "subjectteacher" in sa.inspect(bind).get_table_names():
        op.alter_column(
            "subjectteacher",
            "subject_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
    op.drop_column("classroomsubject", "code")
    op.drop_column("classroomsubject", "name")
