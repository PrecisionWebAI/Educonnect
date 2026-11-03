"""`classname` + `section` are global catalogs; `classroom` is the school's room.

Revision ID: f9e0f1a2b3cf
Revises: f9e0f1a2b3ce
Create Date: 2026-11-03

The model
---------
`classname` (15 rows: Nursery, LKG, UKG, Class 1 … Class 12) and `section`
(A … J, 10 rows) are **platform** catalogs: no `school_id`, never growing with a
new school, and every class/section dropdown reads them.

`classroom` is the opposite - it belongs to one school and grows with it: one row
per class-section the school actually uses ("Class 10-A"). It is **not** seeded
in bulk; the row is created the moment a student is registered into that
class-section (or a class teacher / timetable period needs it).

Three kinds of reference
------------------------
    room    -> classroom.id        the class-section a student/register/period belongs to
    class   -> classname.class_id  the class alone (fee structure, paper, source)
    section -> section.section_id  the letter alone (a paper's section, an application's)

Because each new `classroom` row reuses the id of the per-school `section` row it
replaces, every referencing row keeps the uuid it already had - only the foreign
key is re-pointed. Old `section` rows that nothing referenced are **not** carried
over (the old seeder wrote all 150 per school; a room exists because something
uses it).

Every step is guarded, so this is safe on a database that already ran the
reverted revision (its columns are adopted here) and on a fresh one.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3cf"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The fixed class list — `(name, level, stage)`. `academics/seed.py` is the
#: source of truth for the application; this copy keeps the migration standalone.
CLASS_CATALOG: tuple[tuple[str, int, str], ...] = (
    ("Nursery", 0, "pre_primary"),
    ("LKG", 1, "pre_primary"),
    ("UKG", 2, "pre_primary"),
    ("Class 1", 3, "primary"),
    ("Class 2", 4, "primary"),
    ("Class 3", 5, "primary"),
    ("Class 4", 6, "primary"),
    ("Class 5", 7, "primary"),
    ("Class 6", 8, "middle"),
    ("Class 7", 9, "middle"),
    ("Class 8", 10, "middle"),
    ("Class 9", 11, "secondary"),
    ("Class 10", 12, "secondary"),
    ("Class 11", 13, "senior_secondary"),
    ("Class 12", 14, "senior_secondary"),
)

#: Every class runs the same ten sections.
SECTION_NAMES: tuple[str, ...] = tuple("ABCDEFGHIJ")

#: Where the old per-school `section` table is parked while its name is reused.
OLD_SECTION = "classroom_section_old"

#: (table, column) — the column names a **room**; renamed to `classroom_id`.
ROOM_COLUMNS: tuple[tuple[str, str], ...] = (
    ("studentprofile", "section_id"),
    ("attendancerecord", "section_id"),
    ("timetableperiod", "section_id"),
    ("homeworkassignment", "section_id"),
    ("classlog", "section_id"),
    ("subjectteacher", "section_id"),
    ("syllabusprogress", "section_id"),
)

#: (table, column) — the column names a **class**; renamed to `class_id`.
CLASS_COLUMNS: tuple[tuple[str, str], ...] = (
    ("feestructure", "classroom_id"),
    ("paperdraft", "classroom_id"),
    ("examsource", "classroom_id"),
    ("questionusagelog", "classroom_id"),
    ("educationreport", "classroom_id"),
)

#: (table, column) — the column names a **section** (the letter).
SECTION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("paperdraft", "section_id"),
    ("student_admission_form", "applied_section_id"),
)

#: Admission columns that name a class (they already hold ids on a database that
#: ran the reverted revision; the wording columns beside them stay as the record).
ADMISSION_CLASS_COLUMNS: tuple[str, ...] = (
    "applied_class_id",
    "current_class_id",
    "previous_class_id",
    "separation_class_id",
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


def _foreign_keys(table: str, column: str) -> list[str]:
    """The FK constraint names on that column (there should be at most one)."""
    rows = _bind().execute(
        sa.text(
            "SELECT tc.constraint_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = tc.constraint_name "
            "WHERE tc.table_schema = 'public' AND tc.table_name = :table "
            "AND tc.constraint_type = 'FOREIGN KEY' AND kcu.column_name = :column"
        ),
        {"table": table, "column": column},
    ).fetchall()
    return [row[0] for row in rows]


def _drop_foreign_keys(table: str, column: str) -> None:
    for constraint in _foreign_keys(table, column):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")


def _add_foreign_key(table: str, column: str, parent: str, parent_column: str) -> None:
    op.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {table}_{column}_fkey "
        f"FOREIGN KEY ({column}) REFERENCES {parent} ({parent_column})"
    )


def _rename_column(table: str, old: str, new: str) -> None:
    """Rename a column, keeping its data (its FK is dropped - the target changes)."""
    if not _has_table(table) or not _has_column(table, old) or _has_column(table, new):
        return
    _drop_foreign_keys(table, old)
    op.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")


# ---------------------------------------------------------------------------
# 1. The two global catalogs
# ---------------------------------------------------------------------------


def _ensure_classname() -> None:
    """`classname` — the platform's 15 classes. No `school_id`: it never grows."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS classname (
            class_id uuid NOT NULL,
            classname varchar NOT NULL,
            stage varchar NOT NULL DEFAULT 'primary',
            level integer NOT NULL DEFAULT 0,
            CONSTRAINT classname_pkey PRIMARY KEY (class_id)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_classname_name ON classname (classname)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_classname_level ON classname (level)")

    values = ", ".join(
        f"('{name}', {level}, '{stage}')" for name, level, stage in CLASS_CATALOG
    )
    op.execute(
        f"""
        INSERT INTO classname (class_id, classname, stage, level)
        SELECT gen_random_uuid(), v.name, v.stage, v.level
        FROM (VALUES {values}) AS v(name, level, stage)
        WHERE NOT EXISTS (
            SELECT 1 FROM classname c WHERE lower(c.classname) = lower(v.name)
        )
        """
    )


