"""Operations screens: leave, tickets, library, notifications.

Revision ID: f3a9d1c8e2b7
Revises: d9e7f3a5b2c8
Create Date: 2026-10-21

Why:
  The Leave, Tickets, Library and Notifications screens answered with hard-coded
  rows because the database had no table for them. This migration creates five:

    * `leaverequest`     - one table for both student and staff leave (a staff
                           leave has `student_id` NULL), so the leave board, the
                           staff-requests board and the attendance leave-sync all
                           read the same real rows.
    * `supportticket`    - IT/accounts/facility requests with a reporter, an
                           assignee and Open/In Progress/Resolved state.
    * `librarybook`      - the catalogue (ISBN, title, author, copies/available).
    * `libraryissue`     - a book issued to a student with due date + status.
    * `notification`     - a message addressed to one user with a read flag.

  Every table is tenant-scoped (`school_id` -> `school`) exactly like the other
  school-owned tables, so the session listeners in app/core/db.py stamp the
  tenant and filter reads automatically.

Downgrade drops the five tables (indexes first, then the foreign keys via the
table drop).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a9d1c8e2b7"
down_revision: str | Sequence[str] | None = "d9e7f3a5b2c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def _school_id_column() -> sa.Column:
    """The tenant column, matching `TenantMixin` (nullable, indexed, FK school)."""
    return sa.Column("school_id", sa.Integer(), nullable=True)


def _tenant_fk_index(table: str) -> None:
    op.create_index(f"ix_{table}_school_id", table, ["school_id"])
    op.create_foreign_key(
        f"{table}_school_id_fkey", table, "school", ["school_id"], ["id"]
    )


def upgrade() -> None:
    """Upgrade schema."""
    # --- leaverequest -------------------------------------------------------
    op.create_table(
        "leaverequest",
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("requester_user_id", sa.Integer(), nullable=False),
        sa.Column("leave_type", _AUTO_STR(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("reason", _AUTO_STR(), nullable=True),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        _school_id_column(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["requester_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["studentprofile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant_fk_index("leaverequest")

    # --- supportticket ------------------------------------------------------
    op.create_table(
        "supportticket",
        sa.Column("subject", _AUTO_STR(), nullable=False),
        sa.Column("category", _AUTO_STR(), nullable=False),
        sa.Column("priority", _AUTO_STR(), nullable=False, server_default="Medium"),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Open"),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("assignee", _AUTO_STR(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        _school_id_column(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant_fk_index("supportticket")

    # --- librarybook --------------------------------------------------------
    op.create_table(
        "librarybook",
        sa.Column("isbn", _AUTO_STR(), nullable=False),
        sa.Column("title", _AUTO_STR(), nullable=False),
        sa.Column("author", _AUTO_STR(), nullable=False),
        sa.Column("category", _AUTO_STR(), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available", sa.Integer(), nullable=False, server_default="1"),
        _school_id_column(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant_fk_index("librarybook")

    # --- libraryissue -------------------------------------------------------
    op.create_table(
        "libraryissue",
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Issued"),
        _school_id_column(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["librarybook.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["studentprofile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant_fk_index("libraryissue")

    # --- notification -------------------------------------------------------
    op.create_table(
        "notification",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", _AUTO_STR(), nullable=False),
        sa.Column("body", _AUTO_STR(), nullable=False),
        sa.Column("kind", _AUTO_STR(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        _school_id_column(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant_fk_index("notification")


def downgrade() -> None:
    """Downgrade schema."""
    for table in (
        "notification",
        "libraryissue",
        "librarybook",
        "supportticket",
        "leaverequest",
    ):
        op.drop_constraint(f"{table}_school_id_fkey", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_school_id", table_name=table)
        op.drop_table(table)
