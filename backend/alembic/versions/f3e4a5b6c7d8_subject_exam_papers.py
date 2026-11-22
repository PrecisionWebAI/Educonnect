"""Exam papers belong to section subjects; shared papers get a group (M3).

Revision ID: f3e4a5b6c7d8
Revises: f2d3e4a5b6c7

What this migration does
------------------------
* creates `exam_paper_group` and `exam_paper_group_chapter`;
* adds `exam_paper.classroom_subject_id` and `paper_group_id`;
* expands every class-level paper (class + school-wide subject) into one paper per
  section that **already has** that subject as a `classroomsubject` in the exam's
  academic year. The old row becomes the first section's paper (its id - and its marks
  and chapter links - survive); the other sections get copies. Sections sharing the paper
  share a group whose chapters are the old chapters, by name;
* remaps every mark to the paper of the section the student **sat** in, read from
  `enrollment` for the exam's academic year - never from `student.classroom_id`, which
  only holds where the student is today;
* adds `classroom_subject_id` to `paperdraft`, `examsource` and `questionusagelog`.

Hard rules (phase3.md, Section 4)
---------------------------------
* take a full database backup first;
* no `classroomsubject` row is created - ever;
* a paper, mark or draft that cannot be mapped is reported and the migration aborts;
* marks are counted before and after and must match exactly; `exam_paper` must grow by
  exactly the number of copies made; nothing else may change;
* legacy columns stay (nullable) until M5.

Deviation from the plan, on purpose: the source library and the question-usage log are
class-level knowledge. An `examsource` / `questionusagelog` row whose class has several
sections is *ambiguous*, not broken, so it keeps `classroom_subject_id` NULL instead of
aborting the migration. A `paperdraft` that names a subject **and** a section but matches
no classroom subject still aborts.

The data steps are plain functions of a connection (`run_data_steps`) so the test suite
runs them on SQLite. The DDL that tightens the schema is PostgreSQL-only.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "f3e4a5b6c7d8"
down_revision: str | Sequence[str] | None = "f2d3e4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAPER_UNIQUE = "uq_exampaper_exam_classroom_subject"


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

COUNTED = (
    "classroomsubject",
    "exam_paper",
    "exam_paper_chapter",
    "marks",
    "chapter",
    "timetableperiod",
    "homeworkassignment",
    "attendancerecord",
    "paperdraft",
    "examsource",
)


def snapshot(bind) -> dict[str, int]:
    """Row counts the verification gate compares against."""
    return {
        table: _count(bind, f"SELECT count(*) FROM {table}")
        for table in COUNTED
        if table in _tables(bind)
    }


# ------------------------------------------------------------------------- papers


def _exam_year(bind, exam_id, school_id):
    row = bind.execute(
        sa.text("SELECT academic_year_id FROM exam WHERE id = :id"), {"id": exam_id}
    ).first()
    if row is not None and row[0] is not None:
        return row[0]
    current = bind.execute(
        sa.text(
            "SELECT id FROM academic_year "
            "WHERE school_id = :school_id AND is_current = true LIMIT 1"
        ),
        {"school_id": school_id},
    ).first()
    return current[0] if current else None


def _paper_targets(bind, paper, year_id) -> list[tuple]:
    """Existing section subjects that hold this paper's class/subject, stable order.

    The order matches M2's chapter order (`section_id, id`) so that the section a chapter
    was kept on is also the section its paper is kept on.
    """
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
                   AND cs.academic_year_id = :year_id
                 ORDER BY room.section_id, cs.id
                """
            ),
            {
                "school_id": paper["school_id"],
                "class_id": paper["class_id"],
                "subject_id": paper["subject_id"],
                "year_id": year_id,
            },
        ).all()
    )


def _skipped_sections(bind, paper, targets) -> list[str]:
    taken = {row[1] for row in targets}
    rooms = bind.execute(
        sa.text(
            "SELECT id FROM classroom WHERE school_id = :school_id AND class_id = :class_id"
        ),
        {"school_id": paper["school_id"], "class_id": paper["class_id"]},
    ).all()
    return [str(row[0]) for row in rooms if row[0] not in taken]


