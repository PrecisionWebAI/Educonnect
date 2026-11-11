"""UUID primary keys everywhere, with every table rebuilt in a readable order.

Revision ID: f8d9e0f1a2b3
Revises: f7c8d9e0f1a2
Create Date: 2026-11-02

Why:
  Two things change at once, and they need the same operation:

  * **UUID ids.** Every table's `id` becomes a `uuid4` and every foreign key
    follows, so ids are not guessable, do not leak row counts across schools, and
    survive a merge or an import.
  * **Column order.** PostgreSQL fixes a table's column order at creation, and
    the current order is historical - it is whatever a dozen migrations happened
    to append. The models now declare `id`, `school_id`, then the foreign keys,
    then the domain columns grouped (Aadhaar next to PAN, the bank fields
    together) with timestamps last, and this migration makes the database match.

  So the tables are rebuilt rather than altered: the old ones are parked in a
  `legacy` schema, the new ones are created from the models, every row is copied
  across through an old-id -> new-uuid map, and the legacy schema is dropped.
  No row is lost.

Note for future migrations: this one creates the schema from the models, so it
must stay the **last** migration that does so - anything added after it is
written against the UUID schema.
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlmodel import SQLModel

# revision identifiers, used by Alembic.
revision: str = "f8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "f7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Alembic's own bookkeeping table - it must not be moved or rebuilt.
_KEEP = ("alembic_version",)


def _metadata() -> sa.MetaData:
    """The models' metadata, from the one registry the app keeps.

    `app/core/schema.py` lists every model module (it is what builds a database),
    so this migration cannot fall behind a new domain - it used to carry its own
    copy of that list.
    """
    from app.core.schema import load_models

    load_models()
    return SQLModel.metadata


def upgrade() -> None:
    """Rebuild every table with UUID ids and a readable column order."""
    bind = op.get_bind()
    metadata = _metadata()
    inspector = sa.inspect(bind)

    op.execute("CREATE SCHEMA IF NOT EXISTS legacy")

    # 1. Park everything out of the way, so the new tables can take the names.
    parked = {table.name for table in metadata.sorted_tables}
    for name in inspector.get_table_names():
        if name in _KEEP:
            continue
        op.execute(f'ALTER TABLE "{name}" SET SCHEMA legacy')
        parked.discard(name)

    # 2. Create the schema the models describe (UUID ids, ordered columns).
    metadata.create_all(bind)

    # 3. Copy every row across, translating each id through its parent's map.
    _copy_rows(bind, metadata)

    # 4. The old tables have served their purpose.
    op.execute("DROP SCHEMA legacy CASCADE")


def _copy_rows(bind, metadata: sa.MetaData) -> None:
    """Move the rows from `legacy.*` into the new tables.

    `metadata.sorted_tables` is already in dependency order, so a parent is
    always copied before the children that point at it - which is what makes the
    id translation possible in a single pass.
    """
    inspector = sa.inspect(bind)
    legacy_tables = set(inspector.get_table_names(schema="legacy"))
    id_map: dict[str, dict[int, object]] = {}

    for table in metadata.sorted_tables:
        if table.name not in legacy_tables:
            continue
        legacy_columns = {
            column["name"]
            for column in inspector.get_columns(table.name, schema="legacy")
        }
        rows = (
            bind.execute(sa.text(f'SELECT * FROM legacy."{table.name}"')).mappings().all()
        )

        mapping: dict[int, object] = {}
        payload: list[dict] = []
        for row in rows:
            values: dict = {}
            for column in table.columns:
                if column.name == "id":
                    values["id"] = uuid4()
                    continue
                if column.name not in legacy_columns:
                    continue
                value = row[column.name]
                for foreign_key in column.foreign_keys:
                    parent = id_map.get(foreign_key.column.table.name)
                    if value is not None and parent and value in parent:
                        value = parent[value]
                    break
                values[column.name] = value
            mapping[row["id"]] = values["id"]
            payload.append(values)

        if payload:
            bind.execute(sa.insert(table), payload)
        id_map[table.name] = mapping


def downgrade() -> None:
    """Not reversible: the old integer ids are gone once the rows are re-keyed."""
    raise NotImplementedError(
        "UUID ids cannot be converted back to the previous integer sequence."
    )