def _free_old_section_names() -> None:
    """Free the `section_*` names the renamed table kept.

    Postgres keeps a table's constraint and index **names** when the table is
    renamed, and the new platform `section` needs `section_pkey`. So they are
    prefixed here before the new table is created.
    """
    rows = _bind().execute(
        sa.text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = :table"
        ),
        {"table": OLD_SECTION},
    ).fetchall()
    for (name,) in rows:
        if name.startswith("section"):
            op.execute(
                f"ALTER TABLE {OLD_SECTION} RENAME CONSTRAINT {name} TO old_{name}"
            )

    indexes = _bind().execute(
        sa.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = :table"
        ),
        {"table": OLD_SECTION},
    ).fetchall()
    for (name,) in indexes:
        if name.startswith(("ix_section", "uq_section")):
            op.execute(f'ALTER INDEX "{name}" RENAME TO old_{name}')


def _ensure_section() -> None:
    """`section` — the platform's A-J list.

    The name is taken by the per-school table today, so that table is parked as
    `classroom_section_old` first: its rows become the school's `classroom` rows
    (step 3) and it is dropped at the end.
    """
    if _has_table("section") and _has_column("section", "school_id"):
        op.execute(f"ALTER TABLE section RENAME TO {OLD_SECTION}")
    if _has_table(OLD_SECTION):
        _free_old_section_names()

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS section (
            section_id uuid NOT NULL,
            section_name varchar NOT NULL,
            CONSTRAINT section_pkey PRIMARY KEY (section_id)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_section_name ON section (section_name)"
    )

    values = ", ".join(f"('{name}')" for name in SECTION_NAMES)
    op.execute(
        f"""
        INSERT INTO section (section_id, section_name)
        SELECT gen_random_uuid(), v.name
        FROM (VALUES {values}) AS v(name)
        WHERE NOT EXISTS (
            SELECT 1 FROM section s WHERE upper(s.section_name) = upper(v.name)
        )
        """
    )


# ---------------------------------------------------------------------------
# 2. `classroom` becomes the school's room table
# ---------------------------------------------------------------------------