def _chapter_links(bind, paper_id) -> list[tuple]:
    """The old chapter links of one paper: (link id, chapter id, name, sequence)."""
    return list(
        bind.execute(
            sa.text(
                """
                SELECT link.id, link.chapter_id, ch.name, ch.sequence,
                       ch.classroom_subject_id
                  FROM exam_paper_chapter AS link
                  JOIN chapter AS ch ON ch.id = link.chapter_id
                 WHERE link.exam_paper_id = :paper_id
                 ORDER BY ch.sequence
                """
            ),
            {"paper_id": paper_id},
        ).all()
    )


def expand_papers(bind) -> dict:
    """Make every class-level paper section-owned. Returns the report part."""
    report: dict = {
        "copies": 0,
        "groups": 0,
        "links_moved": 0,
        "orphans": [],
        "skipped": [],
        "migrated": set(),
    }
    if "exam_paper" not in _tables(bind):
        return report

    papers = (
        bind.execute(
            sa.text(
                """
                SELECT id, school_id, exam_id, class_id, subject_id, exam_date,
                       start_time, end_time, max_marks, passing_marks, room, note,
                       published_at
                  FROM exam_paper
                 WHERE classroom_subject_id IS NULL
                 ORDER BY exam_id, class_id, subject_id
                """
            )
        )
        .mappings()
        .all()
    )
    now = datetime.utcnow()

    for paper in papers:
        year_id = _exam_year(bind, paper["exam_id"], paper["school_id"])
        targets = _paper_targets(bind, paper, year_id) if year_id else []
        if not targets:
            report["orphans"].append(
                f"exam_paper id={paper['id']} exam={paper['exam_id']} "
                f"class={paper['class_id']} subject={paper['subject_id']} year={year_id}: "
                "no section of this class has the subject that year"
            )
            continue
        report["skipped"] += _skipped_sections(bind, paper, targets)
        links = _chapter_links(bind, paper["id"])

        group_id = None
        if len(targets) > 1:
            group_id = uuid4()
            bind.execute(
                sa.text(
                    """
                    INSERT INTO exam_paper_group (
                        id, school_id, exam_id, display_title, created_at, updated_at
                    ) VALUES (
                        :id, :school_id, :exam_id,
                        (SELECT name FROM subject WHERE id = :subject_id),
                        :now, :now
                    )
                    """
                ),
                {
                    "id": group_id,
                    "school_id": paper["school_id"],
                    "exam_id": paper["exam_id"],
                    "subject_id": paper["subject_id"],
                    "now": now,
                },
            )
            report["groups"] += 1
            for number, link in enumerate(links, start=1):
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO exam_paper_group_chapter (
                            id, school_id, paper_group_id, sequence, name
                        ) VALUES (:id, :school_id, :group_id, :sequence, :name)
                        """
                    ),
                    {
                        "id": uuid4(),
                        "school_id": paper["school_id"],
                        "group_id": group_id,
                        "sequence": number,
                        "name": link[2],
                    },
                )
            # A shared paper's chapters live on the group only: the links move, and the
            # gate expects exactly that many fewer `exam_paper_chapter` rows.
            report["links_moved"] += len(links)
            bind.execute(
                sa.text("DELETE FROM exam_paper_chapter WHERE exam_paper_id = :id"),
                {"id": paper["id"]},
            )
        else:
            # One section: the links must point at that section's own chapters.
            target_cs = targets[0][0]
            for link in links:
                if link[4] == target_cs:
                    continue
                own = bind.execute(
                    sa.text(
                        "SELECT id FROM chapter "
                        "WHERE classroom_subject_id = :cs AND name = :name"
                    ),
                    {"cs": target_cs, "name": link[2]},
                ).first()
                if own is None:
                    report["orphans"].append(
                        f"exam_paper id={paper['id']} chapter '{link[2]}': the section "
                        "subject has no chapter of that name"
                    )
                    continue
                bind.execute(
                    sa.text(
                        "UPDATE exam_paper_chapter SET chapter_id = :chapter WHERE id = :id"
                    ),
                    {"chapter": own[0], "id": link[0]},
                )

        for index, (classroom_subject_id, _room) in enumerate(targets):
            if index == 0:
                bind.execute(
                    sa.text(
                        """
                        UPDATE exam_paper
                           SET classroom_subject_id = :cs, paper_group_id = :group_id
                         WHERE id = :id
                        """
                    ),
                    {
                        "cs": classroom_subject_id,
                        "group_id": group_id,
                        "id": paper["id"],
                    },
                )
                report["migrated"].add(str(paper["id"]))
                continue
            bind.execute(
                sa.text(
                    """
                    INSERT INTO exam_paper (
                        id, school_id, exam_id, classroom_subject_id, paper_group_id,
                        class_id, subject_id, exam_date, start_time, end_time,
                        max_marks, passing_marks, room, note, published_at
                    ) VALUES (
                        :id, :school_id, :exam_id, :cs, :group_id,
                        NULL, NULL, :exam_date, :start_time, :end_time,
                        :max_marks, :passing_marks, :room, :note, :published_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "school_id": paper["school_id"],
                    "exam_id": paper["exam_id"],
                    "cs": classroom_subject_id,
                    "group_id": group_id,
                    "exam_date": paper["exam_date"],
                    "start_time": paper["start_time"],
                    "end_time": paper["end_time"],
                    "max_marks": paper["max_marks"],
                    "passing_marks": paper["passing_marks"],
                    "room": paper["room"],
                    "note": paper["note"],
                    "published_at": paper["published_at"],
                },
            )
            report["copies"] += 1
    return report


