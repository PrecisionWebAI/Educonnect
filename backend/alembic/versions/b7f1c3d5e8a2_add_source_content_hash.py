"""RAG Phase 3.1: examsource content_hash + replaces_id (dedup & versioning)

Revision ID: b7f1c3d5e8a2
Revises: e5f7b9c2d4a6
Create Date: 2026-09-26

Kyun (asli problem):
  · **Duplicate indexing** — same PDF/text dobara save hone par naya row banta
    tha + poora content dobara embed hota tha (paisa/time barbaad, aur vector DB
    mein same content do baar). Ab `content_hash` par dedup hoti hai.
  · **Stale vectors** — source replace/re-upload hone par purane chunks vector DB
    mein pade rehte the aur retrieval mein aa sakte the. `replaces_id` version
    chain banati hai, jisse purane source ke vectors delete kiye jaate hain.

Dono columns nullable hain (purani rows ke liye koi backfill zaroori nahi —
service hash ki kami par chup-chaap compute kar leti hai).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "b7f1c3d5e8a2"
down_revision: Union[str, Sequence[str], None] = "e5f7b9c2d4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("examsource", sa.Column("content_hash", _AUTO_STR(), nullable=True))
    op.create_index(
        "ix_examsource_content_hash", "examsource", ["content_hash"], unique=False
    )
    op.add_column("examsource", sa.Column("replaces_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_examsource_replaces_id",
        "examsource",
        "examsource",
        ["replaces_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_examsource_replaces_id", "examsource", type_="foreignkey")
    op.drop_column("examsource", "replaces_id")
    op.drop_index("ix_examsource_content_hash", table_name="examsource")
    op.drop_column("examsource", "content_hash")
