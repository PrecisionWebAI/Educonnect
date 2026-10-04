"""Admission promotes into a student: link columns + guardian contact email

Registering an application now creates the real records (student login,
`studentprofile`, guardian login, parent link), so the application needs to
remember what it created - that link is what keeps "Registered" and "listed in
the student directory" the same thing.

* `admissionapplication.student_id`      the student it made (UNIQUE: one form,
                                         one student)
* `admissionapplication.student_user_id` / `guardian_user_id`  the two logins
* `admissionapplication.promoted_at`     when that happened
* `user.contact_email`                   the person's real email; the login email
                                         is a generated school address
                                         (`stu.*` / `gau.*`), and this column is
                                         how a parent's second child is recognised

Revision ID: d8a3b6c2f5e1
Revises: c7f2a9d4e6b8
Create Date: 2026-04-11
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d8a3b6c2f5e1"
down_revision = "c7f2a9d4e6b8"
branch_labels = None
depends_on = None

#: (column, referred table, referred column) - names follow SQLAlchemy's own
#: `<table>_<column>_fkey` pattern, so autogenerate does not report drift.
_FK_COLUMNS = (
    ("admissionapplication_student_id_fkey", "student_id", "studentprofile", "id"),
    ("admissionapplication_student_user_id_fkey", "student_user_id", "user", "id"),
    ("admissionapplication_guardian_user_id_fkey", "guardian_user_id", "user", "id"),
)


def upgrade() -> None:
    """Add the promotion link and the contact email."""
    op.add_column("user", sa.Column("contact_email", sa.String(), nullable=True))
    op.create_index("ix_user_contact_email", "user", ["contact_email"], unique=False)

    op.add_column(
        "admissionapplication", sa.Column("student_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "admissionapplication",
        sa.Column("student_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "admissionapplication",
        sa.Column("guardian_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "admissionapplication", sa.Column("promoted_at", sa.DateTime(), nullable=True)
    )

    for name, column, target_table, target_column in _FK_COLUMNS:
        op.create_foreign_key(
            name,
            "admissionapplication",
            target_table,
            [column],
            [target_column],
        )

    # One form cannot create two students; NULL stays allowed for drafts.
    op.create_unique_constraint(
        "admissionapplication_student_id_key", "admissionapplication", ["student_id"]
    )


def downgrade() -> None:
    """Drop the link and the contact email."""
    op.drop_constraint(
        "admissionapplication_student_id_key", "admissionapplication", type_="unique"
    )
    for name, _column, _target_table, _target_column in reversed(_FK_COLUMNS):
        op.drop_constraint(name, "admissionapplication", type_="foreignkey")

    for column in ("promoted_at", "guardian_user_id", "student_user_id", "student_id"):
        op.drop_column("admissionapplication", column)

    op.drop_index("ix_user_contact_email", table_name="user")
    op.drop_column("user", "contact_email")
