"""Teachers' subjects become plain text; hiring stops pointing at a subject (M4).

Revision ID: f4a5b6c7d8e9
Revises: f3e4a5b6c7d8

What this migration does
------------------------
* adds `employee.subject_tags` and fills it from `teachersubject` + `subject.name`
  (alphabetical, comma-separated). A teacher's list that would not fit in 500
  characters aborts the migration - nothing is cut;
* fills `pipeline_hiring_table.subject_name` from the old subject where it is empty;
* seeds each school's `school_setting hiring.subject_suggestions` (a JSON list) from the
  distinct subject names it had - only a convenience for the interview form, linked to
  nothing;
* drops `pipeline_hiring_table.subject_id` and the `teachersubject` table.

Hard rules (phase3.md, Section 4)
---------------------------------
* take a full database backup first;
* no `classroomsubject` row is created or changed;
* every `teachersubject` row must be represented in its teacher's `subject_tags`, the
  hiring row count must not move, and `classroomsubject` must be exactly as it was -
  otherwise the migration aborts before dropping anything.

The data steps are plain functions of a connection so the tests run them on SQLite. The
downgrade refuses: the list was a set of subject *rows*, the new column is free text, and
a faithful reverse needs the backup.
"""

import json
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | Sequence[str] | None = "f3e4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUGGESTIONS_KEY = "hiring.subject_suggestions"
MAX_TAGS = 500


class MigrationAbort(RuntimeError):
    """A count did not add up or a list would not fit. Nothing is dropped."""


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    if table not in _tables(bind):
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _count(bind, sql: str) -> int:
    return int(bind.execute(sa.text(sql)).scalar_one())


def snapshot(bind) -> dict[str, int]:
    """The counts that must not move."""
    counts = {}
    for table in ("classroomsubject", "pipeline_hiring_table", "employee"):
        if table in _tables(bind):
            counts[table] = _count(bind, f"SELECT count(*) FROM {table}")
    return counts


def backfill_tags(bind) -> dict:
    """`employee.subject_tags` from `teachersubject`. Returns what it did."""
    report = {"teachers": 0, "too_long": []}
    if "teachersubject" not in _tables(bind) or "subject" not in _tables(bind):
        return report
    rows = bind.execute(
        sa.text(
            """
            SELECT ts.teacher_id, s.name
              FROM teachersubject AS ts
              JOIN subject AS s ON s.id = ts.subject_id
             ORDER BY ts.teacher_id, lower(s.name)
            """
        )
    ).all()
    names: dict = {}
    for teacher_id, name in rows:
        clean = " ".join((name or "").split())
        if clean and clean.lower() not in {
            item.lower() for item in names.setdefault(teacher_id, [])
        }:
            names[teacher_id].append(clean)
    for teacher_id, listed in names.items():
        line = ", ".join(listed)
        if len(line) > MAX_TAGS:
            report["too_long"].append(f"employee {teacher_id}: {len(line)} characters")
            continue
        bind.execute(
            sa.text(
                "UPDATE employee SET subject_tags = :line "
                "WHERE id = :id AND (subject_tags IS NULL OR subject_tags = '')"
            ),
            {"line": line, "id": teacher_id},
        )
        report["teachers"] += 1
    return report


def backfill_hiring(bind) -> None:
    """`subject_name` from the old subject where the snapshot is empty."""
    if "pipeline_hiring_table" not in _tables(bind):
        return
    columns = _columns(bind, "pipeline_hiring_table")
    if "subject_id" not in columns or "subject_name" not in columns:
        return
    bind.execute(
        sa.text(
            """
            UPDATE pipeline_hiring_table
               SET subject_name = (
                   SELECT name FROM subject WHERE subject.id = pipeline_hiring_table.subject_id
               )
             WHERE subject_id IS NOT NULL
               AND (subject_name IS NULL OR subject_name = '')
            """
        )
    )


