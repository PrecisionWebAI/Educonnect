"""Hiring pipeline interview intake + employee detail fields.

Revision ID: a7e2c9f1d4b3
Revises: d6f3e8b2c1a4
Create Date: 2026-10-31

Why:
  * The Pipeline tab becomes an interview scheduler: a candidate now carries
    contact details (phone/email), the post applied for (`applied_for`, a role
    codename), an optional subject, a resume path and a scheduled interview
    date+time, plus the who/when of the Hired decision.
  * The Registration tab becomes the full employee record: `staffprofile` (the
    single employee table) and `staffregistration` (the form) gain KYC / bank /
    salary columns so a hire captures Aadhaar, bank details and salary in one
    step instead of a separate HR system.

Downgrade drops the added columns (FKs are dropped first).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e2c9f1d4b3"
down_revision: str | Sequence[str] | None = "d6f3e8b2c1a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    # --- hiringcandidate: interview intake + decision stamp -----------------
    op.add_column("hiringcandidate", sa.Column("phone", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("email", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("applied_for", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("subject_name", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("resume_path", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("interview_at", sa.DateTime(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("interview_note", _AUTO_STR(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("decided_by_user_id", sa.Integer(), nullable=True))
    op.add_column("hiringcandidate", sa.Column("decided_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        "fk_hiringcandidate_subject_id",
        "hiringcandidate",
        "subject",
        ["subject_id"],
        ["id"],
    )
    op.create_index(
        "ix_hiringcandidate_applied_for",
        "hiringcandidate",
        ["applied_for"],
        unique=False,
    )

    # --- staffregistration: the expanded hire form ---------------------------
    op.add_column("staffregistration", sa.Column("phone", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.add_column("staffregistration", sa.Column("address", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("emergency_contact", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("aadhaar_no", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("pan_no", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("bank_name", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("bank_account_no", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("ifsc", _AUTO_STR(), nullable=True))
    op.add_column("staffregistration", sa.Column("salary_monthly", sa.Float(), nullable=True))
    op.add_column("staffregistration", sa.Column("previous_salary_monthly", sa.Float(), nullable=True))

    # --- staffprofile: the employee record ----------------------------------
    op.add_column("staffprofile", sa.Column("email", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("phone", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.add_column("staffprofile", sa.Column("address", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("emergency_contact", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("aadhaar_no", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("pan_no", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("bank_name", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("bank_account_no", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("ifsc", _AUTO_STR(), nullable=True))
    op.add_column("staffprofile", sa.Column("salary_monthly", sa.Float(), nullable=True))
    op.add_column("staffprofile", sa.Column("previous_salary_monthly", sa.Float(), nullable=True))
    op.create_foreign_key(
        "fk_staffprofile_subject_id",
        "staffprofile",
        "subject",
        ["subject_id"],
        ["id"],
    )
    op.create_index(
        "ix_staffprofile_aadhaar_no", "staffprofile", ["aadhaar_no"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_staffprofile_aadhaar_no", table_name="staffprofile")
    op.drop_index("ix_hiringcandidate_applied_for", table_name="hiringcandidate")
    op.drop_constraint("fk_staffprofile_subject_id", "staffprofile", type_="foreignkey")
    op.drop_constraint(
        "fk_hiringcandidate_subject_id", "hiringcandidate", type_="foreignkey"
    )

    for column in (
        "previous_salary_monthly",
        "salary_monthly",
        "ifsc",
        "bank_account_no",
        "bank_name",
        "pan_no",
        "aadhaar_no",
        "emergency_contact",
        "address",
        "subject_id",
        "phone",
        "email",
    ):
        op.drop_column("staffprofile", column)

    for column in (
        "previous_salary_monthly",
        "salary_monthly",
        "ifsc",
        "bank_account_no",
        "bank_name",
        "pan_no",
        "aadhaar_no",
        "emergency_contact",
        "address",
        "subject_id",
        "phone",
    ):
        op.drop_column("staffregistration", column)

    for column in (
        "decided_at",
        "decided_by_user_id",
        "interview_note",
        "interview_at",
        "resume_path",
        "subject_name",
        "subject_id",
        "applied_for",
        "email",
        "phone",
    ):
        op.drop_column("hiringcandidate", column)
