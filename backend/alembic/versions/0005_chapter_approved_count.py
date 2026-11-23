"""Remember how many chapters the principal last approved.

Revision ID: 0005
Revises: 0004

While changes to an approved chapter list wait for approval, the Course table keeps
showing the approved count. Existing approved lists get their current chapter count.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    have = {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("classroomsubject")
    }
    if "chapter_plan_approved_count" in have:
        return
    op.add_column(
        "classroomsubject",
        sa.Column("chapter_plan_approved_count", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE classroomsubject AS cs
           SET chapter_plan_approved_count =
               (SELECT count(*) FROM chapter AS ch WHERE ch.classroom_subject_id = cs.id)
         WHERE cs.chapter_plan_status = 'Approved'
        """
    )


def downgrade() -> None:
    op.drop_column("classroomsubject", "chapter_plan_approved_count")