def _classroom_room_columns() -> None:
    """Add `class_id`, `section_id`, `class_teacher_id` to `classroom`."""
    # The old class columns are still NOT NULL until they are dropped at the end,
    # and a room row does not carry them - so they are relaxed first.
    for column in ("name", "level", "stage"):
        if _has_column("classroom", column):
            op.execute(f"ALTER TABLE classroom ALTER COLUMN {column} DROP NOT NULL")

    for column in ("class_id", "section_id"):
        if not _has_column("classroom", column):
            op.execute(f"ALTER TABLE classroom ADD COLUMN {column} uuid")
        _drop_foreign_keys("classroom", column)
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_classroom_{column} ON classroom ({column})"
        )
    if not _has_column("classroom", "class_teacher_id"):
        op.execute("ALTER TABLE classroom ADD COLUMN class_teacher_id uuid")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_classroom_class_teacher_id "
            "ON classroom (class_teacher_id)"
        )

    _add_foreign_key("classroom", "class_id", "classname", "class_id")
    _add_foreign_key("classroom", "section_id", "section", "section_id")
    _add_foreign_key("classroom", "class_teacher_id", "employee", "id")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_classroom_school_class_section "
        "ON classroom (school_id, class_id, section_id)"
    )


def _move_rooms() -> None:
    """The old per-school sections that are **in use** become `classroom` rows.

    The id is reused on purpose: every referencing row (a student, a register, a
    period) keeps the uuid it already had, so only the foreign key has to move.
    A section nothing referenced is left behind - rooms are not bulk-seeded.
    """
    if not _has_table(OLD_SECTION):
        return
    op.execute(
        f"""
        INSERT INTO classroom (id, school_id, class_id, section_id, class_teacher_id)
        SELECT old.id, old.school_id, cn.class_id, gs.section_id, old.class_teacher_id
        FROM {OLD_SECTION} old
        JOIN classroom c ON c.id = old.classroom_id
        JOIN classname cn ON lower(cn.classname) = lower(c.name)
        JOIN section gs ON upper(gs.section_name) = upper(old.name)
        WHERE old.class_teacher_id IS NOT NULL
           OR EXISTS (SELECT 1 FROM studentprofile s WHERE s.section_id = old.id)
           OR EXISTS (SELECT 1 FROM attendancerecord a WHERE a.section_id = old.id)
           OR EXISTS (SELECT 1 FROM timetableperiod t WHERE t.section_id = old.id)
           OR EXISTS (SELECT 1 FROM homeworkassignment h WHERE h.section_id = old.id)
           OR EXISTS (SELECT 1 FROM classlog l WHERE l.section_id = old.id)
           OR EXISTS (SELECT 1 FROM subjectteacher st WHERE st.section_id = old.id)
           OR EXISTS (SELECT 1 FROM syllabusprogress sp WHERE sp.section_id = old.id)
        ON CONFLICT (id) DO NOTHING
        """
    )


def _repoint_room_columns() -> None:
    """`section_id` -> `classroom_id`, pointing at the school's room."""
    for table, column in ROOM_COLUMNS:
        if not _has_table(table):
            continue
        _rename_column(table, column, "classroom_id")
        if not _has_column(table, "classroom_id"):
            continue
        _drop_foreign_keys(table, "classroom_id")
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_classroom_id "
            f"ON {table} (classroom_id)"
        )
        _add_foreign_key(table, "classroom_id", "classroom", "id")


def _repoint_class_columns() -> None:
    """`classroom_id` -> `class_id`, pointing at the platform's class.

    The values are re-mapped **before** the old class rows go: each one named a
    school's class row, and the class it named is now a `classname` row.
    """
    for table, column in CLASS_COLUMNS:
        if not _has_table(table):
            continue
        _rename_column(table, column, "class_id")
        if not _has_column(table, "class_id"):
            continue
        _drop_foreign_keys(table, "class_id")
        op.execute(
            f"""
            UPDATE {table} t SET class_id = cn.class_id
            FROM classroom c
            JOIN classname cn ON lower(cn.classname) = lower(c.name)
            WHERE t.class_id = c.id AND c.name IS NOT NULL
            """
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_class_id ON {table} (class_id)"
        )
        _add_foreign_key(table, "class_id", "classname", "class_id")