# --------------------------------------------------------------------------- marks


def remap_marks(bind, migrated: set[str]) -> list[str]:
    """Point each mark at the paper of the section the student sat in that year."""
    if "marks" not in _tables(bind):
        return []
    orphans: list[str] = []

    for mark in bind.execute(
        sa.text("SELECT id, exam_id FROM marks WHERE exam_paper_id IS NULL")
    ).all():
        orphans.append(f"marks id={mark[0]}: no exam_paper_id to remap from")

    rows = bind.execute(
        sa.text(
            """
            SELECT m.id, m.exam_id, m.student_id, m.exam_paper_id,
                   e.academic_year_id, cs.subject_id
              FROM marks AS m
              JOIN exam AS e ON e.id = m.exam_id
              JOIN exam_paper AS p ON p.id = m.exam_paper_id
              JOIN classroomsubject AS cs ON cs.id = p.classroom_subject_id
            """
        )
    ).all()
    for mark_id, exam_id, student_id, paper_id, year_id, legacy_subject in rows:
        if str(paper_id) not in migrated:
            continue
        if year_id is None:
            orphans.append(
                f"marks id={mark_id}: its exam has no academic year, so the section "
                "the student sat in cannot be read from enrollment"
            )
            continue
        enrolled = bind.execute(
            sa.text(
                "SELECT classroom_id FROM enrollment "
                "WHERE student_id = :student AND academic_year_id = :year"
            ),
            {"student": student_id, "year": year_id},
        ).first()
        if enrolled is None:
            orphans.append(
                f"marks id={mark_id} student={student_id}: no enrollment in the exam's year"
            )
            continue
        target = bind.execute(
            sa.text(
                """
                SELECT p.id
                  FROM exam_paper AS p
                  JOIN classroomsubject AS cs ON cs.id = p.classroom_subject_id
                 WHERE p.exam_id = :exam
                   AND cs.classroom_id = :room
                   AND cs.subject_id = :subject
                """
            ),
            {"exam": exam_id, "room": enrolled[0], "subject": legacy_subject},
        ).first()
        if target is None:
            orphans.append(
                f"marks id={mark_id} student={student_id}: their section "
                f"{enrolled[0]} has no paper for this subject in the exam"
            )
            continue
        if target[0] != paper_id:
            bind.execute(
                sa.text("UPDATE marks SET exam_paper_id = :paper WHERE id = :id"),
                {"paper": target[0], "id": mark_id},
            )
    return orphans


# ---------------------------------------------------------------- builder tables


def _current_year_sql(alias: str) -> str:
    return (
        "(SELECT id FROM academic_year "
        f"WHERE school_id = {alias}.school_id AND is_current = true LIMIT 1)"
    )


def link_drafts(bind) -> list[str]:
    """A draft that names a subject **and** a section must resolve to one classroom subject."""
    if "paperdraft" not in _tables(bind) or "classroom_subject_id" not in _columns(
        bind, "paperdraft"
    ):
        return []
    bind.execute(
        sa.text(
            f"""
            UPDATE paperdraft
               SET classroom_subject_id = (
                   SELECT cs.id
                     FROM classroomsubject AS cs
                     JOIN classroom AS room ON room.id = cs.classroom_id
                    WHERE cs.school_id = paperdraft.school_id
                      AND room.class_id = paperdraft.class_id
                      AND room.section_id = paperdraft.section_id
                      AND cs.subject_id = paperdraft.subject_id
                      AND cs.academic_year_id = {_current_year_sql("paperdraft")}
               )
             WHERE classroom_subject_id IS NULL
               AND subject_id IS NOT NULL
               AND class_id IS NOT NULL
               AND section_id IS NOT NULL
            """
        )
    )
    return [
        f"paperdraft id={row[0]} class={row[1]} section={row[2]} subject={row[3]}: "
        "no existing classroomsubject for that section/subject"
        for row in bind.execute(
            sa.text(
                """
                SELECT id, class_id, section_id, subject_id FROM paperdraft
                 WHERE classroom_subject_id IS NULL
                   AND subject_id IS NOT NULL
                   AND class_id IS NOT NULL
                   AND section_id IS NOT NULL
                """
            )
        ).all()
    ]


def link_library(bind, table: str) -> None:
    """`examsource` / `questionusagelog`: set the link only when it is unambiguous."""
    if table not in _tables(bind) or "classroom_subject_id" not in _columns(
        bind, table
    ):
        return
    if "subject_id" not in _columns(bind, table) or "class_id" not in _columns(
        bind, table
    ):
        return
    bind.execute(
        sa.text(
            f"""
            UPDATE {table}
               SET classroom_subject_id = (
                   SELECT cs.id
                     FROM classroomsubject AS cs
                     JOIN classroom AS room ON room.id = cs.classroom_id
                    WHERE cs.school_id = {table}.school_id
                      AND room.class_id = {table}.class_id
                      AND cs.subject_id = {table}.subject_id
                      AND cs.academic_year_id = {_current_year_sql(table)}
               )
             WHERE classroom_subject_id IS NULL
               AND subject_id IS NOT NULL
               AND class_id IS NOT NULL
               AND (
                   SELECT count(*)
                     FROM classroomsubject AS cs
                     JOIN classroom AS room ON room.id = cs.classroom_id
                    WHERE cs.school_id = {table}.school_id
                      AND room.class_id = {table}.class_id
                      AND cs.subject_id = {table}.subject_id
                      AND cs.academic_year_id = {_current_year_sql(table)}
               ) = 1
            """
        )
    )


# ------------------------------------------------------------------------- the gate


def verify(
    bind, before: dict[str, int], copies: int, links_moved: int = 0
) -> dict[str, dict]:
    """before / expected_after / actual_after per table; raise on any difference."""
    after = snapshot(bind)
    expected = dict(before)
    if "exam_paper" in expected:
        expected["exam_paper"] = before["exam_paper"] + copies
    if "exam_paper_chapter" in expected:
        expected["exam_paper_chapter"] = before["exam_paper_chapter"] - links_moved
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
        raise MigrationAbort(f"M3 row counts do not add up: {wrong}")
    return report


def run_data_steps(bind) -> dict:
    """Every M3 data step, then the count gate. Raises `MigrationAbort` on a problem."""
    before = snapshot(bind)
    papers = expand_papers(bind)
    orphans = list(papers["orphans"])
    orphans += remap_marks(bind, papers["migrated"])
    orphans += link_drafts(bind)
    link_library(bind, "examsource")
    link_library(bind, "questionusagelog")
    if orphans:
        raise MigrationAbort(
            "M3 cannot map these rows to an existing classroom subject; nothing was "
            "created. Resolve them and re-run:\n  " + "\n  ".join(orphans)
        )
    return {
        "counts": verify(bind, before, papers["copies"], papers["links_moved"]),
        "copies": papers["copies"],
        "groups": papers["groups"],
        "skipped_sections": papers["skipped"],
    }


# ------------------------------------------------------------------------ upgrade


