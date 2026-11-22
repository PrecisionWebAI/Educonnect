"""Chapters and class operations point at classroom subjects (M2).

Revision ID: f2d3e4a5b6c7
Revises: f1c2d3e4a5b6

What this migration does
------------------------
* `subjectteacher`: every row is linked to an **existing** `classroomsubject`;
  adds `UNIQUE(classroom_subject_id, effective_from)`.
* `chapter`: becomes section-owned. Each old class-level chapter is kept as the
  chapter of the first eligible section (its id - and so every
  `exam_paper_chapter` link - is preserved) and copied for every other section
  that already has that subject. `chapterprogress` is folded into the copy that
  belongs to its section.
* `timetableperiod`, `homeworkassignment`, `attendancerecord`, `classlog`: gain
  `classroom_subject_id`, backfilled from the existing section subject.
* attendance: the per-subject unique key moves to `classroom_subject_id` and the
  day-level partial unique index covers rows with neither subject column.

Hard rules (phase3.md, Section 4)
---------------------------------
* take a full database backup before running it;
* no `classroomsubject` row is created - ever;
* a row that cannot be mapped is reported and the migration aborts; nothing is
  silently dropped, guessed or set to NULL;
* before/after counts are compared and any unexplained difference aborts;
* legacy columns stay (nullable) until M5 so older modules remain readable.

The data steps are plain functions of a connection (`run_data_steps`) so the test
suite can run them on SQLite; the schema-tightening steps (NOT NULL, FKs, unique
constraints) are PostgreSQL-only DDL.
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "f2d3e4a5b6c7"
down_revision: str | Sequence[str] | None = "f1c2d3e4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tables whose rows carry a `(classroom_id, subject_id)` pair to repoint, and the
#: column that names the row's own academic year (None = the table has none).
OPERATIONAL_TABLES: tuple[tuple[str, str | None], ...] = (
    ("timetableperiod", "academic_year_id"),
    ("homeworkassignment", None),
    ("attendancerecord", None),
    ("classlog", None),
)
#: Tables where the section subject is required once backfilled.
REQUIRED_LINK = ("timetableperiod", "homeworkassignment")

CHAPTER_UNIQUE = "uq_chapter_classroom_subject_sequence"
TEACHER_UNIQUE = "uq_subjectteacher_cs_from"
ATTENDANCE_UNIQUE = "uq_attendancerecord_school_student_date_classroom_subject"
ATTENDANCE_DAY_INDEX = "uq_attendancerecord_school_student_date_day"


class MigrationAbort(RuntimeError):
    """A row could not be mapped, or a count did not add up. Nothing is committed."""


# --------------------------------------------------------------------------- inspect


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _indexes(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {
        row["name"] for row in sa.inspect(bind).get_indexes(table) if row.get("name")
    }


def _uniques(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {
        row["name"]
        for row in sa.inspect(bind).get_unique_constraints(table)
        if row.get("name")
    }


def _foreign_keys(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {
        row["name"]
        for row in sa.inspect(bind).get_foreign_keys(table)
        if row.get("name")
    }


def _count(bind, sql: str, **params) -> int:
    return int(bind.execute(sa.text(sql), params).scalar_one())


def _add_column(bind, table: str, column: sa.Column) -> None:
    if table in _tables(bind) and column.name not in _columns(bind, table):
        op.add_column(table, column)


# ------------------------------------------------------------------------ snapshots


def snapshot(bind) -> dict[str, int]:
    """Row counts the verification gate compares against."""
    counts = {"classroomsubject": _count(bind, "SELECT count(*) FROM classroomsubject")}
    for table in (
        "chapter",
        "chapterprogress",
        "subjectteacher",
        *(name for name, _ in OPERATIONAL_TABLES),
    ):
        if table in _tables(bind):
            counts[table] = _count(bind, f"SELECT count(*) FROM {table}")
    return counts


# ------------------------------------------------------------------ subject teacher


def _current_year_sql(alias: str) -> str:
    return (
        "(SELECT id FROM academic_year "
        f"WHERE school_id = {alias}.school_id AND is_current = true LIMIT 1)"
    )


def link_subject_teachers(bind) -> list[str]:
    """Fill a missing `classroom_subject_id` from the existing section subject."""
    if "subjectteacher" not in _tables(bind):
        return []
    bind.execute(
        sa.text(
            f"""
            UPDATE subjectteacher
               SET classroom_subject_id = (
                   SELECT cs.id
                     FROM classroomsubject AS cs
                    WHERE cs.school_id = subjectteacher.school_id
                      AND cs.classroom_id = subjectteacher.classroom_id
                      AND cs.subject_id = subjectteacher.subject_id
                      AND cs.academic_year_id = COALESCE(
                          subjectteacher.academic_year_id,
                          {_current_year_sql("subjectteacher")}
                      )
               )
             WHERE classroom_subject_id IS NULL
               AND subject_id IS NOT NULL
            """
        )
    )
    rows = bind.execute(
        sa.text(
            """
            SELECT id, classroom_id, subject_id, academic_year_id
              FROM subjectteacher
             WHERE classroom_subject_id IS NULL
            """
        )
    ).all()
    return [
        f"subjectteacher id={row[0]} classroom={row[1]} subject={row[2]} "
        f"year={row[3]}: no existing classroomsubject"
        for row in rows
    ]


# ------------------------------------------------------------------------- chapters


def _chapter_targets(bind, chapter) -> list[tuple]:
    """Existing section subjects of this chapter's class/subject/year, stable order."""
    return list(
        bind.execute(
            sa.text(
                """
                SELECT cs.id, cs.classroom_id
                  FROM classroomsubject AS cs
                  JOIN classroom AS room ON room.id = cs.classroom_id
                 WHERE cs.school_id = :school_id
                   AND room.class_id = :class_id
                   AND cs.subject_id = :subject_id
                   AND cs.academic_year_id = :academic_year_id
                 ORDER BY room.section_id, cs.id
                """
            ),
            {
                "school_id": chapter["school_id"],
                "class_id": chapter["class_id"],
                "subject_id": chapter["subject_id"],
                "academic_year_id": chapter["academic_year_id"],
            },
        ).all()
    )


