"""Exam module: two indexes for the queries Phase 9 measured.

Revision ID: 0008
Revises: 0007

* `exam.academic_year_id` - every list and every result overview filters exams by the year on
  screen, and the column had no index;
* `notification (event_type, entity_id)` - a "what changed" message numbers itself by counting
  the messages of its kind already sent for that exam (`service._revision`); with only
  `event_type` indexed that count scans every row of the kind, school-wide.

Both are plain indexes (no data changes), safe to run twice.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _indexes(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    if "ix_exam_academic_year_id" not in _indexes("exam"):
        op.create_index("ix_exam_academic_year_id", "exam", ["academic_year_id"])
    if "ix_notification_event_entity" not in _indexes("notification"):
        op.create_index(
            "ix_notification_event_entity",
            "notification",
            ["event_type", "entity_id"],
        )


def downgrade() -> None:
    if "ix_notification_event_entity" in _indexes("notification"):
        op.drop_index("ix_notification_event_entity", table_name="notification")
    if "ix_exam_academic_year_id" in _indexes("exam"):
        op.drop_index("ix_exam_academic_year_id", table_name="exam")
