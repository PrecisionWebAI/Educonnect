"""Rename admissionapplication to student_admission_form.

Revision ID: f2c3d4e5f6a7
Revises: f1b2c3d4e5f6
Create Date: 2026-11-02

Why:
  The table is the student's admission form - the row the Operations > Admission
  screen fills and the row a student login is created from. `admissionapplication`
  said neither whose form it is nor that it belongs to the student. The new name
  says both, and it lines up with `employee` (the staff form) on the other side of
  `user`.

  PostgreSQL keeps the old constraint/index names after a table rename, so they are
  renamed here too - that keeps autogenerate reporting no drift.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "f1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = "admissionapplication"
_NEW = "student_admission_form"

#: (old, new) for every constraint whose name is derived from the table name.
_CONSTRAINTS = (
    ("admissionapplication_pkey", "student_admission_form_pkey"),
    (
        "admissionapplication_student_id_key",
        "student_admission_form_student_id_key",
    ),
    (
        "admissionapplication_student_id_fkey",
        "student_admission_form_student_id_fkey",
    ),
    (
        "admissionapplication_student_user_id_fkey",
        "student_admission_form_student_user_id_fkey",
    ),
    (
        "admissionapplication_guardian_user_id_fkey",
        "student_admission_form_guardian_user_id_fkey",
    ),
    ("admissionapplication_school_id_fkey", "student_admission_form_school_id_fkey"),
)

#: (old, new) for the plain indexes (not constraints).
_INDEXES = (
    (
        "ix_admissionapplication_application_no",
        "ix_student_admission_form_application_no",
    ),
    ("ix_admissionapplication_school_id", "ix_student_admission_form_school_id"),
)


def _constraint_exists(name: str) -> bool:
    return (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name})
        .first()
        is not None
    )


def _index_exists(name: str) -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text("SELECT 1 FROM pg_class WHERE relname = :n AND relkind = 'i'"),
            {"n": name},
        )
        .first()
        is not None
    )


def _rename(old_table: str, new_table: str, constraints, indexes) -> None:
    """Rename the table, then the constraints/indexes named after it."""
    inspector = sa.inspect(op.get_bind())
    if new_table not in inspector.get_table_names():
        op.rename_table(old_table, new_table)
    for old, new in constraints:
        if _constraint_exists(old):
            op.execute(
                sa.text(f'ALTER TABLE "{new_table}" RENAME CONSTRAINT "{old}" TO "{new}"')
            )
    for old, new in indexes:
        if _index_exists(old):
            op.execute(sa.text(f'ALTER INDEX "{old}" RENAME TO "{new}"'))


def upgrade() -> None:
    """Rename the table and everything named after it."""
    _rename(_OLD, _NEW, _CONSTRAINTS, _INDEXES)


def downgrade() -> None:
    """Put the old table name (and its constraint/index names) back."""
    _rename(
        _NEW,
        _OLD,
        tuple((new, old) for old, new in _CONSTRAINTS),
        tuple((new, old) for old, new in _INDEXES),
    )
