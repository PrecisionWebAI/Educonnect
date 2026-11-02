"""The classroom is the hub: child tables stop copying `classroom_id`.

Revision ID: f9e0f1a2b3c7
Revises: f9e0f1a2b3c6
Create Date: 2026-11-02

Why:
  Four tables each stored a `classroom_id` beside a `section_id`, and every one of
  them could disagree with the other: a student could sit in section 10-A while
  their `classroom_id` said Class 9, and the app would show them in both. A section
  already names its class (`section.classroom_id`), so the copy was never the source
  of truth - it was a cache nobody invalidated.

  The copies go. `studentprofile`, `attendancerecord`, `homeworkassignment` and
  `timetableperiod` are left with the section alone, and the class is read through
  it. `homeworkassignment.section_id` and `timetableperiod.section_id` become
  required: now that the class is only reachable through the section, a row with no
  section has no class at all, and the migration **refuses to run** if one exists
  rather than invent a placement for it.

  Two more copies went the same way:

  * `marks.max_marks` repeated the same number on every student's row for a subject,
    so one bad row could score a paper out of something else. It moves to a new
    `examsubject` table - `UNIQUE(exam_id, subject_id)` - which states once what each
    subject is out of.
  * `classdiary` was one row per student per day, so a class-wide note was written
    out again for every child. It splits into `classlog` (`UNIQUE(section_id, date)`
    - the day's entry for the class) and `diaryremark` (a note about one student on
    that entry).

Downgrade puts all of it back, including the copied columns, filled from the section.
Two limits worth knowing: a `classlog` with no remarks cannot become a `classdiary`
row (that table required a student), so such a log is dropped on the way down; and
the restored columns come back at the end of their tables, not in their old
positions, because `ALTER TABLE` can only append.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3c7"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The copies of the class that the section already knows.
DUPLICATE_CLASS_COLUMNS: tuple[str, ...] = (
    "studentprofile",
    "attendancerecord",
    "homeworkassignment",
    "timetableperiod",
)

#: Tables whose `section_id` becomes required, because a row without a section has
#: no class once the copy is gone.
SECTION_REQUIRED: tuple[str, ...] = ("homeworkassignment", "timetableperiod")


def _assert_sections_present(bind, table: str) -> None:
    """Fail loudly rather than invent a class for a row that names no section.

    Run before `section_id` is made NOT NULL: a row with no section cannot be
    placed in a class any more, and silently deleting it would be worse than
    stopping and letting a human decide.
    """
    orphans = bind.execute(
        sa.text(f"SELECT count(*) FROM {table} WHERE section_id IS NULL")
    ).scalar()
    if orphans:
        raise RuntimeError(
            f"{table}.section_id: {orphans} row(s) have no section, so they have no "
            f"class - refusing to continue."
        )


def _assert_rows_resolve(bind, table: str, column: str, parent: str) -> None:
    """A column that is about to become the only route to the class must resolve.

    `classroom_id` is dropped from four tables, leaving the section as the only way
    to reach the class. So before anything goes, every `section_id` in those tables
    must point at a section that is actually there.
    """
    broken = bind.execute(
        sa.text(
            f"SELECT count(*) FROM {table} c WHERE c.{column} IS NOT NULL AND "
            f"NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.id = c.{column})"
        )
    ).scalar()
    if broken:
        raise RuntimeError(
            f"{table}.{column}: {broken} row(s) do not resolve in {parent} - "
            f"refusing to continue."
        )


def upgrade() -> None:
    """Drop the copied columns, split `classdiary`, move `max_marks` onto the exam."""
    bind = op.get_bind()

    # 1. Nothing may be left unplaceable. The section has to exist (it becomes the
    #    only route to the class), and the tables whose `section_id` becomes required
    #    must not have a row without one.
    for table in DUPLICATE_CLASS_COLUMNS:
        _assert_rows_resolve(bind, table, "section_id", "section")
    for table in SECTION_REQUIRED:
        _assert_sections_present(bind, table)

    # 2. `examsubject` - what each subject is out of, stated once per exam.
    op.execute(
        "CREATE TABLE examsubject ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  exam_id uuid NOT NULL,"
        "  subject_id uuid NOT NULL,"
        "  max_marks double precision NOT NULL,"
        "  CONSTRAINT examsubject_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_examsubject_exam_subject UNIQUE (exam_id, subject_id),"
        "  CONSTRAINT examsubject_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT examsubject_exam_id_fkey FOREIGN KEY (exam_id)"
        "    REFERENCES exam (id),"
        "  CONSTRAINT examsubject_subject_id_fkey FOREIGN KEY (subject_id)"
        "    REFERENCES subject (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_examsubject_school_id ON examsubject (school_id)")
    op.execute("CREATE INDEX ix_examsubject_exam_id ON examsubject (exam_id)")

    #    The rows already in `marks` say what each (exam, subject) was out of. Where
    #    they disagree the highest wins - that is the one the paper was set to.
    op.execute(
        "INSERT INTO examsubject (id, school_id, exam_id, subject_id, max_marks) "
        "SELECT gen_random_uuid(), m.school_id, m.exam_id, m.subject_id, "
        "       max(m.max_marks) "
        "FROM marks m GROUP BY m.school_id, m.exam_id, m.subject_id"
    )
    op.execute("ALTER TABLE marks DROP COLUMN max_marks")

    # 3. `classdiary` splits: the class's day becomes a `classlog`, and each
    #    student's note becomes a `diaryremark` filed under it.
    op.execute(
        "CREATE TABLE classlog ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  section_id uuid NOT NULL,"
        "  teacher_id uuid NOT NULL,"
        "  date date NOT NULL,"
        "  note character varying NOT NULL,"
        "  CONSTRAINT classlog_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_classlog_section_date UNIQUE (section_id, date),"
        "  CONSTRAINT classlog_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT classlog_section_id_fkey FOREIGN KEY (section_id)"
        "    REFERENCES section (id),"
        "  CONSTRAINT classlog_teacher_id_fkey FOREIGN KEY (teacher_id)"
        "    REFERENCES employee (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_classlog_school_id ON classlog (school_id)")
    op.execute("CREATE INDEX ix_classlog_section_id ON classlog (section_id)")

    op.execute(
        "CREATE TABLE diaryremark ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  class_log_id uuid NOT NULL,"
        "  student_id uuid NOT NULL,"
        "  remark character varying NOT NULL,"
        "  CONSTRAINT diaryremark_pkey PRIMARY KEY (id),"
        "  CONSTRAINT diaryremark_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT diaryremark_class_log_id_fkey FOREIGN KEY (class_log_id)"
        "    REFERENCES classlog (id),"
        "  CONSTRAINT diaryremark_student_id_fkey FOREIGN KEY (student_id)"
        "    REFERENCES studentprofile (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_diaryremark_school_id ON diaryremark (school_id)")
    op.execute(
        "CREATE INDEX ix_diaryremark_class_log_id ON diaryremark (class_log_id)"
    )

    #    A diary row has to name a section - without one there is no day to file it
    #    under, so stop rather than drop it.
    unplaced = bind.execute(
        sa.text("SELECT count(*) FROM classdiary WHERE section_id IS NULL")
    ).scalar()
    if unplaced:
        raise RuntimeError(
            f"classdiary.section_id: {unplaced} row(s) name no section, so they have "
            f"no class log to belong to - refusing to continue."
        )

    #    One log per section per day, carrying that day's note; then every diary row
    #    becomes a remark about its own student on that log.
    op.execute(
        "INSERT INTO classlog (id, school_id, section_id, teacher_id, date, note) "
        "SELECT DISTINCT ON (d.section_id, d.date) "
        "       gen_random_uuid(), d.school_id, d.section_id, d.teacher_id, d.date, "
        "       d.note "
        "FROM classdiary d ORDER BY d.section_id, d.date, d.id"
    )
    op.execute(
        "INSERT INTO diaryremark (id, school_id, class_log_id, student_id, remark) "
        "SELECT gen_random_uuid(), d.school_id, cl.id, d.student_id, d.note "
        "FROM classdiary d "
        "JOIN classlog cl ON cl.section_id = d.section_id AND cl.date = d.date"
    )
    op.execute("DROP TABLE classdiary")

    # 4. The copies of the class go. The section is the route to it from now on.
    for table in DUPLICATE_CLASS_COLUMNS:
        op.execute(f"ALTER TABLE {table} DROP COLUMN classroom_id")

    # 5. With no copy to fall back on, a row without a section has no class at all -
    #    so the section is required.
    for table in SECTION_REQUIRED:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN section_id SET NOT NULL")


def downgrade() -> None:
    """Put the copies back, rejoin `classdiary`, restore `max_marks`."""
    # 1. The section is optional again, now that the class is stored directly.
    for table in SECTION_REQUIRED:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN section_id DROP NOT NULL")

    # 2. The copies come back, filled from the section that replaced them. They land
    #    at the end of their tables, because `ALTER TABLE` can only append.
    for table in DUPLICATE_CLASS_COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN classroom_id uuid")
        op.execute(
            f"UPDATE {table} c SET classroom_id = s.classroom_id "
            f"FROM section s WHERE s.id = c.section_id"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_classroom_id_fkey "
            f"FOREIGN KEY (classroom_id) REFERENCES classroom (id)"
        )

    # 3. `classlog` + `diaryremark` fold back into one `classdiary` row per remark.
    #    A log with no remarks has no student to hang on, so it cannot come back.
    op.execute(
        "CREATE TABLE classdiary ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  student_id uuid NOT NULL,"
        "  teacher_id uuid NOT NULL,"
        "  classroom_id uuid,"
        "  section_id uuid,"
        "  date date NOT NULL,"
        "  note character varying NOT NULL,"
        "  CONSTRAINT classdiary_pkey PRIMARY KEY (id),"
        "  CONSTRAINT classdiary_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT classdiary_student_id_fkey FOREIGN KEY (student_id)"
        "    REFERENCES studentprofile (id),"
        "  CONSTRAINT classdiary_teacher_id_fkey FOREIGN KEY (teacher_id)"
        "    REFERENCES employee (id),"
        "  CONSTRAINT classdiary_classroom_id_fkey FOREIGN KEY (classroom_id)"
        "    REFERENCES classroom (id),"
        "  CONSTRAINT classdiary_section_id_fkey FOREIGN KEY (section_id)"
        "    REFERENCES section (id)"
        ")"
    )
    op.execute(
        "INSERT INTO classdiary (id, school_id, student_id, teacher_id, "
        "                        classroom_id, section_id, date, note) "
        "SELECT gen_random_uuid(), dr.school_id, dr.student_id, cl.teacher_id, "
        "       s.classroom_id, cl.section_id, cl.date, dr.remark "
        "FROM diaryremark dr "
        "JOIN classlog cl ON cl.id = dr.class_log_id "
        "JOIN section s ON s.id = cl.section_id"
    )
    op.execute("DROP TABLE diaryremark")
    op.execute("DROP TABLE classlog")

    # 4. `max_marks` returns to each mark, read back from the exam's own statement of
    #    it. A mark whose (exam, subject) is not in `examsubject` falls back to 100.
    op.execute("ALTER TABLE marks ADD COLUMN max_marks double precision")
    op.execute(
        "UPDATE marks m SET max_marks = es.max_marks FROM examsubject es "
        "WHERE es.exam_id = m.exam_id AND es.subject_id = m.subject_id"
    )
    op.execute("UPDATE marks SET max_marks = 100.0 WHERE max_marks IS NULL")
    op.execute("ALTER TABLE marks ALTER COLUMN max_marks SET NOT NULL")
    op.execute("DROP TABLE examsubject")
