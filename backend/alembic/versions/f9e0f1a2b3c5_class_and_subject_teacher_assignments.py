"""Class teacher and subject teacher become real assignments.

Revision ID: f9e0f1a2b3c5
Revises: f9e0f1a2b3c4
Create Date: 2026-11-02

Why:
  Two tables described the same thing twice and could disagree with each other:

  * `classteacherassignment` (teacher, classroom, section) allowed *several* rows
    per section - nothing in the schema stopped a section having three class
    teachers - and let `section_id` be NULL, so "the class teacher of Class 6"
    could be filed against a class rather than a section.
  * `teacherassignment` (teacher, classroom, section, subject) repeated the
    classroom that `section` already carries, and its "who teaches this subject"
    meaning was buried in a timetable-shaped table.

  Both are replaced by the rule itself:

  * `section.class_teacher_id` - one teacher per section, enforced by the column
    rather than by application code;
  * `subjectteacher` (`UNIQUE(section_id, subject_id)`) - one teacher per subject
    per section, living beside `subject` because the mapping is about a subject.

  Rows are carried over before the old tables go. Both were empty at the time of
  writing, but the copy runs anyway so the migration is honest on any database.
  A `classteacherassignment` row with a NULL `section_id` has no section to move
  to, so it is dropped rather than guessed at.

Downgrade recreates both tables empty and drops the two replacements.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3c5"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the two assignment tables with a column and a subject mapping."""
    # 1. One class teacher per section. The column goes last, which is where the
    #    model declares it (`SectionBase` first, then `Section`'s own fields).
    op.execute("ALTER TABLE section ADD COLUMN class_teacher_id uuid")
    op.execute(
        "ALTER TABLE section ADD CONSTRAINT section_class_teacher_id_fkey "
        "FOREIGN KEY (class_teacher_id) REFERENCES employee (id)"
    )
    op.execute("CREATE INDEX ix_section_class_teacher_id ON section (class_teacher_id)")

    # 2. One teacher per subject per section.
    op.execute(
        "CREATE TABLE subjectteacher ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  section_id uuid NOT NULL,"
        "  subject_id uuid NOT NULL,"
        "  teacher_id uuid NOT NULL,"
        "  CONSTRAINT subjectteacher_pkey PRIMARY KEY (id),"
        "  CONSTRAINT uq_subjectteacher_section_subject"
        "    UNIQUE (section_id, subject_id),"
        "  CONSTRAINT subjectteacher_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT subjectteacher_section_id_fkey FOREIGN KEY (section_id)"
        "    REFERENCES section (id),"
        "  CONSTRAINT subjectteacher_subject_id_fkey FOREIGN KEY (subject_id)"
        "    REFERENCES subject (id),"
        "  CONSTRAINT subjectteacher_teacher_id_fkey FOREIGN KEY (teacher_id)"
        "    REFERENCES employee (id)"
        ")"
    )
    op.execute("CREATE INDEX ix_subjectteacher_school_id ON subjectteacher (school_id)")

    # 3. Carry the rows over. A section can only hold one class teacher, so the
    #    first row by id wins where the old table held several.
    op.execute(
        "UPDATE section s SET class_teacher_id = picked.teacher_id "
        "FROM ("
        "  SELECT DISTINCT ON (section_id) section_id, teacher_id "
        "  FROM classteacherassignment WHERE section_id IS NOT NULL "
        "  ORDER BY section_id, id"
        ") AS picked "
        "WHERE picked.section_id = s.id"
    )
    op.execute(
        "INSERT INTO subjectteacher (id, school_id, section_id, subject_id, teacher_id) "
        "SELECT DISTINCT ON (ta.section_id, ta.subject_id) "
        "  gen_random_uuid(), ta.school_id, ta.section_id, ta.subject_id, ta.teacher_id "
        "FROM teacherassignment ta WHERE ta.section_id IS NOT NULL "
        "ORDER BY ta.section_id, ta.subject_id, ta.id"
    )

    # 4. The old shape is gone.
    op.execute("DROP TABLE teacherassignment")
    op.execute("DROP TABLE classteacherassignment")


def downgrade() -> None:
    """Bring back the two assignment tables, empty."""
    op.execute(
        "CREATE TABLE classteacherassignment ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  teacher_id uuid NOT NULL,"
        "  classroom_id uuid NOT NULL,"
        "  section_id uuid,"
        "  CONSTRAINT classteacherassignment_pkey PRIMARY KEY (id),"
        "  CONSTRAINT classteacherassignment_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT classteacherassignment_teacher_id_fkey FOREIGN KEY (teacher_id)"
        "    REFERENCES employee (id),"
        "  CONSTRAINT classteacherassignment_classroom_id_fkey"
        "    FOREIGN KEY (classroom_id) REFERENCES classroom (id),"
        "  CONSTRAINT classteacherassignment_section_id_fkey FOREIGN KEY (section_id)"
        "    REFERENCES section (id)"
        ")"
    )
    op.execute(
        "CREATE INDEX ix_classteacherassignment_school_id "
        "ON classteacherassignment (school_id)"
    )

    op.execute(
        "CREATE TABLE teacherassignment ("
        "  id uuid NOT NULL,"
        "  school_id uuid,"
        "  teacher_id uuid NOT NULL,"
        "  classroom_id uuid NOT NULL,"
        "  section_id uuid,"
        "  subject_id uuid NOT NULL,"
        "  CONSTRAINT teacherassignment_pkey PRIMARY KEY (id),"
        "  CONSTRAINT teacherassignment_school_id_fkey FOREIGN KEY (school_id)"
        "    REFERENCES school (id),"
        "  CONSTRAINT teacherassignment_teacher_id_fkey FOREIGN KEY (teacher_id)"
        "    REFERENCES employee (id),"
        "  CONSTRAINT teacherassignment_classroom_id_fkey"
        "    FOREIGN KEY (classroom_id) REFERENCES classroom (id),"
        "  CONSTRAINT teacherassignment_section_id_fkey FOREIGN KEY (section_id)"
        "    REFERENCES section (id),"
        "  CONSTRAINT teacherassignment_subject_id_fkey FOREIGN KEY (subject_id)"
        "    REFERENCES subject (id)"
        ")"
    )
    op.execute(
        "CREATE INDEX ix_teacherassignment_school_id ON teacherassignment (school_id)"
    )

    op.execute("DROP TABLE subjectteacher")
    op.execute("ALTER TABLE section DROP COLUMN class_teacher_id")
