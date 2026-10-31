"""Remaining Operations screens: meetings, transport, settings, reports,
copilot, chat files.

Revision ID: a7b2c9d1e3f4
Revises: f3a9d1c8e2b7
Create Date: 2026-10-21

Why:
  The Meetings, Transport, Settings (school info / security logs / gateways),
  Reports (cards / data-quality / education), Copilot and Chat-files screens
  still answered with hard-coded rows. This migration gives each of them a real
  table (all tenant-scoped like the other school-owned tables):

    meeting, transportroute, bus, securitylog, gatewaystatus, palettecommand,
    reportcard, dataquality, educationreport, copilotautomation,
    copilotsuggestion, chatfile.

  Settings > Users and Settings > School info are the two that read existing
  tables instead (`user` and `school`), so they need no new table here.

Downgrade drops the twelve tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b2c9d1e3f4"
down_revision: str | Sequence[str] | None = "f3a9d1c8e2b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def _sid() -> sa.Column:
    return sa.Column("school_id", sa.Integer(), nullable=True)


def _tenant(table: str) -> None:
    op.create_index(f"ix_{table}_school_id", table, ["school_id"])
    op.create_foreign_key(
        f"{table}_school_id_fkey", table, "school", ["school_id"], ["id"]
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "meeting",
        sa.Column("title", _AUTO_STR(), nullable=False),
        sa.Column("with_whom", _AUTO_STR(), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time", _AUTO_STR(), nullable=False),
        sa.Column("room", _AUTO_STR(), nullable=True),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Scheduled"),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("meeting")

    op.create_table(
        "transportroute",
        sa.Column("name", _AUTO_STR(), nullable=False),
        sa.Column("bus_id", _AUTO_STR(), nullable=False),
        sa.Column("driver", _AUTO_STR(), nullable=False),
        sa.Column("stops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Active"),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("transportroute")

    op.create_table(
        "bus",
        sa.Column("name", _AUTO_STR(), nullable=False),
        sa.Column("plate", _AUTO_STR(), nullable=False),
        sa.Column("route", _AUTO_STR(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("occupied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Parked"),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("bus")

    op.create_table(
        "securitylog",
        sa.Column("event", _AUTO_STR(), nullable=False),
        sa.Column("user", _AUTO_STR(), nullable=False),
        sa.Column("when", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("securitylog")

    op.create_table(
        "gatewaystatus",
        sa.Column("name", _AUTO_STR(), nullable=False),
        sa.Column("type", _AUTO_STR(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("quota", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("gatewaystatus")

    op.create_table(
        "palettecommand",
        sa.Column("label", _AUTO_STR(), nullable=False),
        sa.Column("shortcut", _AUTO_STR(), nullable=False),
        sa.Column("category", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("palettecommand")

    op.create_table(
        "reportcard",
        sa.Column("title", _AUTO_STR(), nullable=False),
        sa.Column("metric", _AUTO_STR(), nullable=False),
        sa.Column("value", _AUTO_STR(), nullable=False),
        sa.Column("trend", _AUTO_STR(), nullable=False),
        sa.Column("tone", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("reportcard")

    op.create_table(
        "dataquality",
        sa.Column("area", _AUTO_STR(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("issue", _AUTO_STR(), nullable=False),
        sa.Column("status", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("dataquality")

    op.create_table(
        "educationreport",
        sa.Column("metric", _AUTO_STR(), nullable=False),
        sa.Column("class_name", _AUTO_STR(), nullable=False),
        sa.Column("value", _AUTO_STR(), nullable=False),
        sa.Column("trend", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("educationreport")

    op.create_table(
        "copilotautomation",
        sa.Column("title", _AUTO_STR(), nullable=False),
        sa.Column("schedule", _AUTO_STR(), nullable=False),
        sa.Column("last_run", _AUTO_STR(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("copilotautomation")

    op.create_table(
        "copilotsuggestion",
        sa.Column("prompt", _AUTO_STR(), nullable=False),
        sa.Column("tag", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("copilotsuggestion")

    op.create_table(
        "chatfile",
        sa.Column("name", _AUTO_STR(), nullable=False),
        sa.Column("shared_by", _AUTO_STR(), nullable=False),
        sa.Column("size", _AUTO_STR(), nullable=False),
        sa.Column("when", _AUTO_STR(), nullable=False),
        _sid(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _tenant("chatfile")


def downgrade() -> None:
    """Downgrade schema."""
    for table in (
        "chatfile",
        "copilotsuggestion",
        "copilotautomation",
        "educationreport",
        "dataquality",
        "reportcard",
        "palettecommand",
        "gatewaystatus",
        "securitylog",
        "bus",
        "transportroute",
        "meeting",
    ):
        op.drop_constraint(f"{table}_school_id_fkey", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_school_id", table_name=table)
        op.drop_table(table)