def seed_suggestions(bind) -> int:
    """One `hiring.subject_suggestions` per school that has subjects and no row yet."""
    if "subject" not in _tables(bind) or "school_setting" not in _tables(bind):
        return 0
    seeded = 0
    schools = bind.execute(
        sa.text("SELECT DISTINCT school_id FROM subject WHERE school_id IS NOT NULL")
    ).all()
    for (school_id,) in schools:
        exists = bind.execute(
            sa.text("SELECT 1 FROM school_setting WHERE school_id = :s AND key = :k"),
            {"s": school_id, "k": SUGGESTIONS_KEY},
        ).first()
        if exists:
            continue
        names = [
            " ".join(row[0].split())
            for row in bind.execute(
                sa.text(
                    "SELECT DISTINCT name FROM subject WHERE school_id = :s ORDER BY name"
                ),
                {"s": school_id},
            ).all()
            if row[0] and row[0].strip()
        ]
        bind.execute(
            sa.text(
                "INSERT INTO school_setting (id, school_id, key, value, updated_at) "
                "VALUES (:id, :s, :k, :v, :now)"
            ),
            {
                "id": uuid4(),
                "s": school_id,
                "k": SUGGESTIONS_KEY,
                "v": json.dumps(names),
                "now": datetime.utcnow(),
            },
        )
        seeded += 1
    return seeded


def verify(bind, before: dict[str, int]) -> dict:
    """Every teacher subject is in the text, and nothing else moved."""
    after = snapshot(bind)
    moved = {
        table: {"before": before[table], "after": after.get(table, 0)}
        for table in before
        if after.get(table, 0) != before[table]
    }
    if moved:
        raise MigrationAbort(f"M4 row counts moved: {moved}")

    missing: list[str] = []
    if "teachersubject" in _tables(bind) and "subject" in _tables(bind):
        for teacher_id, name, tags in bind.execute(
            sa.text(
                """
                SELECT ts.teacher_id, s.name, e.subject_tags
                  FROM teachersubject AS ts
                  JOIN subject AS s ON s.id = ts.subject_id
                  JOIN employee AS e ON e.id = ts.teacher_id
                """
            )
        ).all():
            listed = {
                " ".join(part.split()).lower()
                for part in (tags or "").split(",")
                if part.strip()
            }
            if " ".join((name or "").split()).lower() not in listed:
                missing.append(f"employee {teacher_id}: '{name}'")
    if missing:
        raise MigrationAbort(
            "These teacher subjects did not reach subject_tags; nothing was dropped:\n  "
            + "\n  ".join(missing)
        )
    return {"counts": after}


def run_data_steps(bind) -> dict:
    before = snapshot(bind)
    tags = backfill_tags(bind)
    if tags["too_long"]:
        raise MigrationAbort(
            f"A teacher's subjects would not fit in {MAX_TAGS} characters; shorten the "
            "list and re-run:\n  " + "\n  ".join(tags["too_long"])
        )
    backfill_hiring(bind)
    seeded = seed_suggestions(bind)
    report = verify(bind, before)
    report.update(tags=tags["teachers"], suggestions=seeded)
    return report


def upgrade() -> None:
    bind = op.get_bind()
    if "employee" not in _tables(bind):
        return
    if "subject_tags" not in _columns(bind, "employee"):
        op.add_column(
            "employee", sa.Column("subject_tags", sa.String(500), nullable=True)
        )
    report = run_data_steps(bind)
    print(
        f"[M4] teachers tagged: {report['tags']}, suggestion lists seeded: "
        f"{report['suggestions']}, counts: {report['counts']}"
    )
    if "pipeline_hiring_table" in _tables(bind) and "subject_id" in _columns(
        bind, "pipeline_hiring_table"
    ):
        if bind.dialect.name == "postgresql":
            op.execute(
                "ALTER TABLE pipeline_hiring_table DROP COLUMN IF EXISTS subject_id CASCADE"
            )
        else:
            op.drop_column("pipeline_hiring_table", "subject_id")
    if "teachersubject" in _tables(bind):
        op.drop_table("teachersubject")


def downgrade() -> None:
    raise RuntimeError(
        "M4 turned teachers' subject rows into free text and dropped `teachersubject`; the "
        "rows cannot be rebuilt exactly. Restore the pre-M4 backup instead of downgrading."
    )
