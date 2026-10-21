"""Multi-tenant helpers - one `school_id` column, enforced by the session.

Why this shape
--------------
Every school-owned table needs the same column, and every one of the ~90 queries
in the app needs to respect it. Editing them by hand would mean touching 18
domains and remembering the rule on every future query - one forgotten `where`
is a silent data leak.

So the rule lives in **one** place instead:

* `TenantMixin` declares `school_id` once; every school-owned model inherits it.
* `app/core/db.py` installs two Session events:
    - `do_orm_execute`   -> adds `WHERE school_id = :current` to every SELECT
    - `before_flush`     -> stamps `school_id` on new rows, rejects cross-school writes
* `get_current_user` sets the tenant once per request
  (`session.info["school_id"] = user.school_id`).

Consequences worth knowing:

* Platform roles (`system_admin`, `owner`) have `school_id = None`, so the
  listeners stay inert for them - that is the escape hatch for cross-school work,
  the seeds and the tests.
* A single-record read from another school does not raise; it simply finds
  nothing, which is the correct answer for an API (404, not 403 - it must not
  confirm that the id exists elsewhere).
* The column is nullable in the database. `before_flush` is what guarantees a row
  always lands in a school; making it NOT NULL is a later hardening step that
  needs every seed and fixture to set it explicitly.
"""

from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as _Session  # noqa: F401  (documented above)
from sqlmodel import Field, SQLModel


class TenantError(RuntimeError):
    """A school-scoped row was written outside the session's school."""


class TenantMixin(SQLModel):
    """The tenant column, mixed into every school-owned table.

    Nullable on purpose: `before_flush` fills it from the session, so model
    constructors stay unchanged (`Classroom(name=..., level=...)`).
    """

    school_id: int | None = Field(
        default=None, foreign_key="school.id", index=True
    )


#: `session.exec(stmt, execution_options={SKIP_SCHOOL: True})` opts a query out of
#: the tenant filter - only for genuinely global reads (platform admin, seeds).
SKIP_SCHOOL = "skip_school"


def tenant_of(session: Session) -> int | None:
    """The school this session is bound to, or None for platform roles."""
    return session.info.get("school_id")


def bound_to(session: Session, school_id: int | None) -> None:
    """Bind a session to a school (used by `get_current_user` and the seeds)."""
    session.info["school_id"] = school_id