def copy_chapters(bind) -> dict:
    """Make every class-level chapter section-owned. Returns the report part."""
    report: dict = {"copies": 0, "orphans": [], "skipped_sections": []}
    if "chapter" not in _tables(bind):
        return report
    has_progress = "chapterprogress" in _tables(bind)
    progress: dict[tuple, tuple] = {}
    if has_progress:
        for row in bind.execute(
            sa.text(
                """
                SELECT id, chapter_id, classroom_id, status, completed_on,
                       completed_by_employee_id
                  FROM chapterprogress
                """
            )
        ).all():
            progress[(str(row[1]), str(row[2]))] = (row[0], row[3], row[4], row[5])
    mapped_progress: set[str] = set()

    chapters = (
        bind.execute(
            sa.text(
                """
            SELECT id, school_id, class_id, subject_id, academic_year_id,
                   sequence, name, planned_date
              FROM chapter
             WHERE classroom_subject_id IS NULL
             ORDER BY class_id, subject_id, sequence
            """
            )
        )
        .mappings()
        .all()
    )

    for chapter in chapters:
        targets = _chapter_targets(bind, chapter)
        if not targets:
            report["orphans"].append(
                f"chapter id={chapter['id']} class={chapter['class_id']} "
                f"subject={chapter['subject_id']} year={chapter['academic_year_id']}: "
                "no section of this class has the subject"
            )
            continue

        for index, (classroom_subject_id, classroom_id) in enumerate(targets):
            found = progress.get((str(chapter["id"]), str(classroom_id)))
            if found is not None:
                mapped_progress.add(str(found[0]))
            values = {
                "status": found[1] if found else "Pending",
                "completed_on": found[2] if found else None,
                "completed_by_employee_id": found[3] if found else None,
            }
            clash = bind.execute(
                sa.text(
                    """
                    SELECT id FROM chapter
                     WHERE classroom_subject_id = :classroom_subject_id
                       AND sequence = :sequence
                    """
                ),
                {
                    "classroom_subject_id": classroom_subject_id,
                    "sequence": chapter["sequence"],
                },
            ).first()
            if clash is not None:
                report["orphans"].append(
                    f"chapter id={chapter['id']}: section subject "
                    f"{classroom_subject_id} already has sequence {chapter['sequence']}"
                )
                continue

            if index == 0:
                # The canonical row keeps its id, so exam_paper_chapter links survive.
                bind.execute(
                    sa.text(
                        """
                        UPDATE chapter
                           SET classroom_subject_id = :classroom_subject_id,
                               status = :status,
                               completed_on = :completed_on,
                               completed_by_employee_id = :completed_by_employee_id
                         WHERE id = :id
                        """
                    ),
                    {
                        "id": chapter["id"],
                        "classroom_subject_id": classroom_subject_id,
                        **values,
                    },
                )
                continue

            bind.execute(
                sa.text(
                    """
                    INSERT INTO chapter (
                        id, school_id, classroom_subject_id, class_id, subject_id,
                        academic_year_id, sequence, name, planned_date, status,
                        completed_on, completed_by_employee_id
                    ) VALUES (
                        :id, :school_id, :classroom_subject_id, NULL, NULL,
                        :academic_year_id, :sequence, :name, :planned_date, :status,
                        :completed_on, :completed_by_employee_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "school_id": chapter["school_id"],
                    "classroom_subject_id": classroom_subject_id,
                    "academic_year_id": chapter["academic_year_id"],
                    "sequence": chapter["sequence"],
                    "name": chapter["name"],
                    "planned_date": chapter["planned_date"],
                    **values,
                },
            )
            report["copies"] += 1

    if has_progress:
        unmapped = {str(value[0]) for value in progress.values()} - mapped_progress
        for key, value in progress.items():
            if str(value[0]) in unmapped:
                report["orphans"].append(
                    f"chapterprogress id={value[0]} chapter={key[0]} "
                    f"classroom={key[1]}: that section has no copy of the chapter"
                )
    return report


# ---------------------------------------------------------------- operational rows


def repoint_rows(bind, table: str, year_column: str | None) -> list[str]:
    """Backfill `classroom_subject_id` from `(classroom_id, subject_id, year)`."""
    if table not in _tables(bind):
        return []
    year = (
        f"COALESCE({table}.{year_column}, {_current_year_sql(table)})"
        if year_column
        else _current_year_sql(table)
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE {table}
               SET classroom_subject_id = (
                   SELECT cs.id
                     FROM classroomsubject AS cs
                    WHERE cs.school_id = {table}.school_id
                      AND cs.classroom_id = {table}.classroom_id
                      AND cs.subject_id = {table}.subject_id
                      AND cs.academic_year_id = {year}
               )
             WHERE subject_id IS NOT NULL
               AND classroom_subject_id IS NULL
            """
        )
    )
    orphans = [
        f"{table} id={row[0]} classroom={row[1]} subject={row[2]}: "
        "no existing classroomsubject for that section/subject/year"
        for row in bind.execute(
            sa.text(
                f"""
                SELECT id, classroom_id, subject_id FROM {table}
                 WHERE subject_id IS NOT NULL AND classroom_subject_id IS NULL
                """
            )
        ).all()
    ]
    if table in REQUIRED_LINK:
        orphans += [
            f"{table} id={row[0]}: names no subject at all"
            for row in bind.execute(
                sa.text(
                    f"SELECT id FROM {table} "
                    "WHERE subject_id IS NULL AND classroom_subject_id IS NULL"
                )
            ).all()
        ]
    return orphans


