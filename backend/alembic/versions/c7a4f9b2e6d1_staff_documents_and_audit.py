"""Staff documents and the staff audit trail.

Revision ID: c7a4f9b2e6d1
Revises: b3d1c8e2f7a9
Create Date: 2026-11-12

Why
---
Phase 2 gave a profile its four list tables. Two things were still missing, and
neither is a list of facts about the person:

    staffdocument    the *files* - a scan, a degree certificate, a contract. The
                     bytes stay on disk under `UPLOAD_DIR/staff-docs/<school>/<employee>/`
                     and the row keeps a **relative** key, its size, its type and
                     who verified it against the original.
    staffauditlog    the *evidence* - who changed what, when. Append-only, because
                     a qualification edited a year after joining is exactly the
                     fact a promotion or a disciplinary argument turns on.

Neither table adds a column to an existing table, which is why this revision is
safe to run on a database that was built by `create_missing()`: a boot stamps the
schema at head without replaying revisions, so a revision that only *creates*
tables still has nothing to do there - `create_all` already made them from the
models. (Revisions that `ADD COLUMN` are the ones that need care; see the
operational note in `backend/phase.md`.)

`storage_key` is deliberately nullable-free but **not** a path: it is
`staff-docs/<school_id>/<employee_id>/<uuid><ext>`, joined onto `UPLOAD_DIR` when
a download is served, and re-checked to be inside that employee's own folder. No
absolute path is ever stored, so a moved volume is not a data migration and no
response can leak the server's layout.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a4f9b2e6d1"
down_revision: str | Sequence[str] | None = "b3d1c8e2f7a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _id() -> sa.Column:
    """The row's uuid - `UUIDMixin`, declared first in the models for a reason."""
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _school() -> sa.Column:
    """The tenant column: `TenantMixin` (nullable, indexed, FK to `school`)."""
    return sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True)


def _employee() -> sa.Column:
    return sa.Column(
        "employee_id",
        sa.Uuid(),
        sa.ForeignKey("employee.id"),
        nullable=False,
        index=True,
    )


def _user(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("user.id"), nullable=True)


def _created_at() -> sa.Column:
    """`utcnow()` is the model's Python default, so the column needs no server one."""
    return sa.Column("created_at", sa.DateTime(), nullable=False)


def _create_documents() -> None:
    if _has_table("staffdocument"):
        return
    op.create_table(
        "staffdocument",
        _id(),
        _school(),
        _employee(),
        sa.Column("doc_type", _text(), nullable=False),
        sa.Column("title", _text(), nullable=True),
        sa.Column("file_name", _text(), nullable=False),
        sa.Column("storage_key", _text(), nullable=False),
        sa.Column("content_type", _text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        _user("uploaded_by_user_id"),
        sa.Column("verified_on", sa.Date(), nullable=True),
        _user("verified_by_user_id"),
        sa.Column("note", _text(), nullable=True),
        _created_at(),
        sa.UniqueConstraint(
            "employee_id",
            "doc_type",
            "file_name",
            name="uq_staffdocument_employee_type_name",
        ),
    )


def _create_audit_log() -> None:
    if _has_table("staffauditlog"):
        return
    op.create_table(
        "staffauditlog",
        _id(),
        _school(),
        _employee(),
        sa.Column("section", _text(), nullable=False),
        sa.Column("action", _text(), nullable=False),
        sa.Column("row_id", sa.Uuid(), nullable=True),
        sa.Column("summary", _text(), nullable=False),
        _user("changed_by_user_id"),
        _created_at(),
    )


def upgrade() -> None:
    _create_documents()
    _create_audit_log()


def downgrade() -> None:
    for name in ("staffauditlog", "staffdocument"):
        if _has_table(name):
            op.drop_table(name)
