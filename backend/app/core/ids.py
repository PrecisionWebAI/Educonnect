"""Primary keys: one UUID per row.

Every table uses a UUID `id` (``uuid4``) rather than a sequential integer:

* ids are not guessable and do not leak row counts across schools,
* two schools - or an import - can create rows without colliding,
* a row keeps its identity if data is ever merged or sharded.

`UUIDMixin` is declared **last** in a model's bases on purpose. SQLAlchemy reads
the bases in *reverse* order and the class's own fields after them, so the mixin
lands first in the table: `id`, then the tenant `school_id`, then the domain
columns - which is the order the tables are read in.
"""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UUIDMixin(SQLModel):
    """The `id` column, mixed into every table."""

    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
