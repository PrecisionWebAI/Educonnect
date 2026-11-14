"""The list-shaped parts of a staff profile, and the post's own detail.

Revision ID: b3d1c8e2f7a9
Revises: f6a7b8c9d0e1
Create Date: 2026-11-12

Why
---
The directory says *who is on the roll*. A profile says *what the school knows
about them*, and that is not one value per person: several degrees, several past
employers, certificates that expire, and the history that explains a seniority
claim years later. In `employee` those would either be a text blob no query can
answer or a numbered column family (`degree_1` … `degree_5`), and both fail the
first time somebody has a sixth qualification.

So four small tables, each school-owned, each `employee_id` + the facts:

    staffqualification       degrees and diplomas (degree, institution, year, grade)
    staffexperience          earlier jobs (employer, designation, from/to)
    staffcertification       certificates (name, issuer, issued, valid till, ref no)
    staffemploymenthistory   joined / promoted / transferred / designation / left

plus four nullable columns on `employee` for the post itself: `designation`,
`employment_type`, `probation_end` and `reports_to_employee_id`.

Nothing is backfilled. An empty profile is the honest state for a school that has
not entered qualifications yet, and a guessed designation ("Teacher") would be a
claim the school never made.

Note for the next revision: `f8d9e0f1a2b3` is the last migration that builds the
schema from the models, so this one is written by hand against the UUID schema -
tables, indexes and foreign keys exactly as the models declare them, so
`scripts/check_schema.py` stays green.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d1c8e2f7a9"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {item["name"] for item in inspector.get_columns(table)}


def _id() -> sa.Column:
    """The row's uuid - `UUIDMixin`, declared first in the models for a reason."""
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _school() -> sa.Column:
    """The tenant column: `TenantMixin` (nullable, indexed, FK to `school`)."""
    return sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True)


def _created_at() -> sa.Column:
    """`utcnow()` is the model's Python default, so the column needs no server one."""
    return sa.Column("created_at", sa.DateTime(), nullable=False)


def _employee() -> sa.Column:
    return sa.Column(
        "employee_id",
        sa.Uuid(),
        sa.ForeignKey("employee.id"),
        nullable=False,
        index=True,
    )


def _create_qualification() -> None:
    if _has_table("staffqualification"):
        return
    op.create_table(
        "staffqualification",
        _id(),
        _school(),
        _employee(),
        sa.Column("degree", _text(), nullable=False),
        sa.Column("institution", _text(), nullable=True),
        sa.Column("year_completed", sa.Integer(), nullable=True),
        sa.Column("grade", _text(), nullable=True),
        _created_at(),
    )


def _create_experience() -> None:
    if _has_table("staffexperience"):
        return
    op.create_table(
        "staffexperience",
        _id(),
        _school(),
        _employee(),
        sa.Column("employer", _text(), nullable=False),
        sa.Column("designation", _text(), nullable=True),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("note", _text(), nullable=True),
        _created_at(),
    )


def _create_certification() -> None:
    if _has_table("staffcertification"):
        return
    op.create_table(
        "staffcertification",
        _id(),
        _school(),
        _employee(),
        sa.Column("name", _text(), nullable=False),
        sa.Column("issuer", _text(), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("valid_till", sa.Date(), nullable=True),
        sa.Column("reference_no", _text(), nullable=True),
        _created_at(),
    )


def _create_history() -> None:
    if _has_table("staffemploymenthistory"):
        return
    op.create_table(
        "staffemploymenthistory",
        _id(),
        _school(),
        _employee(),
        sa.Column("event", _text(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("from_value", _text(), nullable=True),
        sa.Column("to_value", _text(), nullable=True),
        sa.Column("note", _text(), nullable=True),
        # Who recorded it. NULL when a seed or a migration wrote the row.
        sa.Column(
            "recorded_by_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True
        ),
        _created_at(),
    )


def _add_employee_posts() -> None:
    """The post itself: four nullable columns, no backfill (see the module note)."""
    added = (
        ("designation", sa.Column("designation", _text(), nullable=True)),
        ("employment_type", sa.Column("employment_type", _text(), nullable=True)),
        ("probation_end", sa.Column("probation_end", sa.Date(), nullable=True)),
        (
            "reports_to_employee_id",
            sa.Column(
                "reports_to_employee_id",
                sa.Uuid(),
                sa.ForeignKey("employee.id"),
                nullable=True,
            ),
        ),
    )
    for name, column in added:
        if not _has_column("employee", name):
            op.add_column("employee", column)
    if not _has_column("employee", "reports_to_employee_id"):
        return
    op.create_index(
        "ix_employee_reports_to_employee_id",
        "employee",
        ["reports_to_employee_id"],
        if_not_exists=True,
    )


def upgrade() -> None:
    """Four profile tables plus the post's own columns."""
    _add_employee_posts()
    _create_qualification()
    _create_experience()
    _create_certification()
    _create_history()
    print(
        "[profile] staffqualification, staffexperience, staffcertification, "
        "staffemploymenthistory + employee.designation/employment_type/"
        "probation_end/reports_to_employee_id"
    )


def downgrade() -> None:
    """Put the profile back to "not recorded yet".

    The rows go with their tables - a qualification has nowhere else to live - and
    the four `employee` columns are dropped last, because
    `reports_to_employee_id` points at the table it sits on.
    """
    for table in (
        "staffemploymenthistory",
        "staffcertification",
        "staffexperience",
        "staffqualification",
    ):
        op.execute(f'DROP TABLE IF EXISTS "{table}"')

    op.execute("DROP INDEX IF EXISTS ix_employee_reports_to_employee_id")
    for column in (
        "reports_to_employee_id",
        "probation_end",
        "employment_type",
        "designation",
    ):
        if _has_column("employee", column):
            op.drop_column("employee", column)
