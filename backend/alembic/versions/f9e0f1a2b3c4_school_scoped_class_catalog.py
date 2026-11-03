"""`classroom` and `section` become school-owned; each school gets its own catalog.

Revision ID: f9e0f1a2b3c4
Revises: f8d9e0f1a2b3
Create Date: 2026-11-02

Why:
  These were the last two school tables without a `school_id`. One "Class 6" row was
  shared by every school on the platform, so a class teacher assigned to it, a fee
  structure filed against it or a student placed in it was visible everywhere.
  `app/core/db.py` narrows every query by `school_id`, so isolation is only as good
  as the columns it can filter on.

  Every existing school gets its own copy of the 15 classes and their 150 sections;
  the rows that pointed at the shared catalog are re-pointed at their own school's
  copy; the shared rows are dropped. Uniqueness moves with it: `classroom.name` is
  unique per school (not globally) and `section` is unique per (school, class, name).

  At the time of writing only `studentprofile` (5 rows) and `feestructure` (1 row)
  pointed at the shared catalog - every other child table was empty - so the
  re-point is small. The migration still checks every child table and **refuses to
  run** if a row would be orphaned, rather than silently dropping it.

  The two tables are rebuilt rather than `ALTER`ed, so `school_id` lands second
  (`id, school_id, name, ...`) the way it does in every other table - `ALTER TABLE`
  can only append a column. Their foreign keys are dropped and put back verbatim
  around the swap, because PostgreSQL has no way to reorder columns in place.

Downgrade collapses the catalog back to one shared set (the alphabetically first
school's rows win) and re-points the children at it.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3c4"
down_revision: str | Sequence[str] | None = "f8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Every table holding a `classroom_id` / `section_id`, and which of the two it has.
#: Checked as a whole so a row added later cannot slip past the re-point.
CHILD_TABLES: tuple[tuple[str, str | None, str | None], ...] = (
    ("attendancerecord", "classroom_id", "section_id"),
    ("classdiary", "classroom_id", "section_id"),
    ("classteacherassignment", "classroom_id", "section_id"),
    ("examsource", "classroom_id", None),
    ("feestructure", "classroom_id", None),
    ("homeworkassignment", "classroom_id", "section_id"),
    ("paperdraft", "classroom_id", None),
    ("studentprofile", "classroom_id", "section_id"),
    ("syllabusprogress", None, "section_id"),
    ("teacherassignment", "classroom_id", "section_id"),
    ("timetableperiod", "classroom_id", "section_id"),
)


def _parent_of(column: str) -> str:
    """`classroom_id` -> `classroom`, `section_id` -> `section`."""
    return "classroom" if column == "classroom_id" else "section"


def _assert_children_resolve(bind) -> None:
    """Fail loudly rather than drop a parent a child still points at.

    Run after the children have been re-pointed and before the old tables go: a
    child whose `classroom_id` / `section_id` does not resolve in the freshly built
    table would be orphaned by the drop, so the migration stops instead.
    """
    for table, classroom_column, section_column in CHILD_TABLES:
        for column in (classroom_column, section_column):
            if column is None:
                continue
            parent = _parent_of(column)
            leftover = bind.execute(
                sa.text(
                    f'SELECT count(*) FROM "{table}" c '
                    f"WHERE c.{column} IS NOT NULL AND NOT EXISTS "
                    f"(SELECT 1 FROM {parent} p WHERE p.id = c.{column})"
                )
            ).scalar()
            if leftover:
                raise RuntimeError(
                    f"{table}.{column}: {leftover} row(s) do not resolve in "
                    f"{parent} - refusing to continue."
                )


def _referencing_fks(bind, parents: tuple[str, ...]) -> list[tuple[str, str, str]]:
    """(child table, constraint name, definition) for every FK pointing at `parents`.

    They are dropped before a parent is rebuilt and re-added afterwards: PostgreSQL
    cannot reorder a table's columns in place, so the only route is to create the
    table again - and its foreign keys have to step aside while that happens.
    """
    rows = bind.execute(
        sa.text(
            "SELECT child.relname, c.conname, pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c "
            "JOIN pg_class child ON child.oid = c.conrelid "
            "JOIN pg_class parent ON parent.oid = c.confrelid "
            "WHERE c.contype = 'f' AND parent.relname = ANY(:parents)"
        ),
        {"parents": list(parents)},
    ).all()
    return [(row[0], row[1], row[2]) for row in rows]


def _restore_fks(bind, fks: list[tuple[str, str, str]]) -> None:
    """Put the foreign keys back exactly as they were.

    A rebuilt table may already declare one of them itself (`section` points at
    `classroom` either way), so anything that exists is left alone.
    """
    existing = {
        (row[0], row[1])
        for row in bind.execute(
            sa.text(
                "SELECT t.relname, c.conname FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid WHERE c.contype = 'f'"
            )
        ).all()
    }
    for child, name, definition in fks:
        if (child, name) in existing:
            continue
        op.execute(f'ALTER TABLE "{child}" ADD CONSTRAINT "{name}" {definition}')


def _strip_table(bind, table: str) -> None:
    """Drop a parked table's constraints and indexes so its names are free again.

    `ALTER TABLE ... RENAME TO` leaves index and constraint names untouched, and
    those names are unique per schema - without this the rebuilt table could not
    take `classroom_pkey` or `ix_classroom_name` back.
    """
    for name, kind in bind.execute(
        sa.text(
            "SELECT c.conname, c.contype FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid WHERE t.relname = :t"
        ),
        {"t": table},
    ).all():
        if kind == "p":
            op.drop_constraint(name, table, type_="primary")
        elif kind == "u":
            op.drop_constraint(name, table, type_="unique")
        elif kind == "f":
            op.drop_constraint(name, table, type_="foreignkey")
    for (name,) in bind.execute(
        sa.text("SELECT indexname FROM pg_indexes WHERE tablename = :t"), {"t": table}
    ).all():
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    """Give every school its own copy of the class catalog."""
    bind = op.get_bind()

    # 1. The foreign keys pointing at the two tables step aside - the tables are
    #    rebuilt rather than altered, so that `school_id` can sit second the way it
    #    does in every other table (ALTER TABLE can only append a column).
    fks = _referencing_fks(bind, ("classroom", "section"))
    for child, name, _ in fks:
        op.drop_constraint(name, child, type_="foreignkey")

    # 2. Park the shared catalog under a name the new tables can take, and free its
    #    index/constraint names - they are schema-unique, so the rebuild needs them.
    op.execute("ALTER TABLE classroom RENAME TO classroom_legacy")
    op.execute("ALTER TABLE section RENAME TO section_legacy")
    _strip_table(bind, "section_legacy")
    _strip_table(bind, "classroom_legacy")

    # 3. The new, school-owned tables.
    op.execute(
        "CREATE TABLE classroom ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  name character varying NOT NULL,"
        "  level integer NOT NULL,"
        "  stage character varying NOT NULL,"
        "  CONSTRAINT classroom_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_classroom_school_name UNIQUE (school_id, name),"
        "  CONSTRAINT classroom_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_classroom_name ON classroom (name)")
    op.execute("CREATE INDEX ix_classroom_school_id ON classroom (school_id)")

    op.execute(
        "CREATE TABLE section ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  name character varying NOT NULL,"
        "  classroom_id uuid NOT NULL,"
        "  CONSTRAINT section_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_section_school_classroom_name"
        "    UNIQUE (school_id, classroom_id, name),"
        "  CONSTRAINT section_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT section_classroom_id_fkey FOREIGN KEY (classroom_id)"
        "    REFERENCES classroom (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_section_school_id ON section (school_id)")

    # 4. One copy of the class catalog per school. A single INSERT ... SELECT is
    #    snapshotted before it writes, so the read sees only the rows that were
    #    already there - the copies cannot feed themselves.
    op.execute(
        "CREATE TEMP TABLE _classroom_map (old_id uuid, school_id uuid, new_id uuid)"
    )
    op.execute(
        "INSERT INTO _classroom_map (old_id, school_id, new_id) "
        "SELECT c.id, s.id, gen_random_uuid() "
        "FROM classroom_legacy c CROSS JOIN school s"
    )
    op.execute(
        "INSERT INTO classroom (id, school_id, name, level, stage) "
        "SELECT m.new_id, m.school_id, c.name, c.level, c.stage "
        "FROM _classroom_map m JOIN classroom_legacy c ON c.id = m.old_id"
    )

    op.execute(
        "CREATE TEMP TABLE _section_map (old_id uuid, school_id uuid, new_id uuid)"
    )
    op.execute(
        "INSERT INTO _section_map (old_id, school_id, new_id) "
        "SELECT sec.id, m.school_id, gen_random_uuid() "
        "FROM section_legacy sec JOIN _classroom_map m ON m.old_id = sec.classroom_id"
    )
    op.execute(
        "INSERT INTO section (id, school_id, name, classroom_id) "
        "SELECT sm.new_id, sm.school_id, sec.name, cm.new_id "
        "FROM _section_map sm "
        "JOIN section_legacy sec ON sec.id = sm.old_id "
        "JOIN _classroom_map cm "
        "  ON cm.old_id = sec.classroom_id AND cm.school_id = sm.school_id"
    )

    # 4. Move every child onto its own school's copy.
    op.execute(
        "UPDATE studentprofile sp SET classroom_id = cm.new_id, section_id = sm.new_id "
        "FROM _classroom_map cm, _section_map sm "
        "WHERE cm.old_id = sp.classroom_id AND cm.school_id = sp.school_id "
        "AND sm.old_id = sp.section_id AND sm.school_id = sp.school_id"
    )
    op.execute(
        "UPDATE feestructure f SET classroom_id = cm.new_id "
        "FROM _classroom_map cm "
        "WHERE cm.old_id = f.classroom_id AND cm.school_id = f.school_id"
    )

    # 5. Nothing may still point at a shared row.
    _assert_children_resolve(bind)

    # 6. The shared catalog has served its purpose.
    op.execute("DROP TABLE section_legacy")
    op.execute("DROP TABLE classroom_legacy")
    op.execute("DROP TABLE _section_map")
    op.execute("DROP TABLE _classroom_map")

    # 7. The children get their foreign keys back, now against the new tables.
    _restore_fks(bind, fks)


def downgrade() -> None:
    """Collapse the per-school catalog back to one shared set."""
    bind = op.get_bind()
    keeper = (
        bind.execute(sa.text("SELECT id FROM school ORDER BY name LIMIT 1")).scalar()
    )
    if keeper is None:
        raise RuntimeError("No school to collapse the class catalog onto.")

    # 1. The same rebuild, in reverse: the shared shape has no `school_id`.
    fks = _referencing_fks(bind, ("classroom", "section"))
    for child, name, _ in fks:
        op.drop_constraint(name, child, type_="foreignkey")

    op.execute("ALTER TABLE classroom RENAME TO classroom_legacy")
    op.execute("ALTER TABLE section RENAME TO section_legacy")
    _strip_table(bind, "section_legacy")
    _strip_table(bind, "classroom_legacy")

    op.execute(
        "CREATE TABLE classroom ("
        "  id uuid NOT NULL,"
        "  name character varying NOT NULL,"
        "  level integer NOT NULL,"
        "  stage character varying NOT NULL,"
        "  CONSTRAINT classroom_pkey PRIMARY KEY (id)"
        ")"
    )
    op.execute("CREATE UNIQUE INDEX ix_classroom_name ON classroom (name)")

    op.execute(
        "CREATE TABLE section ("
        "  id uuid NOT NULL,"
        "  name character varying NOT NULL,"
        "  classroom_id uuid NOT NULL,"
        "  CONSTRAINT section_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_section_classroom_name UNIQUE (classroom_id, name),"
        "  CONSTRAINT section_classroom_id_fkey FOREIGN KEY (classroom_id)"
        "    REFERENCES classroom (id)"
        ")"
    )

    # 2. The keeper school's catalog becomes the shared one; every other school's
    #    rows map onto it by class name and section name.
    op.execute("CREATE TEMP TABLE _classroom_map (old_id uuid, new_id uuid)")
    bind.execute(
        sa.text(
            "INSERT INTO _classroom_map (old_id, new_id) "
            "SELECT old.id, keep.id FROM classroom_legacy old "
            "JOIN classroom_legacy keep ON keep.name = old.name AND keep.school_id = :k"
        ),
        {"k": keeper},
    )
    op.execute("CREATE TEMP TABLE _section_map (old_id uuid, new_id uuid)")
    bind.execute(
        sa.text(
            "INSERT INTO _section_map (old_id, new_id) "
            "SELECT olds.id, keeps.id FROM section_legacy olds "
            "JOIN classroom_legacy oldc ON oldc.id = olds.classroom_id "
            "JOIN classroom_legacy keepc "
            "  ON keepc.name = oldc.name AND keepc.school_id = :k "
            "JOIN section_legacy keeps "
            "  ON keeps.classroom_id = keepc.id AND keeps.name = olds.name"
        ),
        {"k": keeper},
    )

    bind.execute(
        sa.text(
            "INSERT INTO classroom (id, name, level, stage) "
            "SELECT keep.id, keep.name, keep.level, keep.stage "
            "FROM classroom_legacy keep WHERE keep.school_id = :k"
        ),
        {"k": keeper},
    )
    bind.execute(
        sa.text(
            "INSERT INTO section (id, name, classroom_id) "
            "SELECT keeps.id, keeps.name, keeps.classroom_id "
            "FROM section_legacy keeps "
            "JOIN classroom_legacy keepc ON keepc.id = keeps.classroom_id "
            "WHERE keepc.school_id = :k"
        ),
        {"k": keeper},
    )

    # 3. Move every child onto the shared rows.
    bind.execute(
        sa.text(
            "UPDATE studentprofile sp "
            "SET classroom_id = cm.new_id, section_id = sm.new_id "
            "FROM _classroom_map cm, _section_map sm "
            "WHERE cm.old_id = sp.classroom_id AND sm.old_id = sp.section_id"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE feestructure f SET classroom_id = cm.new_id "
            "FROM _classroom_map cm WHERE cm.old_id = f.classroom_id"
        )
    )

    _assert_children_resolve(bind)

    op.execute("DROP TABLE section_legacy")
    op.execute("DROP TABLE classroom_legacy")
    op.execute("DROP TABLE _section_map")
    op.execute("DROP TABLE _classroom_map")

    _restore_fks(bind, fks)