def _repoint_admission_class_columns() -> None:
    """The admission form's class columns point at the platform's class."""
    if not _has_table("student_admission_form"):
        return
    for column in ADMISSION_CLASS_COLUMNS:
        if not _has_column("student_admission_form", column):
            continue
        _drop_foreign_keys("student_admission_form", column)
        op.execute(
            f"""
            UPDATE student_admission_form a SET {column} = cn.class_id
            FROM classroom c
            JOIN classname cn ON lower(cn.classname) = lower(c.name)
            WHERE a.{column} = c.id AND c.name IS NOT NULL
            """
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_student_admission_form_{column} "
            f"ON student_admission_form ({column})"
        )
        _add_foreign_key("student_admission_form", column, "classname", "class_id")


def _repoint_section_columns() -> None:
    """A column that names the letter now points at the platform's `section`."""
    for table, column in SECTION_COLUMNS:
        if not _has_table(table) or not _has_column(table, column):
            continue
        _drop_foreign_keys(table, column)
        if _has_table(OLD_SECTION):
            op.execute(
                f"""
                UPDATE {table} t SET {column} = gs.section_id
                FROM {OLD_SECTION} old
                JOIN section gs ON upper(gs.section_name) = upper(old.name)
                WHERE t.{column} = old.id
                """
            )
        _add_foreign_key(table, column, "section", "section_id")


def _retire_old_class_rows() -> None:
    """The school's old class rows go; `classname` holds the class now.

    Everything that pointed at them has been re-pointed (step 5), so what is left
    in `classroom` is exactly the rooms - one row per class-section in use.
    """
    if not _has_column("classroom", "name"):
        return
    op.execute("DELETE FROM classroom WHERE class_id IS NULL AND section_id IS NULL")
    op.execute("DROP INDEX IF EXISTS uq_classroom_school_name")
    op.execute("DROP INDEX IF EXISTS ix_classroom_name")
    op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS name")
    op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS level")
    op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS stage")


def _drop_old_section() -> None:
    """The per-school section table is fully replaced (its rows are rooms now)."""
    op.execute(f"DROP TABLE IF EXISTS {OLD_SECTION}")


def upgrade() -> None:
    """Global class/section catalogs, and `classroom` as the school's room."""
    _ensure_classname()
    _ensure_section()
    _classroom_room_columns()
    _move_rooms()
    _repoint_room_columns()
    _repoint_class_columns()
    _repoint_admission_class_columns()
    _repoint_section_columns()
    # The old per-school section table still points at the old class rows, so it
    # goes before them - nothing else references a class row by then.
    _drop_old_section()
    _retire_old_class_rows()
    print(
        "[class] classname (15) + section (A-J) are platform catalogs; "
        "classroom holds one row per class-section in use"
    )


def downgrade() -> None:
    """Put the per-school class/section tables back.

    Only the columns this revision added are dropped; the class/section **ids**
    that were re-pointed cannot be un-mapped (the rows they named are gone), so
    the wording columns the application kept are the way back.
    """
    for table, column in ROOM_COLUMNS:
        if _has_table(table) and _has_column(table, "classroom_id"):
            _drop_foreign_keys(table, "classroom_id")
    for table, _ in CLASS_COLUMNS:
        if _has_table(table) and _has_column(table, "class_id"):
            _drop_foreign_keys(table, "class_id")
    if _has_column("classroom", "class_id"):
        op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS class_id")
    if _has_column("classroom", "section_id"):
        op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS section_id")
    if _has_column("classroom", "class_teacher_id"):
        op.execute("ALTER TABLE classroom DROP COLUMN IF EXISTS class_teacher_id")
    op.execute("DROP INDEX IF EXISTS uq_classroom_school_class_section")
    op.execute("DROP TABLE IF EXISTS section")
    op.execute("DROP TABLE IF EXISTS classname")
