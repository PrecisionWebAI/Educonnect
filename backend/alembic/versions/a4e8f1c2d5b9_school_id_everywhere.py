"""Multi-tenancy: `school_id` on every school-owned table.

Revision ID: a4e8f1c2d5b9
Revises: f2d5a8c1e4b7
Create Date: 2026-10-21

Why:
  `school` and `user.school_id` existed, but the data itself was still global: a
  second school would have listed the first school's classes, students, fees and
  papers, because none of those tables had a tenant column.

  This adds `school_id` (indexed, FK to `school`) to the 29 school-owned tables.
  `user` already has it. `role`, `permission`, `rolepermission`, `user_role`,
  `school` and `impersonationlog` stay global on purpose - they are platform
  catalogs and the platform audit trail.

  Enforcement lives in the application, not the database: `app/core/db.py` adds
  `WHERE school_id = :session_school` to every SELECT and stamps every INSERT.
  The column is therefore nullable - the listener is what guarantees a row lands
  in a school - and a later revision can tighten it to NOT NULL once every seed
  and fixture sets it explicitly.

  Also: `classroom.name` and `subject.name` / `subject.code` stop being globally
  unique and become unique **per school** - every school has a "Class 6" and a
  "Mathematics".

Upgrade backfills every existing row with the only school that can exist today,
so nothing is orphaned. Downgrade removes the columns and restores the global
unique indexes.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4e8f1c2d5b9"
down_revision: str | Sequence[str] | None = "f2d5a8c1e4b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Every table `TenantMixin` is mixed into (`app/domains/*/models.py`).
#: `user` is not listed: it already had the column from the previous revision.
TENANT_TABLES: tuple[str, ...] = (
    "admissionapplication",
    "attendanceauditlog",
    "attendancerecord",
    "chatmessage",
    "chatthread",
    "chatthreadparticipant",
    "classdiary",
    "classroom",
    "classteacherassignment",
    "examsource",
    "feestructure",
    "feetransaction",
    "generationjob",
    "hiringcandidate",
    "homeworkassignment",
    "homeworksubmission",
    "paperdraft",
    "questionusagelog",
    "salarypayment",
    "section",
    "staffprofile",
    "staffregistration",
    "staffvacancy",
    "studentparentrelationship",
    "studentprofile",
    "subject",
    "teacherassignment",
    "teacherprofile",
    "timetableperiod",
)


def _columns(table: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND table_schema = current_schema()"
        ),
        {"t": table},
    )
    return {row[0] for row in rows}


def _indexes(table: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text("SELECT indexname FROM pg_indexes WHERE tablename = :t"), {"t": table}
    )
    return {row[0] for row in rows}


def _current_school_id() -> int | None:
    """The school every existing row belongs to (there can only be one today)."""
    return (
        op.get_bind()
        .execute(sa.text("SELECT id FROM school ORDER BY id LIMIT 1"))
        .scalar()
    )


def _add_tenant_column(table: str, school_id: int | None) -> None:
    if "school_id" not in _columns(table):
        op.add_column(table, sa.Column("school_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_school_id", table, ["school_id"])
        op.create_foreign_key(
            f"{table}_school_id_fkey", table, "school", ["school_id"], ["id"]
        )
    if school_id is None:
        return
    # Backfill in the same revision, so no existing row is left tenant-less.
    op.get_bind().execute(
        sa.text(f'UPDATE "{table}" SET school_id = :sid WHERE school_id IS NULL'),
        {"sid": school_id},
    )


def _per_school_uniques() -> None:
    """`classroom.name` and `subject.name|code` are unique per school, not globally."""
    if "uq_classroom_school_name" not in _indexes("classroom"):
        if "ix_classroom_name" in _indexes("classroom"):
            op.drop_index("ix_classroom_name", table_name="classroom")
        op.create_index("ix_classroom_name", "classroom", ["name"])
        op.create_index(
            "uq_classroom_school_name", "classroom", ["school_id", "name"], unique=True
        )

    if "uq_subject_school_name" not in _indexes("subject"):
        for index in ("ix_subject_name", "ix_subject_code"):
            if index in _indexes("subject"):
                op.drop_index(index, table_name="subject")
        op.create_index("ix_subject_name", "subject", ["name"])
        op.create_index("ix_subject_code", "subject", ["code"])
        op.create_index(
            "uq_subject_school_name", "subject", ["school_id", "name"], unique=True
        )
        op.create_index(
            "uq_subject_school_code", "subject", ["school_id", "code"], unique=True
        )


def upgrade() -> None:
    school_id = _current_school_id()
    for table in TENANT_TABLES:
        _add_tenant_column(table, school_id)
    _per_school_uniques()


def downgrade() -> None:
    op.drop_index("uq_subject_school_code", table_name="subject")
    op.drop_index("uq_subject_school_name", table_name="subject")
    op.drop_index("ix_subject_name", table_name="subject")
    op.drop_index("ix_subject_code", table_name="subject")
    op.create_index("ix_subject_name", "subject", ["name"], unique=True)
    op.create_index("ix_subject_code", "subject", ["code"], unique=True)

    op.drop_index("uq_classroom_school_name", table_name="classroom")
    op.drop_index("ix_classroom_name", table_name="classroom")
    op.create_index("ix_classroom_name", "classroom", ["name"], unique=True)

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"{table}_school_id_fkey", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_school_id", table_name=table)
        op.drop_column(table, "school_id")