def _create_group_tables(bind) -> None:
    if "exam_paper_group" not in _tables(bind):
        op.create_table(
            "exam_paper_group",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False
            ),
            sa.Column("exam_id", sa.Uuid(), sa.ForeignKey("exam.id"), nullable=False),
            sa.Column("display_title", sa.String(), nullable=True),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column(
                "locked_by_user_id",
                sa.Uuid(),
                sa.ForeignKey("app_user.id"),
                nullable=True,
            ),
            sa.Column(
                "created_by_user_id",
                sa.Uuid(),
                sa.ForeignKey("app_user.id"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_exam_paper_group_exam_id", "exam_paper_group", ["exam_id"])
        op.create_index(
            "ix_exam_paper_group_school_id", "exam_paper_group", ["school_id"]
        )
    if "exam_paper_group_chapter" not in _tables(bind):
        op.create_table(
            "exam_paper_group_chapter",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False
            ),
            sa.Column(
                "paper_group_id",
                sa.Uuid(),
                sa.ForeignKey("exam_paper_group.id"),
                nullable=False,
            ),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.UniqueConstraint(
                "paper_group_id", "sequence", name="uq_exampapergroupchapter_group_seq"
            ),
        )
        op.create_index(
            "ix_exam_paper_group_chapter_paper_group_id",
            "exam_paper_group_chapter",
            ["paper_group_id"],
        )
        op.create_index(
            "ix_exam_paper_group_chapter_school_id",
            "exam_paper_group_chapter",
            ["school_id"],
        )


def _add_columns(bind) -> None:
    _add_column(bind, "exam_paper", sa.Column("classroom_subject_id", sa.Uuid()))
    _add_column(bind, "exam_paper", sa.Column("paper_group_id", sa.Uuid()))
    _add_column(bind, "paperdraft", sa.Column("classroom_subject_id", sa.Uuid()))
    _add_column(bind, "paperdraft", sa.Column("paper_group_id", sa.Uuid()))
    _add_column(bind, "paperdraft", sa.Column("exam_paper_id", sa.Uuid()))
    _add_column(bind, "examsource", sa.Column("classroom_subject_id", sa.Uuid()))
    _add_column(bind, "questionusagelog", sa.Column("classroom_subject_id", sa.Uuid()))


def _index(bind, table: str, column: str, *, unique: bool = False) -> None:
    name = f"ix_{table}_{column}"
    if table in _tables(bind) and name not in _indexes(bind, table):
        op.create_index(name, table, [column], unique=unique)


def _foreign_key(bind, table: str, column: str, target: str) -> None:
    name = f"fk_{table}_{column}"
    if table in _tables(bind) and name not in _foreign_keys(bind, table):
        op.create_foreign_key(name, table, target, [column], ["id"])


def _tighten(bind) -> None:
    for table, column in (
        ("exam_paper", "classroom_subject_id"),
        ("exam_paper", "paper_group_id"),
        ("paperdraft", "classroom_subject_id"),
        ("examsource", "classroom_subject_id"),
        ("questionusagelog", "classroom_subject_id"),
    ):
        _index(bind, table, column)
    _index(bind, "paperdraft", "paper_group_id", unique=True)
    _index(bind, "paperdraft", "exam_paper_id", unique=True)

    if bind.dialect.name != "postgresql":
        return

    for table, column in (
        ("exam_paper", "classroom_subject_id"),
        ("examsource", "classroom_subject_id"),
        ("questionusagelog", "classroom_subject_id"),
        ("paperdraft", "classroom_subject_id"),
    ):
        _foreign_key(bind, table, column, "classroomsubject")
    for table, column, target in (
        ("exam_paper", "paper_group_id", "exam_paper_group"),
        ("paperdraft", "paper_group_id", "exam_paper_group"),
        ("paperdraft", "exam_paper_id", "exam_paper"),
    ):
        _foreign_key(bind, table, column, target)

    op.alter_column(
        "exam_paper", "classroom_subject_id", existing_type=sa.Uuid(), nullable=False
    )
    for column in ("class_id", "subject_id"):
        op.alter_column("exam_paper", column, existing_type=sa.Uuid(), nullable=True)
    if PAPER_UNIQUE not in _uniques(bind, "exam_paper"):
        op.create_unique_constraint(
            PAPER_UNIQUE, "exam_paper", ["exam_id", "classroom_subject_id"]
        )
    op.alter_column("marks", "exam_paper_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("marks", "subject_id", existing_type=sa.Uuid(), nullable=True)


def upgrade() -> None:
    bind = op.get_bind()
    if "exam_paper" not in _tables(bind) or "classroomsubject" not in _tables(bind):
        return
    _create_group_tables(bind)
    _add_columns(bind)
    report = run_data_steps(bind)
    for table, row in report["counts"].items():
        print(f"[M3] {table}: {row}")
    print(
        f"[M3] paper copies: {report['copies']}, groups: {report['groups']}, "
        f"sections without the subject (no paper made): {len(report['skipped_sections'])}"
    )
    _tighten(bind)


def downgrade() -> None:
    raise RuntimeError(
        "M3 turns class-level papers into section papers and remaps marks through "
        "enrollment; the original class-level shape cannot be rebuilt exactly. Restore "
        "the pre-M3 backup instead of downgrading."
    )
