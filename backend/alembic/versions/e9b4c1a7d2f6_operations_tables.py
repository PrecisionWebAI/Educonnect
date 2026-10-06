"""Operations tables: full admission form, hiring pipeline, fee-card fields,
salary register.

Revision ID: e9b4c1a7d2f6
Revises: d3f8b2c7a1e5
Create Date: 2026-10-04

Why:
  The four Operations screens (Admission, Staff Hiring, Fees Structure, Staff
  Salary) rendered hard-coded rows because the database could not store what
  they collect. This migration gives them somewhere to live.

  * `admissionapplication` - widened from 9 columns to the whole admission form,
    `status` moved off the `admissionstatus` enum onto text (`Draft` /
    `Registered` - the values the screen shows), and four separation columns
    added so a student leaving the school is recorded on their own row.
    The table held 0 rows, so the `applied_for_class_level` int -> text
    conversion and the enum drop need no data conversion (the backfills below
    are still written out, so this migration also works on a populated copy).
  * `staffvacancy` + `hiringcandidate` - new; nothing stored hiring before.
  * `feestructure` - gained `due_day` and `status` (Draft / Active).
  * `salarypayment` - new; there was no salary table at all, only a static
    figure on the staff profile, so the register was invented in the frontend.

Downgrade restores the original admission shape and drops the new tables, so a
bad deploy can still be rolled back.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9b4c1a7d2f6"
down_revision: str | Sequence[str] | None = "d3f8b2c7a1e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString

#: Admission-form columns added by this migration (all nullable text).
_ADMISSION_TEXT_COLUMNS = (
    "student_middle_name",
    "gender",
    "blood_group",
    "religion",
    "category",
    "mother_tongue",
    "nationality",
    "aadhaar_id",
    "address",
    "permanent_address",
    "previous_school_name",
    "previous_class_passed",
    "previous_board",
    "transfer_certificate_no",
    "old_unique_id",
    "father_name",
    "father_occupation",
    "father_phone",
    "father_email",
    "father_annual_income",
    "mother_name",
    "mother_occupation",
    "mother_phone",
    "mother_email",
    "mother_annual_income",
    "guardian_relation",
    "guardian_occupation",
    "guardian_address",
    "current_class_or_last_class",
    "applied_section_preference",
    "needs_transport",
    "transport_route",
    "needs_hostel",
    "separation_dropped_class",
    "separation_reason",
    "separation_session",
)

#: Columns that already existed but stop being mandatory (drafts are partial).
_ADMISSION_OPTIONAL_COLUMNS = (
    "student_first_name",
    "student_last_name",
    "date_of_birth",
    "guardian_name",
    "guardian_email",
    "guardian_phone",
    "applied_for_class_level",
)


def upgrade() -> None:
    """Upgrade schema."""
    # --- 1. feestructure: due day + publish state -------------------------
    op.add_column("feestructure", sa.Column("due_day", _AUTO_STR(), nullable=True))
    op.add_column(
        "feestructure",
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Draft"),
    )
    # The server default only exists to fill the rows already in the table.
    op.alter_column("feestructure", "status", server_default=None)

    # --- 2. admissionapplication: the whole form --------------------------
    for column in _ADMISSION_TEXT_COLUMNS:
        op.add_column(
            "admissionapplication", sa.Column(column, _AUTO_STR(), nullable=True)
        )

    op.add_column(
        "admissionapplication", sa.Column("separation_date", sa.Date(), nullable=True)
    )

    # `applied_for_class_level` stored a grade number; the form stores the class
    # the family asked for ("Grade 6"), so the column becomes text.
    op.alter_column(
        "admissionapplication",
        "applied_for_class_level",
        existing_type=sa.Integer(),
        type_=_AUTO_STR(),
        existing_nullable=False,
        postgresql_using="applied_for_class_level::text",
    )

    for column in _ADMISSION_OPTIONAL_COLUMNS:
        op.alter_column("admissionapplication", column, nullable=True)

    # --- 3. admissionapplication.status: enum -> text ---------------------
    op.alter_column(
        "admissionapplication",
        "status",
        existing_type=sa.Enum(
            "pending",
            "under_review",
            "approved",
            "rejected",
            name="admissionstatus",
        ),
        type_=_AUTO_STR(),
        existing_nullable=False,
        postgresql_using="status::text",
    )
    op.execute("DROP TYPE IF EXISTS admissionstatus")

    # --- 4. admissionapplication: form number + creation date -------------
    op.add_column(
        "admissionapplication", sa.Column("application_no", _AUTO_STR(), nullable=True)
    )
    op.execute(
        "UPDATE admissionapplication "
        "SET application_no = 'ADM-' || id::text WHERE application_no IS NULL"
    )
    op.alter_column("admissionapplication", "application_no", nullable=False)
    op.create_index(
        op.f("ix_admissionapplication_application_no"),
        "admissionapplication",
        ["application_no"],
        unique=True,
    )

    op.add_column(
        "admissionapplication", sa.Column("created_on", sa.Date(), nullable=True)
    )
    op.execute(
        "UPDATE admissionapplication SET created_on = now()::date "
        "WHERE created_on IS NULL"
    )
    op.alter_column("admissionapplication", "created_on", nullable=False)

    # --- 5. staffvacancy + hiringcandidate --------------------------------
    op.create_table(
        "staffvacancy",
        sa.Column("role", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("openings", sa.Integer(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staffvacancy_role"), "staffvacancy", ["role"], unique=False)

    op.create_table(
        "hiringcandidate",
        sa.Column("candidate_no", _AUTO_STR(), nullable=True),
        sa.Column("candidate_name", _AUTO_STR(), nullable=False),
        sa.Column("role", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("qualification", _AUTO_STR(), nullable=True),
        sa.Column("experience", sa.Integer(), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.Column("interview_on", sa.Date(), nullable=True),
        sa.Column("emp_id", _AUTO_STR(), nullable=True),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_hiringcandidate_candidate_no"),
        "hiringcandidate",
        ["candidate_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_hiringcandidate_emp_id"), "hiringcandidate", ["emp_id"], unique=False
    )

    # --- 6. salarypayment -------------------------------------------------
    op.create_table(
        "salarypayment",
        sa.Column("staff_code", _AUTO_STR(), nullable=False),
        sa.Column("staff_name", _AUTO_STR(), nullable=False),
        sa.Column("designation", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("month", _AUTO_STR(), nullable=False),
        sa.Column("gross", sa.Float(), nullable=False),
        sa.Column("deductions", sa.Float(), nullable=False),
        sa.Column("net", sa.Float(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_salarypayment_staff_code"),
        "salarypayment",
        ["staff_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_salarypayment_month"), "salarypayment", ["month"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_salarypayment_month"), table_name="salarypayment")
    op.drop_index(op.f("ix_salarypayment_staff_code"), table_name="salarypayment")
    op.drop_table("salarypayment")

    op.drop_index(op.f("ix_hiringcandidate_emp_id"), table_name="hiringcandidate")
    op.drop_index(op.f("ix_hiringcandidate_candidate_no"), table_name="hiringcandidate")
    op.drop_table("hiringcandidate")

    op.drop_index(op.f("ix_staffvacancy_role"), table_name="staffvacancy")
    op.drop_table("staffvacancy")

    op.drop_column("admissionapplication", "created_on")

    op.drop_index(
        op.f("ix_admissionapplication_application_no"),
        table_name="admissionapplication",
    )
    op.drop_column("admissionapplication", "application_no")

    # Text -> enum again: rows written by the new UI ("Draft" / "Registered")
    # have no enum label, so they are folded back onto `pending` first.
    op.execute(
        "UPDATE admissionapplication SET status = 'pending' WHERE status NOT IN "
        "('pending', 'under_review', 'approved', 'rejected')"
    )
    admission_status = sa.Enum(
        "pending", "under_review", "approved", "rejected", name="admissionstatus"
    )
    admission_status.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "admissionapplication",
        "status",
        existing_type=_AUTO_STR(),
        type_=admission_status,
        existing_nullable=False,
        postgresql_using="status::admissionstatus",
    )

    op.alter_column(
        "admissionapplication",
        "applied_for_class_level",
        existing_type=_AUTO_STR(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="applied_for_class_level::integer",
    )

    for column in (
        "student_first_name",
        "student_last_name",
        "date_of_birth",
        "guardian_name",
        "guardian_email",
        "guardian_phone",
    ):
        op.alter_column(
            "admissionapplication",
            column,
            existing_type=_AUTO_STR(),
            nullable=False,
        )

    op.drop_column("admissionapplication", "separation_date")
    for column in reversed(_ADMISSION_TEXT_COLUMNS):
        op.drop_column("admissionapplication", column)

    op.drop_column("feestructure", "status")
    op.drop_column("feestructure", "due_day")
