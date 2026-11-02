"""RBAC: the role catalog, who holds which role, and what a role may do.

Design (see `info/db_mapping.txt`, LAYER 0):

* `role` - roles are **DATA**, not an enum. `codename` is the machine key
  (`vice_principal`), `label` the human one. Adding a role is an INSERT, never a
  migration - which is exactly the class of bug that killed the old enum (the
  PostgreSQL type had drifted to 14 labels while Python knew 13).
* `user_role` - a person holds **several** roles: a principal who also teaches,
  a physics teacher who also runs the library, a teacher who is also a parent.
  `is_primary` says which one opens their dashboard at login.
* `rolepermission` - which permission a role grants. It stores `role_id`, not
  the role *codename* as text: the old shape repeated "teacher" in hundreds of
  rows, and the database would accept a grant for a role that does not exist.

A user's effective permissions are the **union** over all their roles
(`AuthorizationService`), which is what makes several roles additive instead of
mutually exclusive.

The two join tables use **composite primary keys** instead of a surrogate `id`:
no extra column, and the key itself is the uniqueness rule the doc asks for.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel
from app.core.ids import UUIDMixin


def utcnow() -> datetime:
    """Naive UTC timestamp (the timestamp columns are timezone-less)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Role(UUIDMixin, table=True):
    """One entry in the role catalog."""

    #: Machine name used in code and the API, e.g. `vice_principal`.
    codename: str = Field(unique=True, index=True)
    #: Shown in the UI, e.g. `Vice Principal`.
    label: str
    description: str | None = None
    #: Catalog roles ship with the app (they are not a school's to delete).
    is_system: bool = Field(default=True)


class UserRole(UUIDMixin, table=True):
    """A role held by a person. One row per (user, role) pair.

    The row carries its own auto-increment `id` (every table does, so rows are
    addressable and joins can point at the pair), and `UNIQUE(user_id, role_id)`
    states the real rule: a person holds a given role once.
    """

    # SQLModel would derive `userrole` from the class name; the architecture map
    # names this table `user_role`, so it is pinned here.
    __tablename__ = "user_role"

    user_id: UUID = Field(foreign_key="user.id")
    role_id: UUID = Field(foreign_key="role.id", index=True)
    #: The role whose dashboard opens at login when several are held.
    is_primary: bool = Field(default=False)
    assigned_at: datetime = Field(default_factory=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),
    )


class Permission(UUIDMixin, table=True):
    """Catalog of every permission codename the app checks."""

    #: e.g. "students.read" - the string `RequirePermission(...)` names in code.
    codename: str = Field(unique=True, index=True)
    #: Grouping for the permissions screen, e.g. "Students".
    category: str = Field(default="General")
    #: Human sentence, e.g. "Read Students".
    label: str = Field(default="")


class RolePermission(UUIDMixin, table=True):
    """Which permission a role grants. One row per (role, permission) pair.

    Like every other table it carries its own auto-increment `id`; the real rule
    - a role grants a permission once - is the `UNIQUE(role_id, permission_id)`.
    """

    role_id: UUID = Field(foreign_key="role.id")
    permission_id: UUID = Field(foreign_key="permission.id", index=True)

    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_id", name="uq_rolepermission_role_permission"
        ),
    )


class ImpersonationLog(UUIDMixin, table=True):
    """One row per "the platform admin viewed the app as somebody else" session.

    A switched token already carries the actor in its `act` claim, but a token is
    not a record - it lives in a browser and expires. This table is what makes
    "who looked at whose account, and when" answerable later, and it is closed
    (ended_at) when the admin returns to their own account.
    """

    actor_user_id: UUID = Field(foreign_key="user.id", index=True)
    target_user_id: UUID = Field(foreign_key="user.id", index=True)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    reason: str | None = None
