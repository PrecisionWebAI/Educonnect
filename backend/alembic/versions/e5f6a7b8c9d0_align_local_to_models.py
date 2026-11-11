"""Bring the local database in line with the models (the deployed truth).

`scripts/init_schema.py` builds a database from `SQLModel.metadata`, and Supabase
is built that way, so the models are what "the schema" means now. The local
development database was built incrementally and had drifted from them in three
measurable ways, all found by comparing `information_schema` on both:

* **Six NOT NULLs** the models require and the local columns lacked
  (`classroom.class_id`, `classroom.section_id`, `guardian.created_at`,
  `student.created_on`, `student_guardian_relationship.is_primary`,
  `student_guardian_relationship.relationship_type`). Checked for nulls first:
  none.
* **One column going the other way** - `student.admission_number` is nullable in
  the models (a student row may exist before a number is minted) but was NOT
  NULL locally.
* **Two server defaults** the models do not declare (`classname.level = 0`,
  `classname.stage = 'primary'`); the seeder writes both explicitly.

What is **not** changed here, on purpose: the six unique rules the models declare
are already enforced locally as standalone unique indexes
(`CREATE UNIQUE INDEX uq_classname_name ...`, visible in `pg_index`). Only a few
of the *names* differ from what `create_all` emits
(`uq_subjectteacher_section_subject` here vs
`uq_subjectteacher_classroom_subject` there, and the same for syllabus progress
and the class log). Uniqueness is therefore identical - adding a same-column
constraint beside an existing unique index would double the write cost and buy
nothing.

Every statement below is written to be a **no-op on a model-built database**, so
this revision is safe to apply to Supabase as-is: `SET NOT NULL` on an already
NOT NULL column does nothing and `DROP DEFAULT` on a column without a default
does nothing.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

#: Nothing to add: see the docstring - the unique rules already exist locally as
#: unique indexes with (mostly) the same names, so only the column-level
#: differences below are real drift.
_UNIQUE: tuple[tuple[str, str, str], ...] = ()

_NULLABLE_OFF = (
    ("classroom", "class_id"),
    ("classroom", "section_id"),
    ("guardian", "created_at"),
    ("student", "created_on"),
    ("student_guardian_relationship", "is_primary"),
    ("student_guardian_relationship", "relationship_type"),
)


def upgrade() -> None:
    # 1. Server defaults the models do not declare.
    op.execute("ALTER TABLE classname ALTER COLUMN level DROP DEFAULT")
    op.execute("ALTER TABLE classname ALTER COLUMN stage DROP DEFAULT")

    # 2. Columns the models mark NOT NULL (verified: no nulls).
    for table, column in _NULLABLE_OFF:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET NOT NULL')

    # 3. The one column that goes the other way: a number can be minted later.
    op.execute("ALTER TABLE student ALTER COLUMN admission_number DROP NOT NULL")

    # 4. (No constraint work: the unique rules already exist as unique indexes.)


def downgrade() -> None:
    """Put the local drift back. Only useful for going back to the old shape."""
    for name, table, _ in _UNIQUE:
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{name}"')

    op.execute("ALTER TABLE student ALTER COLUMN admission_number SET NOT NULL")

    for table, column in _NULLABLE_OFF:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP NOT NULL')

    op.execute("ALTER TABLE classname ALTER COLUMN level SET DEFAULT 0")
    op.execute("ALTER TABLE classname ALTER COLUMN stage SET DEFAULT 'primary'")