# ------------------------------------------------------------------------- the gate


def verify(bind, before: dict[str, int], copies: int) -> dict[str, dict]:
    """before / expected_after / actual_after per table; raise on any difference."""
    after = snapshot(bind)
    expected = dict(before)
    if "chapter" in expected:
        expected["chapter"] = before["chapter"] + copies
    report = {
        table: {
            "before": before[table],
            "expected_after": expected[table],
            "actual_after": after.get(table, 0),
            "delta": after.get(table, 0) - expected[table],
        }
        for table in before
    }
    wrong = {table: row for table, row in report.items() if row["delta"] != 0}
    if wrong:
        raise MigrationAbort(f"M2 row counts do not add up: {wrong}")
    return report


def run_data_steps(bind) -> dict:
    """Every M2 data step, then the count gate. Raises `MigrationAbort` on a problem."""
    before = snapshot(bind)
    orphans = link_subject_teachers(bind)
    chapter_report = copy_chapters(bind)
    orphans += chapter_report["orphans"]
    for table, year_column in OPERATIONAL_TABLES:
        orphans += repoint_rows(bind, table, year_column)
    if orphans:
        raise MigrationAbort(
            "M2 cannot map these rows to an existing classroom subject; nothing was "
            "created. Resolve them and re-run:\n  " + "\n  ".join(orphans)
        )
    if "chapter" in _tables(bind):
        bind.execute(
            sa.text("UPDATE chapter SET status = 'Pending' WHERE status IS NULL")
        )
    return {
        "counts": verify(bind, before, chapter_report["copies"]),
        "copies": chapter_report["copies"],
        "orphans": [],
    }


