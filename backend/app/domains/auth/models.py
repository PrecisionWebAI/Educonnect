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

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Naive UTC timestamp (the timestamp columns are timezone-less)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Role(SQLModel, table=True):
    """One entry in the role catalog."""

    id: int | None = Field(default=None, primary_key=True)
    #: Machine name used in code and the API, e.g. `vice_principal`.
    codename: str = Field(unique=True, index=True)
    #: Shown in the UI, e.g. `Vice Principal`.
    label: str
    description: str | None = None
    #: Catalog roles ship with the app (they are not a school's to delete).
    is_system: bool = Field(default=True)


class UserRole(SQLModel, table=True):
    """A role held by a person. One row per (user, role) pair.

    The composite primary key *is* the UNIQUE(user_id, role_id) rule the
    architecture map asks for - stating it twice would only add a second index.
    """

    # SQLModel would derive `userrole` from the class name; the architecture map
    # names this table `user_role`, so it is pinned here.
    __tablename__ = "user_role"

    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role_id: int = Field(foreign_key="role.id", primary_key=True, index=True)
    #: The role whose dashboard opens at login when several are held.
    is_primary: bool = Field(default=False)
    assigned_at: datetime = Field(default_factory=utcnow)


class Permission(SQLModel, table=True):
    """Catalog of every permission codename the app checks."""

    id: int | None = Field(default=None, primary_key=True)
    #: e.g. "students.read" - the string `RequirePermission(...)` names in code.
    codename: str = Field(unique=True, index=True)
    #: Grouping for the permissions screen, e.g. "Students".
    category: str = Field(default="General")
    #: Human sentence, e.g. "Read Students".
    label: str = Field(default="")


class RolePermission(SQLModel, table=True):
    """Which permission a role grants. One row per (role, permission) pair.

    Composite key again: `(role_id, permission_id)` is the uniqueness rule, and
    `role_id` leads it because "all permissions of a role" is the hot lookup.
    """

    role_id: int = Field(foreign_key="role.id", primary_key=True)
    permission_id: int = Field(
        foreign_key="permission.id", primary_key=True, index=True
    )


class ImpersonationLog(SQLModel, table=True):
    """One row per "the platform admin viewed the app as somebody else" session.

    A switched token already carries the actor in its `act` claim, but a token is
    not a record - it lives in a browser and expires. This table is what makes
    "who looked at whose account, and when" answerable later, and it is closed
    (ended_at) when the admin returns to their own account.
    """

    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int = Field(foreign_key="user.id", index=True)
    target_user_id: int = Field(foreign_key="user.id", index=True)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    reason: str | None = None

