"""Merge the legacy branches with the Phase 3 academic-year head.

`b4e7f1a2c9d3` and `c1d2e3f4a5b6` are pre-existing heads from the repository's
older feature branches. The Phase 3 chain ends at `d4f6a8b2c9e1`. A merge revision
keeps `alembic upgrade head` unambiguous without rewriting either branch's history.
The merge itself has no schema work; it just joins the branches.

Revision ID: e5a7b9c1d3f4
Revises: b4e7f1a2c9d3, c1d2e3f4a5b6, d4f6a8b2c9e1
"""

from collections.abc import Sequence

revision: str = "e5a7b9c1d3f4"
down_revision: str | Sequence[str] | None = (
    "b4e7f1a2c9d3",
    "c1d2e3f4a5b6",
    "d4f6a8b2c9e1",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
