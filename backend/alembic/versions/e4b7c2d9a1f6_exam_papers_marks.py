"""Exams: the date sheet (`exam_paper`), marks as decimals, audit and grades.

Why
---
`marks` was a `double precision` score with the maximum stored per exam in
`examsubject`. That made three things impossible: a mark worth 12.5 was stored as an
estimate, an absent child had to be given a 0 (a score they never earned), and changing
a published mark left no trace at all - a family could see one number and the school
could hold another.

What changes
------------
* `exam` gains the lifecycle the screens branch on: `scope` (`class` / `school`),
  `class_id`, `classroom_id`, `academic_year_id`, `exam_type`, `created_by_user_id`,
  `note`, `published_at`; the free-text `status` ("Scheduled") becomes
  `draft/scheduled/done/marks_entry/published`;
* `exam_paper` - one sitting: (exam, class, subject) with the date, the room and
  **`max_marks` / `passing_marks`** (numeric, not float);
* `exam_paper_chapter` - what a sitting covers (Phase 5's `chapter` rows);
* `marks` - `marks_obtained` becomes `numeric(6,2)` and nullable, `is_absent` states an
  absence, `exam_paper_id` ties the score to its paper, and `(exam_paper_id, student_id)`
  is unique. The old `(exam_id, student_id, subject_id)` key stays: both are filled from
  the same paper, so neither can disagree;
* `marks_audit` - every change after publication, with who and when;
* `grade_scale` - the school's own boundaries, one row per minimum percentage;
* **`examsubject` is dropped** (owner decision, 15 Nov 2026). Its row count is checked
  first and the migration **aborts printing the count** if it is not zero.

Downgrade
---------
Recreates `examsubject` **empty** with its original shape (the columns `f9e0f1a2b3c7`
created, plus its unique key and two indexes) and reverses the rest. Scores already
entered are kept: a downgrade returns the schema to "no per-paper maximum", not to
"no marks".

Revision ID: e4b7c2d9a1f6
Revises: d3f1a8c5e2b7
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b7c2d9a1f6"
down_revision: str | Sequence[str] | None = "d3f1a8c5e2b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The word each old free-text status becomes. Anything unknown is `draft`, because an
#: exam nobody can place is one that has not been scheduled.
STATUS_MAP = {
    "scheduled": "scheduled",
    "upcoming": "scheduled",
    "ongoing": "scheduled",
    "completed": "published",
    "complete": "published",
    "done": "done",
    "draft": "draft",
}

#: The reverse, for the downgrade - back to the label the old screen printed.
STATUS_BACK = {
    "draft": "Draft",
    "scheduled": "Scheduled",
    "done": "Completed",
    "marks_entry": "Ongoing",
    "published": "Completed",
}


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _count(sql: str) -> int:
    return int(op.get_bind().execute(sa.text(sql)).scalar_one())


def _add_column(table: str, definition: str) -> None:
    """Add a column unless it is already there (a re-run must not fail)."""
    name = definition.split()[0]
    if name not in _columns(table):
        op.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. `exam` - the lifecycle, the scope and who planned it
    # ------------------------------------------------------------------
    _add_column("exam", "scope varchar(16) NOT NULL DEFAULT 'class'")
    _add_column("exam", "class_id uuid REFERENCES classname(class_id)")
    _add_column("exam", "classroom_id uuid REFERENCES classroom(id)")
    _add_column("exam", "academic_year_id uuid REFERENCES academic_year(id)")
    _add_column("exam", "exam_type varchar(64)")
    _add_column("exam", "created_by_user_id uuid REFERENCES app_user(id)")
    _add_column("exam", "note text")
    _add_column("exam", "published_at timestamptz")

    # The old labels become the lifecycle. Printed before and after, so a reviewer can
    # see what the mapping did rather than trust it.
    shared = sa.text("SELECT status, count(*) FROM exam GROUP BY status")
    print(f"exam.status before: {dict(op.get_bind().execute(shared).all()) or '{}'}")
    for old, new in STATUS_MAP.items():
        op.execute(
            sa.text(
                "UPDATE exam SET status = :new WHERE lower(coalesce(status, '')) = :old"
            ).bindparams(new=new, old=old)
        )
    op.execute(
        "UPDATE exam SET status = 'draft' "
        "WHERE status IS NULL OR status NOT IN "
        "('draft', 'scheduled', 'done', 'marks_entry', 'published')"
    )
    print(f"exam.status after:  {dict(op.get_bind().execute(shared).all()) or '{}'}")

    op.execute("ALTER TABLE exam ALTER COLUMN status SET DEFAULT 'draft'")
    for name, column in (
        ("ix_exam_class_id", "class_id"),
        ("ix_exam_classroom_id", "classroom_id"),
    ):
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON exam ({column})")

    # ------------------------------------------------------------------
    # 2. The date sheet - one sitting per (exam, class, subject)
    # ------------------------------------------------------------------
    if not _has_table("exam_paper"):
        op.execute(
            "CREATE TABLE exam_paper ("
            "  id uuid NOT NULL,"
            "  school_id uuid,"
            "  exam_id uuid NOT NULL,"
            "  class_id uuid NOT NULL,"
            "  subject_id uuid NOT NULL,"
            "  exam_date date,"
            "  start_time time,"
            "  end_time time,"
            "  max_marks numeric(6,2) NOT NULL DEFAULT 100.00,"
            "  passing_marks numeric(6,2),"
            "  room varchar(64),"
            "  note text,"
            "  published_at timestamptz,"
            "  CONSTRAINT exam_paper_pkey PRIMARY KEY (id),"
            "  CONSTRAINT uq_exampaper_exam_class_subject"
            "    UNIQUE (exam_id, class_id, subject_id),"
            "  CONSTRAINT exam_paper_school_id_fkey"
            "    FOREIGN KEY (school_id) REFERENCES school (id),"
            "  CONSTRAINT exam_paper_exam_id_fkey"
            "    FOREIGN KEY (exam_id) REFERENCES exam (id),"
            "  CONSTRAINT exam_paper_class_id_fkey"
            "    FOREIGN KEY (class_id) REFERENCES classname (class_id),"
            "  CONSTRAINT exam_paper_subject_id_fkey"
            "    FOREIGN KEY (subject_id) REFERENCES subject (id)"
            ")"
        )
        for name, column in (
            ("ix_exam_paper_school_id", "school_id"),
            ("ix_exam_paper_exam_id", "exam_id"),
            ("ix_exam_paper_class_id", "class_id"),
            ("ix_exam_paper_subject_id", "subject_id"),
        ):
            op.execute(f"CREATE INDEX {name} ON exam_paper ({column})")

    if not _has_table("exam_paper_chapter"):
        op.execute(
            "CREATE TABLE exam_paper_chapter ("
            "  id uuid NOT NULL,"
            "  school_id uuid,"
            "  exam_paper_id uuid NOT NULL,"
            "  chapter_id uuid NOT NULL,"
            "  CONSTRAINT exam_paper_chapter_pkey PRIMARY KEY (id),"
            "  CONSTRAINT uq_exampaperchapter_paper_chapter"
            "    UNIQUE (exam_paper_id, chapter_id),"
            "  CONSTRAINT exam_paper_chapter_school_id_fkey"
            "    FOREIGN KEY (school_id) REFERENCES school (id),"
            "  CONSTRAINT exam_paper_chapter_exam_paper_id_fkey"
            "    FOREIGN KEY (exam_paper_id) REFERENCES exam_paper (id),"
            "  CONSTRAINT exam_paper_chapter_chapter_id_fkey"
            "    FOREIGN KEY (chapter_id) REFERENCES chapter (id)"
            ")"
        )
        for name, column in (
            ("ix_exam_paper_chapter_school_id", "school_id"),
            ("ix_exam_paper_chapter_exam_paper_id", "exam_paper_id"),
            ("ix_exam_paper_chapter_chapter_id", "chapter_id"),
        ):
            op.execute(f"CREATE INDEX {name} ON exam_paper_chapter ({column})")

    if not _has_table("grade_scale"):
        op.execute(
            "CREATE TABLE grade_scale ("
            "  id uuid NOT NULL,"
            "  school_id uuid,"
            "  min_percent numeric(5,2) NOT NULL,"
            "  grade varchar(8) NOT NULL,"
            "  label varchar(64),"
            "  CONSTRAINT grade_scale_pkey PRIMARY KEY (id),"
            "  CONSTRAINT uq_gradescale_school_min_percent UNIQUE (min_percent),"
            "  CONSTRAINT grade_scale_school_id_fkey"
            "    FOREIGN KEY (school_id) REFERENCES school (id)"
            ")"
        )
        op.execute("CREATE INDEX ix_grade_scale_school_id ON grade_scale (school_id)")

    if not _has_table("marks_audit"):
        op.execute(
            "CREATE TABLE marks_audit ("
            "  id uuid NOT NULL,"
            "  school_id uuid,"
            "  marks_id uuid NOT NULL,"
            "  old_value numeric(6,2),"
            "  new_value numeric(6,2),"
            "  old_absent boolean NOT NULL DEFAULT false,"
            "  new_absent boolean NOT NULL DEFAULT false,"
            "  changed_by_user_id uuid,"
            "  changed_at timestamptz NOT NULL DEFAULT now(),"
            "  reason text,"
            "  CONSTRAINT marks_audit_pkey PRIMARY KEY (id),"
            "  CONSTRAINT marks_audit_school_id_fkey"
            "    FOREIGN KEY (school_id) REFERENCES school (id),"
            "  CONSTRAINT marks_audit_marks_id_fkey"
            "    FOREIGN KEY (marks_id) REFERENCES marks (id),"
            "  CONSTRAINT marks_audit_changed_by_user_id_fkey"
            "    FOREIGN KEY (changed_by_user_id) REFERENCES app_user (id)"
            ")"
        )
        op.execute("CREATE INDEX ix_marks_audit_school_id ON marks_audit (school_id)")
        op.execute("CREATE INDEX ix_marks_audit_marks_id ON marks_audit (marks_id)")

    # ------------------------------------------------------------------
    # 3. `marks` - exact scores, an absence that is not a zero, and its paper
    # ------------------------------------------------------------------
    _add_column("marks", "exam_paper_id uuid REFERENCES exam_paper (id)")
    _add_column("marks", "is_absent boolean NOT NULL DEFAULT false")

    # Old rows: one paper per (exam, class, subject) their student actually sits in.
    # The maximum comes from `examsubject` while it still exists; 100 otherwise.
    if _has_table("examsubject"):
        op.execute(
            "INSERT INTO exam_paper (id, school_id, exam_id, class_id, subject_id,"
            " exam_date, max_marks)"
            " SELECT gen_random_uuid(), m.school_id, m.exam_id, c.class_id, m.subject_id,"
            " e.start_date, coalesce(es.max_marks, 100.00)::numeric(6,2)"
            " FROM marks m"
            " JOIN student s ON s.id = m.student_id"
            " JOIN classroom c ON c.id = s.classroom_id"
            " LEFT JOIN exam e ON e.id = m.exam_id"
            " LEFT JOIN examsubject es"
            "   ON es.exam_id = m.exam_id AND es.subject_id = m.subject_id"
            " WHERE m.exam_paper_id IS NULL AND c.class_id IS NOT NULL"
            " GROUP BY m.school_id, m.exam_id, c.class_id, m.subject_id, e.start_date,"
            " es.max_marks"
            " ON CONFLICT (exam_id, class_id, subject_id) DO NOTHING"
        )
    op.execute(
        "UPDATE marks AS m SET exam_paper_id = p.id"
        " FROM student s, classroom c, exam_paper p"
        " WHERE s.id = m.student_id AND c.id = s.classroom_id"
        "   AND p.exam_id = m.exam_id AND p.class_id = c.class_id"
        "   AND p.subject_id = m.subject_id AND m.exam_paper_id IS NULL"
    )

    op.execute(
        "ALTER TABLE marks ALTER COLUMN marks_obtained TYPE numeric(6,2)"
        " USING marks_obtained::numeric(6,2)"
    )
    op.execute("ALTER TABLE marks ALTER COLUMN marks_obtained DROP NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_marks_exam_paper_id ON marks (exam_paper_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_marks_paper_student"
        " ON marks (exam_paper_id, student_id)"
    )
    print(
        "marks rows linked to a paper: "
        f"{_count('SELECT count(*) FROM marks WHERE exam_paper_id IS NOT NULL')}"
        f" of {_count('SELECT count(*) FROM marks')}"
    )

    # ------------------------------------------------------------------
    # 4. `examsubject` goes - its row count decides, and a count stops the run
    # ------------------------------------------------------------------
    if _has_table("examsubject"):
        rows = _count("SELECT count(*) FROM examsubject")
        if rows != 0:
            raise RuntimeError(
                f"examsubject still holds {rows} row(s); `exam_paper.max_marks` is now "
                "the only per-subject maximum, so move them before this migration runs."
            )
        print(f"examsubject rows: {rows} - dropping the empty table")
        op.drop_table("examsubject")


def downgrade() -> None:
    # 4. `examsubject` comes back **empty** - a downgrade returns the schema, not data.
    if not _has_table("examsubject"):
        op.execute(
            "CREATE TABLE examsubject ("
            "  id uuid NOT NULL,"
            "  school_id uuid,"
            "  exam_id uuid NOT NULL,"
            "  subject_id uuid NOT NULL,"
            "  max_marks double precision NOT NULL,"
            "  CONSTRAINT examsubject_pkey PRIMARY KEY (id),"
            "  CONSTRAINT uq_examsubject_exam_subject UNIQUE (exam_id, subject_id),"
            "  CONSTRAINT examsubject_school_id_fkey"
            "    FOREIGN KEY (school_id) REFERENCES school (id),"
            "  CONSTRAINT examsubject_exam_id_fkey"
            "    FOREIGN KEY (exam_id) REFERENCES exam (id),"
            "  CONSTRAINT examsubject_subject_id_fkey"
            "    FOREIGN KEY (subject_id) REFERENCES subject (id)"
            ")"
        )
        op.execute("CREATE INDEX ix_examsubject_school_id ON examsubject (school_id)")
        op.execute("CREATE INDEX ix_examsubject_exam_id ON examsubject (exam_id)")

    # 3. marks back to a float score with no paper and no absence.
    op.execute("DROP INDEX IF EXISTS uq_marks_paper_student")
    op.execute("DROP INDEX IF EXISTS ix_marks_exam_paper_id")
    # A row with no score (an absence) becomes 0 - the old shape could not say else.
    op.execute("UPDATE marks SET marks_obtained = 0 WHERE marks_obtained IS NULL")
    op.execute(
        "ALTER TABLE marks ALTER COLUMN marks_obtained TYPE double precision"
        " USING marks_obtained::double precision"
    )
    op.execute("ALTER TABLE marks ALTER COLUMN marks_obtained SET NOT NULL")
    for column in ("exam_paper_id", "is_absent"):
        if column in _columns("marks"):
            op.execute(f"ALTER TABLE marks DROP COLUMN {column}")

    # 2. The new tables.
    for table in ("marks_audit", "exam_paper_chapter", "exam_paper", "grade_scale"):
        if _has_table(table):
            op.drop_table(table)

    # 1. exam back to a free-text status.
    for status, label in STATUS_BACK.items():
        op.execute(
            sa.text(
                "UPDATE exam SET status = :label WHERE lower(status) = :status"
            ).bindparams(label=label, status=status)
        )
    op.execute("ALTER TABLE exam ALTER COLUMN status SET DEFAULT 'Scheduled'")
    for column in (
        "published_at",
        "note",
        "created_by_user_id",
        "exam_type",
        "academic_year_id",
        "classroom_id",
        "class_id",
        "scope",
    ):
        if column in _columns("exam"):
            op.execute(f"ALTER TABLE exam DROP COLUMN {column}")