# ------------------------------------------------------------------------ upgrade


def _add_columns(bind) -> None:
    if "chapter" in _tables(bind):
        _add_column(
            bind, "chapter", sa.Column("classroom_subject_id", sa.Uuid(), nullable=True)
        )
        _add_column(bind, "chapter", sa.Column("status", sa.String(), nullable=True))
        _add_column(
            bind, "chapter", sa.Column("completed_on", sa.Date(), nullable=True)
        )
        _add_column(
            bind,
            "chapter",
            sa.Column("completed_by_employee_id", sa.Uuid(), nullable=True),
        )
    for table, _ in OPERATIONAL_TABLES:
        _add_column(
            bind, table, sa.Column("classroom_subject_id", sa.Uuid(), nullable=True)
        )


def _loosen_legacy(bind) -> None:
    """New rows do not name the school-wide subject; old columns become optional."""
    if bind.dialect.name != "postgresql":
        return
    for table, column in (
        ("chapter", "class_id"),
        ("chapter", "subject_id"),
        ("timetableperiod", "subject_id"),
        ("homeworkassignment", "subject_id"),
    ):
        if column in _columns(bind, table):
            op.alter_column(table, column, existing_type=sa.Uuid(), nullable=True)


def _index(bind, table: str, name: str, columns: list[str]) -> None:
    if table in _tables(bind) and name not in _indexes(bind, table):
        op.create_index(name, table, columns)


def _foreign_key(bind, table: str, column: str, target: str) -> None:
    name = f"fk_{table}_{column}"
    if table in _tables(bind) and name not in _foreign_keys(bind, table):
        op.create_foreign_key(name, table, target, [column], ["id"])


