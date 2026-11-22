"""Drop the school-wide subject and every column that pointed at it (M5).

Revision ID: f5b6c7d8e9f0
Revises: f4a5b6c7d8e9

THIS MIGRATION IS IRREVERSIBLE. Take a full database backup (and check it restores)
before running it; the downgrade only explains that.

What it does
------------
First it **proves nothing is lost** (`run_gate`), then it drops:

* tables: `chapterprogress`, and - last - `subject`;
* `classroomsubject.subject_id`;
* `subjectteacher.classroom_id`, `subject_id` (the row names its section subject only);
* `chapter.class_id`, `subject_id`;
* `timetableperiod`, `homeworkassignment`, `classlog`, `attendancerecord` `.subject_id`;
* `exam_paper.class_id`, `subject_id`; `marks.exam_id`, `subject_id`;
* `paperdraft.class_id`, `subject_id`, `section_id`; `examsource.class_id`, `subject_id`;

together with their legacy unique keys and indexes, and it rebuilds the two partial
unique indexes that mentioned `subject_id` (attendance day-level row, subject-teacher
open row).

Hard rules (phase3.md, Section 4)
---------------------------------
* nothing is dropped unless the gate passes: every operational row already names its
  section subject / paper, every mark's exam equals its paper's exam, every teacher
  assignment's section equals its subject's section, no chapter lacks a status, no
  draft names a subject and a section without a section subject;
* row counts of the tables that matter are unchanged (`classroomsubject` above all);
* no `classroomsubject` row is created or changed.

The gate is plain functions of a connection so the tests run it on SQLite; the DDL uses
`DROP ... CASCADE` on PostgreSQL so a constraint or index that mentions a dropped column
goes with it.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5b6c7d8e9f0"
down_revision: str | Sequence[str] | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (table, columns to drop) - in the order they are dropped.
COLUMN_DROPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("subjectteacher", ("classroom_id", "subject_id")),
    ("chapter", ("class_id", "subject_id")),
    ("timetableperiod", ("subject_id",)),
    ("homeworkassignment", ("subject_id",)),
    ("classlog", ("subject_id",)),
    ("attendancerecord", ("subject_id",)),
    ("exam_paper", ("class_id", "subject_id")),
    ("marks", ("exam_id", "subject_id")),
    ("paperdraft", ("class_id", "subject_id", "section_id")),
    ("examsource", ("class_id", "subject_id")),
    ("classroomsubject", ("subject_id",)),
)

COUNTED = (
    "classroomsubject",
    "subjectteacher",
    "chapter",
    "exam_paper",
    "marks",
    "timetableperiod",
    "homeworkassignment",
    "attendancerecord",
    "classlog",
    "paperdraft",
    "examsource",
)


class MigrationAbort(RuntimeError):
    """The data is not in the shape M5 needs. Nothing was dropped."""


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _scalar(bind, sql: str) -> int:
    return int(bind.execute(sa.text(sql)).scalar_one())


def snapshot(bind) -> dict[str, int]:
    return {
        table: _scalar(bind, f"SELECT count(*) FROM {table}")
        for table in COUNTED
        if table in _tables(bind)
    }


def _problem(bind, label: str, sql: str, found: list[str]) -> None:
    count = _scalar(bind, sql)
    if count:
        found.append(f"{count} {label}")


def run_gate(bind) -> dict:
    """Everything that must be true before a column is dropped. Raises on any problem."""
    tables = _tables(bind)
    found: list[str] = []

    def has(table: str, *columns: str) -> bool:
        return table in tables and set(columns) <= _columns(bind, table)

    if has("subjectteacher", "classroom_subject_id"):
        _problem(
            bind,
            "subjectteacher row(s) with no section subject",
            "SELECT count(*) FROM subjectteacher WHERE classroom_subject_id IS NULL",
            found,
        )
    if has("subjectteacher", "classroom_subject_id", "classroom_id"):
        _problem(
            bind,
            "subjectteacher row(s) whose section differs from their subject's",
            "SELECT count(*) FROM subjectteacher AS st JOIN classroomsubject AS cs "
            "ON cs.id = st.classroom_subject_id WHERE st.classroom_id <> cs.classroom_id",
            found,
        )
    for table in ("timetableperiod", "homeworkassignment"):
        if has(table, "classroom_subject_id"):
            _problem(
                bind,
                f"{table} row(s) with no section subject",
                f"SELECT count(*) FROM {table} WHERE classroom_subject_id IS NULL",
                found,
            )
    for table in ("attendancerecord", "classlog"):
        if has(table, "classroom_subject_id", "subject_id"):
            _problem(
                bind,
                f"{table} row(s) that name a subject but no section subject",
                f"SELECT count(*) FROM {table} "
                "WHERE subject_id IS NOT NULL AND classroom_subject_id IS NULL",
                found,
            )
    if has("exam_paper", "classroom_subject_id"):
        _problem(
            bind,
            "exam_paper row(s) with no section subject",
            "SELECT count(*) FROM exam_paper WHERE classroom_subject_id IS NULL",
            found,
        )
    if has("marks", "exam_paper_id"):
        _problem(
            bind,
            "marks row(s) with no paper",
            "SELECT count(*) FROM marks WHERE exam_paper_id IS NULL",
            found,
        )
    if has("marks", "exam_paper_id", "exam_id") and "exam_paper" in tables:
        _problem(
            bind,
            "marks row(s) whose exam differs from their paper's exam",
            "SELECT count(*) FROM marks AS m JOIN exam_paper AS p ON p.id = m.exam_paper_id "
            "WHERE m.exam_id <> p.exam_id",
            found,
        )
    if has("chapter", "classroom_subject_id", "status"):
        _problem(
            bind,
            "chapter row(s) with no section subject or no status",
            "SELECT count(*) FROM chapter "
            "WHERE classroom_subject_id IS NULL OR status IS NULL",
            found,
        )
    if has("paperdraft", "classroom_subject_id", "subject_id", "section_id"):
        _problem(
            bind,
            "paperdraft row(s) that name a subject and a section but no section subject",
            "SELECT count(*) FROM paperdraft WHERE subject_id IS NOT NULL "
            "AND section_id IS NOT NULL AND classroom_subject_id IS NULL",
            found,
        )

    if found:
        raise MigrationAbort(
            "M5 will not drop anything yet - resolve these first:\n  "
            + "\n  ".join(found)
        )
    return {"counts": snapshot(bind)}


# ----------------------------------------------------------------------------- DDL


def _drop_columns(bind) -> None:
    postgres = bind.dialect.name == "postgresql"
    for table, columns in COLUMN_DROPS:
        present = _columns(bind, table)
        for column in columns:
            if column not in present:
                continue
            if postgres:
                op.execute(
                    f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}" CASCADE'
                )
            else:
                op.drop_column(table, column)


def _rebuild_partial_indexes(bind) -> None:
    """The two partial unique indexes that mentioned `subject_id`, without it."""
    if "attendancerecord" in _tables(bind):
        op.execute("DROP INDEX IF EXISTS uq_attendancerecord_school_student_date_day")
        op.execute(
            """
            CREATE UNIQUE INDEX uq_attendancerecord_school_student_date_day
                ON attendancerecord (school_id, student_id, date)
             WHERE classroom_subject_id IS NULL
            """
        )
    if "subjectteacher" in _tables(bind):
        op.execute("DROP INDEX IF EXISTS uq_subjectteacher_open_cs")
        op.execute(
            """
            CREATE UNIQUE INDEX uq_subjectteacher_open_cs
                ON subjectteacher (classroom_subject_id)
             WHERE effective_to IS NULL
            """
        )


def _tighten(bind) -> None:
    """`subjectteacher.classroom_subject_id` is the row's identity: it is required."""
    if bind.dialect.name == "postgresql" and "subjectteacher" in _tables(bind):
        op.alter_column(
            "subjectteacher",
            "classroom_subject_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )


def _drop_tables(bind) -> None:
    postgres = bind.dialect.name == "postgresql"
    for table in ("chapterprogress", "subject"):  # `subject` last, as the plan says
        if table not in _tables(bind):
            continue
        if postgres:
            op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        else:
            op.drop_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if "classroomsubject" not in _tables(bind):
        return
    before = run_gate(bind)["counts"]
    _drop_columns(bind)
    _rebuild_partial_indexes(bind)
    _tighten(bind)
    _drop_tables(bind)

    after = snapshot(bind)
    if after != before:
        # Counts cannot move from DDL alone; if they did, stop the transaction.
        raise MigrationAbort(f"M5 row counts moved: before={before} after={after}")
    print(f"[M5] dropped the school-wide subject; counts unchanged: {after}")


def downgrade() -> None:
    raise RuntimeError(
        "M5 dropped the school-wide `subject` table and every legacy subject/class column; "
        "it cannot be reversed. Restore the pre-M5 backup instead of downgrading."
    )
