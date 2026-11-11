"""Drop the last four server defaults the models do not declare.

After `e5f6a7b8c9d0` the column *sets*, types and nullability of the local
database and a model-built one (`scripts/init_schema.py`, which is how Supabase is
created) were identical. `information_schema` then showed four remaining
differences, all server defaults that the migrations had added and that
`SQLModel.metadata` does not declare:

* `guardian.created_at`                       `DEFAULT now()`
* `student.created_on`                        `DEFAULT CURRENT_DATE`
* `student_guardian_relationship.is_primary`  `DEFAULT false`
* `student_guardian_relationship.relationship_type`  `DEFAULT 'guardian'`

They are redundant: every write goes through SQLModel, which fills these values
in Python (`app/domains/students/models.py`), and the model-built database - the
one Supabase runs on - has never had them and seeds the whole demo roll happily.

So they go, and the two databases end up with the same schema, column for
column. If one of them turns out to be wanted, the place to declare it is the
**model** (`sa_column_kwargs={"server_default": ...}`), which then reaches every
database through `init_schema.py` - not a migration, which is what made local
drift in the first place.

`DROP DEFAULT` on a column with no default is a no-op, so this revision applies
unchanged to a model-built database.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

_DEFAULTS = (
    ("guardian", "created_at", "now()"),
    ("student", "created_on", "CURRENT_DATE"),
    ("student_guardian_relationship", "is_primary", "false"),
    (
        "student_guardian_relationship",
        "relationship_type",
        "'guardian'::character varying",
    ),
)


def upgrade() -> None:
    for table, column, _ in _DEFAULTS:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')


def downgrade() -> None:
    for table, column, default in _DEFAULTS:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT {default}'
        )