def _tighten(bind) -> None:
    """Indexes everywhere; NOT NULL, FKs and unique constraints on PostgreSQL."""
    _index(bind, "chapter", "ix_chapter_classroom_subject_id", ["classroom_subject_id"])
    _index(
        bind,
        "chapter",
        "ix_chapter_completed_by_employee_id",
        ["completed_by_employee_id"],
    )
    for table, _ in OPERATIONAL_TABLES:
        _index(
            bind, table, f"ix_{table}_classroom_subject_id", ["classroom_subject_id"]
        )

    if "attendancerecord" in _tables(bind):
        # The day-level row is the one that names neither subject column.
        if ATTENDANCE_DAY_INDEX in _indexes(bind, "attendancerecord"):
            op.drop_index(ATTENDANCE_DAY_INDEX, table_name="attendancerecord")
        op.execute(
            f"""
            CREATE UNIQUE INDEX {ATTENDANCE_DAY_INDEX}
                ON attendancerecord (school_id, student_id, date)
             WHERE classroom_subject_id IS NULL AND subject_id IS NULL
            """
        )

    if bind.dialect.name != "postgresql":
        return

    if "chapter" in _tables(bind):
        op.alter_column("chapter", "status", existing_type=sa.String(), nullable=False)
        op.alter_column(
            "chapter", "classroom_subject_id", existing_type=sa.Uuid(), nullable=False
        )
        if CHAPTER_UNIQUE not in _uniques(bind, "chapter"):
            op.create_unique_constraint(
                CHAPTER_UNIQUE, "chapter", ["classroom_subject_id", "sequence"]
            )
        if "ck_chapter_status" not in {
            row["name"] for row in sa.inspect(bind).get_check_constraints("chapter")
        }:
            op.create_check_constraint(
                "ck_chapter_status",
                "chapter",
                "status IN ('Pending', 'In progress', 'Completed')",
            )
        _foreign_key(bind, "chapter", "classroom_subject_id", "classroomsubject")
        _foreign_key(bind, "chapter", "completed_by_employee_id", "employee")

    for table in REQUIRED_LINK:
        if table in _tables(bind):
            op.alter_column(
                table, "classroom_subject_id", existing_type=sa.Uuid(), nullable=False
            )
    for table, _ in OPERATIONAL_TABLES:
        _foreign_key(bind, table, "classroom_subject_id", "classroomsubject")

    if "subjectteacher" in _tables(bind) and TEACHER_UNIQUE not in _uniques(
        bind, "subjectteacher"
    ):
        op.create_unique_constraint(
            TEACHER_UNIQUE, "subjectteacher", ["classroom_subject_id", "effective_from"]
        )

    if "attendancerecord" in _tables(bind) and ATTENDANCE_UNIQUE not in _uniques(
        bind, "attendancerecord"
    ):
        op.create_unique_constraint(
            ATTENDANCE_UNIQUE,
            "attendancerecord",
            ["school_id", "student_id", "date", "classroom_subject_id"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    if "classroomsubject" not in _tables(bind):
        return
    _add_columns(bind)
    _loosen_legacy(bind)
    report = run_data_steps(bind)
    for table, row in report["counts"].items():
        print(f"[M2] {table}: {row}")
    print(f"[M2] chapter copies created for other sections: {report['copies']}")
    _tighten(bind)


# ---------------------------------------------------------------------- downgrade


def downgrade() -> None:
    """Best effort, and lossy - restore the pre-M2 backup when you can.

    Section-level chapters that have no legacy class/subject (the copies M2 made, and
    every chapter added after M2) are deleted; the canonical rows go back to being
    class-level. Progress recorded on chapters after M2 is lost. Legacy columns were
    never dropped, so timetable/homework/attendance rows keep reading.
    """
    bind = op.get_bind()
    if "classroomsubject" not in _tables(bind):
        return

    missing = 0
    for table in REQUIRED_LINK:
        if table in _tables(bind):
            missing += _count(
                bind, f"SELECT count(*) FROM {table} WHERE subject_id IS NULL"
            )
    if missing:
        raise RuntimeError(
            f"{missing} timetable/homework row(s) were written after M2 without a legacy "
            "subject_id. Restore the pre-M2 backup instead of downgrading."
        )

    if "attendancerecord" in _tables(bind):
        if ATTENDANCE_UNIQUE in _uniques(bind, "attendancerecord"):
            op.drop_constraint(ATTENDANCE_UNIQUE, "attendancerecord", type_="unique")
        if ATTENDANCE_DAY_INDEX in _indexes(bind, "attendancerecord"):
            op.drop_index(ATTENDANCE_DAY_INDEX, table_name="attendancerecord")
        op.execute(
            f"""
            CREATE UNIQUE INDEX {ATTENDANCE_DAY_INDEX}
                ON attendancerecord (school_id, student_id, date)
             WHERE subject_id IS NULL
            """
        )
    if "subjectteacher" in _tables(bind) and TEACHER_UNIQUE in _uniques(
        bind, "subjectteacher"
    ):
        op.drop_constraint(TEACHER_UNIQUE, "subjectteacher", type_="unique")

    for table, _ in OPERATIONAL_TABLES:
        if table not in _tables(bind):
            continue
        name = f"fk_{table}_classroom_subject_id"
        if name in _foreign_keys(bind, table):
            op.drop_constraint(name, table, type_="foreignkey")
        index = f"ix_{table}_classroom_subject_id"
        if index in _indexes(bind, table):
            op.drop_index(index, table_name=table)
        if "classroom_subject_id" in _columns(bind, table):
            op.drop_column(table, "classroom_subject_id")

    if "chapter" in _tables(bind):
        op.execute("DELETE FROM chapter WHERE class_id IS NULL OR subject_id IS NULL")
        for name in (
            "fk_chapter_classroom_subject_id",
            "fk_chapter_completed_by_employee_id",
        ):
            if name in _foreign_keys(bind, "chapter"):
                op.drop_constraint(name, "chapter", type_="foreignkey")
        if CHAPTER_UNIQUE in _uniques(bind, "chapter"):
            op.drop_constraint(CHAPTER_UNIQUE, "chapter", type_="unique")
        if bind.dialect.name == "postgresql":
            op.execute(
                "ALTER TABLE chapter DROP CONSTRAINT IF EXISTS ck_chapter_status"
            )
        for index in (
            "ix_chapter_classroom_subject_id",
            "ix_chapter_completed_by_employee_id",
        ):
            if index in _indexes(bind, "chapter"):
                op.drop_index(index, table_name="chapter")
        for column in (
            "completed_by_employee_id",
            "completed_on",
            "status",
            "classroom_subject_id",
        ):
            if column in _columns(bind, "chapter"):
                op.drop_column("chapter", column)
        if bind.dialect.name == "postgresql":
            for column in ("class_id", "subject_id"):
                op.alter_column(
                    "chapter", column, existing_type=sa.Uuid(), nullable=False
                )
