"""Staff registration: the hire flow that starts at "this person is hired".

Revision ID: c3e8a1f6d2b9
Revises: d8a3b6c2f5e1
Create Date: 2026-10-05

Why:
  Staff Hiring only had the candidate pipeline: moving a candidate to Hired
  stamped an employee id and nothing else, so a hired person had no login, no
  staff record, and never appeared in the staff directory or the salary
  register. The registration flow fixes that, the way the admission promotion
  fixed it for students, and it needs two tables:

  * `staffregistration` - the short hire-registration form the office fills
    (name, role, department, qualification, experience, contact email, joining
    date). Submitting it is the whole hiring action.
  * `staffprofile` - the staff member the school actually has: their login
    (`stf.*` / `tea.*`), employee code (`EMP-####`), role and department, plus
    a link to the `teacherprofile` row that teaching roles also own (class
    assignment and timetable place teachers through it).

  The `staffregistration` row keeps the links it created (`staff_profile_id`,
  `user_id`, `promoted_at`), so "Hired" and "in the staff list" can never
  disagree again - re-submitting finds the links and does nothing.

Downgrade drops both tables; no existing table is touched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e8a1f6d2b9"
down_revision: str | Sequence[str] | None = "d8a3b6c2f5e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "staffprofile",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("employee_code", _AUTO_STR(), nullable=False),
        sa.Column("role_codename", _AUTO_STR(), nullable=False),
        sa.Column("department", _AUTO_STR(), nullable=False),
        sa.Column("qualification", _AUTO_STR(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacherprofile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staffprofile_user_id"), "staffprofile", ["user_id"], unique=True
    )
    op.create_index(
        op.f("ix_staffprofile_employee_code"),
        "staffprofile",
        ["employee_code"],
        unique=True,
    )

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
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staffprofile.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staffregistration_staff_profile_id"),
        "staffregistration",
        ["staff_profile_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_staffregistration_staff_profile_id"), table_name="staffregistration"
    )
    op.drop_table("staffregistration")

    op.drop_index(op.f("ix_staffprofile_employee_code"), table_name="staffprofile")
    op.drop_index(op.f("ix_staffprofile_user_id"), table_name="staffprofile")
    op.drop_table("staffprofile")
