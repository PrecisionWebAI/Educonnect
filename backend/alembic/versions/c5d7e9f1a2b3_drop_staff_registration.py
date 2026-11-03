"""Drop the staff registration table - the form now fills the profile directly.

Revision ID: c5d7e9f1a2b3
Revises: b8f3d2e4a6c1
Create Date: 2026-10-31

Why:
  Hiring used to keep two tables - `staffregistration` (the form, one row per
  submission, holding a promotion link to the employee it created) and
  `staffprofile` (the employee). The form was just a staging area: its fields are
  already copied onto `staffprofile` at promotion time, and the Registration tab
  is the only writer.

  Filling the form now creates the `staffprofile` row (and its login) directly,
  so the staging table is redundant and removed. It had zero rows.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d7e9f1a2b3"
down_revision: str | Sequence[str] | None = "b8f3d2e4a6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the now-unused registration staging table."""
    op.drop_table("staffregistration")


def downgrade() -> None:
    """Recreate the table (schema as it was last seen)."""
    import sqlalchemy as sa
    import sqlmodel

    _AUTO_STR = sqlmodel.sql.sqltypes.AutoString
    op.create_table(
        "staffregistration",
        sa.Column("full_name", _AUTO_STR(), nullable=False),
        sa.Column("role_codename", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("qualification", _AUTO_STR(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("contact_email", _AUTO_STR(), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("notes", _AUTO_STR(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("phone", _AUTO_STR(), nullable=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("address", _AUTO_STR(), nullable=True),
        sa.Column("emergency_contact", _AUTO_STR(), nullable=True),
        sa.Column("aadhaar_no", _AUTO_STR(), nullable=True),
        sa.Column("pan_no", _AUTO_STR(), nullable=True),
        sa.Column("bank_name", _AUTO_STR(), nullable=True),
        sa.Column("bank_account_no", _AUTO_STR(), nullable=True),
        sa.Column("ifsc", _AUTO_STR(), nullable=True),
        sa.Column("salary_monthly", sa.Float(), nullable=True),
        sa.Column("previous_salary_monthly", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )