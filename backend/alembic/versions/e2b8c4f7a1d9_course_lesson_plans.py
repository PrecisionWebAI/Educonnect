"""The Course schema: section subjects, teacher history, and the weekly lesson plan.

Why
---
`syllabusprogress` (the old two-counter "Course table") was already dropped in
`d3f1a8c5e2b7`; what remains is `chapter` (class-level plan) and `chapterprogress`
(section-level answer). The Course screen still could not answer three questions:

* **which subjects does this section run?** It inferred them from `subjectteacher`, so a
  subject with no teacher did not exist at all;
* **who taught it, and when?** The columns existed but the write path overwrote the open
  row, so history was lost the moment a teacher changed;
* **what did the teacher plan for this week?** There was no table.

What changes
------------
* `subject.is_active` - retired subjects leave the picker, rows and foreign keys stay.
  A case-insensitive unique index (`school_id`, `lower(name)`) is added after refusing to
  continue if two names differ only by case.
* `classroomsubject` - one row per (class-section, subject, session). Backfilled from
  `subjectteacher` and from `chapter` (every existing section of that class), so no
  subject a school already plans disappears from the screen.
* `subjectteacher.classroom_subject_id` - links the history row to its section subject;
  the legacy `(classroom_id, subject_id)` columns stay. Two partial unique indexes make
  "one open assignment" a database rule (one per `classroomsubject`, and one per legacy
  pair for rows the backfill could not place).
* `lessonplan` / `lessonplanhistory` - the latest version of a week and one immutable
  snapshot per submitted version.

Data safety
-----------
Nothing is dropped. The only destructive step is the downgrade, which drops the three new
tables and the new column/indexes - **lesson plan content is lost** on a downgrade, so take
a backup before running it on a school's database.

Revision ID: e2b8c4f7a1d9
Revises: b7d2e4f1a9c3
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "e2b8c4f7a1d9"
down_revision: str | Sequence[str] | None = "b7d2e4f1a9c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table)}


def _rows(statement: str) -> list:
    """Rows as mappings, so a caller reads `row["column"]` rather than a position."""
    return list(op.get_bind().execute(sa.text(statement)).mappings().all())


def _print_rows(title: str, rows: list[tuple]) -> None:
    print(f"[{title}] {len(rows)} row(s)")
    for row in rows[:20]:
        print(f"[{title}] {row}")


def _refuse_when_rows(title: str, rows: list[tuple], hint: str) -> None:
    """Stop, printing what was found - the migration changes nothing in that case."""
    _print_rows(title, rows)
    if rows:
        raise RuntimeError(
            f"[{title}] refusing to continue: {len(rows)} row(s) need a decision first. "
            f"{hint}"
        )


def _subject_flags() -> None:
    """`is_active` + the case-insensitive name key, without touching existing rows."""
    if "subject" not in _tables():
        return

    if "is_active" not in _columns("subject"):
        op.add_column(
            "subject",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
        op.alter_column("subject", "is_active", server_default=None)

    duplicates = _rows(
        "SELECT school_id, lower(name) AS name, count(*) AS rows "
        "FROM subject GROUP BY school_id, lower(name) HAVING count(*) > 1 "
        "ORDER BY school_id, name"
    )
    _refuse_when_rows(
        "subject duplicate names",
        duplicates,
        "Rename one of each pair (they differ only by case) and run the migration again.",
    )

    if "uq_subject_school_name_lower" not in _indexes("subject"):
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX uq_subject_school_name_lower "
                "ON subject (school_id, lower(name))"
            )
        )


def _create_classroom_subject() -> None:
    if "classroomsubject" in _tables():
        return

    op.create_table(
        "classroomsubject",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column(
            "classroom_id",
            sa.Uuid(),
            sa.ForeignKey("classroom.id"),
            nullable=False,
        ),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subject.id"), nullable=False),
        sa.Column(
            "academic_year_id",
            sa.Uuid(),
            sa.ForeignKey("academic_year.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="Active"),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column(
            "archived_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "classroom_id",
            "subject_id",
            "academic_year_id",
            name="uq_classroomsubject_section_subject_year",
        ),
        sa.CheckConstraint(
            "status IN ('Active', 'Archived')",
            name="ck_classroomsubject_status",
        ),
    )
    op.create_index("ix_classroomsubject_school_id", "classroomsubject", ["school_id"])
    op.create_index(
        "ix_classroomsubject_classroom_id", "classroomsubject", ["classroom_id"]
    )
    op.create_index(
        "ix_classroomsubject_subject_id", "classroomsubject", ["subject_id"]
    )
    op.create_index(
        "ix_classroomsubject_academic_year_id",
        "classroomsubject",
        ["academic_year_id"],
    )
    op.create_index(
        "ix_classroomsubject_created_by_user_id",
        "classroomsubject",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_classroomsubject_archived_by_user_id",
        "classroomsubject",
        ["archived_by_user_id"],
    )
    op.create_index(
        "ix_classroomsubject_school_classroom_status",
        "classroomsubject",
        ["school_id", "classroom_id", "status"],
    )


INSERT_SUBJECT = sa.text(
    "INSERT INTO classroomsubject "
    "(id, school_id, classroom_id, subject_id, academic_year_id, status, "
    " created_at, updated_at) "
    "VALUES (:id, :school_id, :classroom_id, :subject_id, :academic_year_id, "
    " 'Active', :now, :now) "
    "ON CONFLICT (classroom_id, subject_id, academic_year_id) DO NOTHING"
)


def _add_section_subject(row) -> bool:
    """Insert one row; returns False when the session year could not be resolved."""
    year_id = row["academic_year_id"]
    if year_id is None:
        return False
    op.get_bind().execute(
        INSERT_SUBJECT,
        {
            "id": uuid4(),
            "school_id": row["school_id"],
            "classroom_id": row["classroom_id"],
            "subject_id": row["subject_id"],
            "academic_year_id": year_id,
            "now": datetime.now(UTC).replace(tzinfo=None),
        },
    )
    return True


def _backfill_classroom_subject() -> None:
    """Every subject the school already teaches or plans becomes a section row."""
    tables = _tables()
    if "classroomsubject" not in tables:
        return

    inserted = 0
    skipped = 0

    if "subjectteacher" in tables:
        assignments = _rows(
            "SELECT st.school_id, st.classroom_id, st.subject_id, "
            "       COALESCE(st.academic_year_id, ("
            "           SELECT a.id FROM academic_year a "
            "           WHERE a.school_id = st.school_id "
            "           ORDER BY a.is_current DESC, a.start_date ASC LIMIT 1"
            "       )) AS academic_year_id "
            "FROM (SELECT DISTINCT school_id, classroom_id, subject_id, "
            "             academic_year_id FROM subjectteacher) st"
        )
        for row in assignments:
            if _add_section_subject(row):
                inserted += 1
            else:
                skipped += 1

    if "chapter" in tables and "classroom" in tables:
        plans = _rows(
            "SELECT c.school_id, room.id AS classroom_id, c.subject_id, "
            "       c.academic_year_id "
            "FROM chapter c "
            "JOIN classroom room "
            "  ON room.class_id = c.class_id AND room.school_id = c.school_id"
        )
        for row in plans:
            if _add_section_subject(row):
                inserted += 1
            else:
                skipped += 1

    total = int(
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM classroomsubject"))
        .scalar_one()
    )
    print(
        f"[classroomsubject] {total} row(s) after backfill "
        f"({inserted} inserted, {skipped} skipped: no session year)"
    )


def _link_subject_teacher() -> None:
    """Add the link, place every existing row, then make "one open row" a DB rule."""
    if "subjectteacher" not in _tables():
        return

    if "classroom_subject_id" not in _columns("subjectteacher"):
        op.add_column(
            "subjectteacher",
            sa.Column("classroom_subject_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_subjectteacher_classroom_subject_id",
            "subjectteacher",
            "classroomsubject",
            ["classroom_subject_id"],
            ["id"],
        )
        op.create_index(
            "ix_subjectteacher_classroom_subject_id",
            "subjectteacher",
            ["classroom_subject_id"],
        )

    # The best row for a legacy assignment: its own session when it names one, else the
    # oldest section-subject row. `NULLS LAST` keeps the boolean ordering readable.
    op.execute(
        sa.text(
            "UPDATE subjectteacher AS st "
            "SET classroom_subject_id = ("
            "  SELECT cs.id FROM classroomsubject cs "
            "  WHERE cs.classroom_id = st.classroom_id "
            "    AND cs.subject_id = st.subject_id "
            "  ORDER BY (cs.academic_year_id = st.academic_year_id) DESC NULLS LAST, "
            "           cs.created_at ASC "
            "  LIMIT 1"
            ") "
            "WHERE st.classroom_subject_id IS NULL"
        )
    )

    duplicated = _rows(
        "SELECT classroom_subject_id, count(*) FROM subjectteacher "
        "WHERE effective_to IS NULL AND classroom_subject_id IS NOT NULL "
        "GROUP BY classroom_subject_id HAVING count(*) > 1"
    )
    _refuse_when_rows(
        "subjectteacher open rows",
        duplicated,
        "Close all but one open row per classroom_subject_id (set effective_to) first.",
    )

    legacy_duplicated = _rows(
        "SELECT classroom_id, subject_id, count(*) FROM subjectteacher "
        "WHERE effective_to IS NULL AND classroom_subject_id IS NULL "
        "GROUP BY classroom_id, subject_id HAVING count(*) > 1"
    )
    _refuse_when_rows(
        "subjectteacher legacy open rows",
        legacy_duplicated,
        "Close all but one open row per (classroom_id, subject_id) first.",
    )

    if "uq_subjectteacher_open_cs" not in _indexes("subjectteacher"):
        op.create_index(
            "uq_subjectteacher_open_cs",
            "subjectteacher",
            ["classroom_subject_id"],
            unique=True,
            postgresql_where=sa.text(
                "effective_to IS NULL AND classroom_subject_id IS NOT NULL"
            ),
        )
    if "uq_subjectteacher_open_legacy" not in _indexes("subjectteacher"):
        op.create_index(
            "uq_subjectteacher_open_legacy",
            "subjectteacher",
            ["classroom_id", "subject_id"],
            unique=True,
            postgresql_where=sa.text(
                "effective_to IS NULL AND classroom_subject_id IS NULL"
            ),
        )


def _create_lesson_plan() -> None:
    if "lessonplan" in _tables():
        return

    op.create_table(
        "lessonplan",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column(
            "classroom_subject_id",
            sa.Uuid(),
            sa.ForeignKey("classroomsubject.id"),
            nullable=False,
        ),
        sa.Column(
            "academic_year_id",
            sa.Uuid(),
            sa.ForeignKey("academic_year.id"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("week_no", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("topics", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "learning_objectives", sa.String(), nullable=False, server_default=""
        ),
        sa.Column("activities", sa.String(), nullable=False, server_default=""),
        sa.Column("homework", sa.String(), nullable=False, server_default=""),
        sa.Column("resources", sa.String(), nullable=False, server_default=""),
        sa.Column("assessment", sa.String(), nullable=False, server_default=""),
        sa.Column("format_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="Submitted"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_version", sa.Integer(), nullable=True),
        sa.Column(
            "submitted_by_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "classroom_subject_id",
            "academic_year_id",
            "year",
            "month",
            "week_no",
            name="uq_lessonplan_subject_year_month_week",
        ),
        sa.CheckConstraint(
            "status IN ('Submitted', 'Approved', 'Rejected')",
            name="ck_lessonplan_status",
        ),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_lessonplan_month"),
        sa.CheckConstraint("week_no >= 1 AND week_no <= 5", name="ck_lessonplan_week"),
        sa.CheckConstraint("end_date >= start_date", name="ck_lessonplan_dates"),
        sa.CheckConstraint("version >= 1", name="ck_lessonplan_version"),
    )
    for name, columns in (
        ("ix_lessonplan_school_id", ["school_id"]),
        ("ix_lessonplan_classroom_subject_id", ["classroom_subject_id"]),
        ("ix_lessonplan_academic_year_id", ["academic_year_id"]),
        ("ix_lessonplan_submitted_by_employee_id", ["submitted_by_employee_id"]),
        ("ix_lessonplan_school_status", ["school_id", "status"]),
        (
            "ix_lessonplan_subject_year_month",
            ["classroom_subject_id", "year", "month"],
        ),
        (
            "ix_lessonplan_school_submitter",
            ["school_id", "submitted_by_employee_id"],
        ),
    ):
        op.create_index(name, "lessonplan", columns)


def _create_lesson_plan_history() -> None:
    if "lessonplanhistory" in _tables():
        return

    op.create_table(
        "lessonplanhistory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column(
            "lesson_plan_id",
            sa.Uuid(),
            sa.ForeignKey("lessonplan.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("topics", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "learning_objectives", sa.String(), nullable=False, server_default=""
        ),
        sa.Column("activities", sa.String(), nullable=False, server_default=""),
        sa.Column("homework", sa.String(), nullable=False, server_default=""),
        sa.Column("resources", sa.String(), nullable=False, server_default=""),
        sa.Column("assessment", sa.String(), nullable=False, server_default=""),
        sa.Column("format_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "submitted_by_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "approved_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column(
            "rejected_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lesson_plan_id",
            "version",
            name="uq_lessonplanhistory_plan_version",
        ),
    )
    op.create_index(
        "ix_lessonplanhistory_school_id", "lessonplanhistory", ["school_id"]
    )
    op.create_index(
        "ix_lessonplanhistory_lesson_plan_id",
        "lessonplanhistory",
        ["lesson_plan_id"],
    )
    op.create_index(
        "ix_lessonplanhistory_submitted_by_employee_id",
        "lessonplanhistory",
        ["submitted_by_employee_id"],
    )
    op.create_index(
        "ix_lessonplanhistory_school_plan",
        "lessonplanhistory",
        ["school_id", "lesson_plan_id"],
    )


def _drop_index(table: str, name: str) -> None:
    if name in _indexes(table):
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    _subject_flags()
    _create_classroom_subject()
    _backfill_classroom_subject()
    _link_subject_teacher()
    _create_lesson_plan()
    _create_lesson_plan_history()
    print("[course] lesson-plan schema ready.")


def downgrade() -> None:
    """Reverse the schema - **lesson plan content is dropped**.

    The plan tables hold what teachers typed, and there is no older table to move it
    into. A downgrade is a schema rollback, not a data migration: take a backup first.
    """
    if "lessonplanhistory" in _tables():
        for name in (
            "ix_lessonplanhistory_school_plan",
            "ix_lessonplanhistory_submitted_by_employee_id",
            "ix_lessonplanhistory_lesson_plan_id",
            "ix_lessonplanhistory_school_id",
        ):
            _drop_index("lessonplanhistory", name)
        op.drop_table("lessonplanhistory")

    if "lessonplan" in _tables():
        for name in (
            "ix_lessonplan_school_submitter",
            "ix_lessonplan_subject_year_month",
            "ix_lessonplan_school_status",
            "ix_lessonplan_submitted_by_employee_id",
            "ix_lessonplan_academic_year_id",
            "ix_lessonplan_classroom_subject_id",
            "ix_lessonplan_school_id",
        ):
            _drop_index("lessonplan", name)
        op.drop_table("lessonplan")

    if "subjectteacher" in _tables():
        _drop_index("subjectteacher", "uq_subjectteacher_open_legacy")
        _drop_index("subjectteacher", "uq_subjectteacher_open_cs")
        _drop_index("subjectteacher", "ix_subjectteacher_classroom_subject_id")
        if op.get_bind().dialect.name == "postgresql":
            # The name is read rather than assumed: a database built by `create_all`
            # names this key `<table>_<column>_fkey`, while this migration names it.
            for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(
                "subjectteacher"
            ):
                if foreign_key.get("constrained_columns") == [
                    "classroom_subject_id"
                ] and foreign_key.get("name"):
                    op.drop_constraint(
                        foreign_key["name"], "subjectteacher", type_="foreignkey"
                    )
        if "classroom_subject_id" in _columns("subjectteacher"):
            op.drop_column("subjectteacher", "classroom_subject_id")

    if "classroomsubject" in _tables():
        for name in (
            "ix_classroomsubject_school_classroom_status",
            "ix_classroomsubject_archived_by_user_id",
            "ix_classroomsubject_created_by_user_id",
            "ix_classroomsubject_academic_year_id",
            "ix_classroomsubject_subject_id",
            "ix_classroomsubject_classroom_id",
            "ix_classroomsubject_school_id",
        ):
            _drop_index("classroomsubject", name)
        op.drop_table("classroomsubject")

    if "subject" in _tables():
        _drop_index("subject", "uq_subject_school_name_lower")
        if "is_active" in _columns("subject"):
            op.drop_column("subject", "is_active")

    print("[course] lesson-plan schema removed (plan content was dropped).")
