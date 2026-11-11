"""User (identity) - one login per person.

There is deliberately **no `role` column** (see `info/db_mapping.txt` LAYER 0):
a person holds one or more roles, and those live in `user_role`
(`app/domains/auth/models.py`). Everything that used to read `user.role` now
reads the loaded role set instead.
"""

import enum
from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel
from sqlalchemy import Index, text

from app.domains.auth.models import utcnow

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin

# Imported for its side effect: `TenantMixin.school_id` is a foreign key to
# `school`, and SQLAlchemy can only resolve that string when the `School` table is
# in the same metadata by the time the mappers are configured.
from app.domains.admin.platform.models import School  # noqa: F401

from app.core.text import CanonicalRequest


class RoleEnum(enum.StrEnum):
    """The seeded role codenames (`role.codename`).

    Convenience for code that must name a role; the database stores roles as
    rows, so this enum is never a column type and adding a role is still just an
    INSERT into `role` (this enum only needs to grow when code refers to it).
    """

    system_admin = "system_admin"
    school_admin = "school_admin"
    principal = "principal"
    vice_principal = "vice_principal"
    hod = "hod"
    teacher = "teacher"
    accountant = "accountant"
    librarian = "librarian"
    transport = "transport"
    staff = "staff"
    student = "student"
    guardian = "guardian"


class UserBase(SQLModel):
    #: The login. Unique **inside a school** (see `User.__table_args__`): two schools
    #: may each have an `admin@abc`, while the platform's own accounts - which have
    #: no school - are unique among themselves.
    email: str = Field(index=True)
    full_name: str
    is_active: bool = True


class User(UserBase, TenantMixin, UUIDMixin, table=True):
    hashed_password: str
    created_at: datetime = Field(default_factory=utcnow)
    # `school_id` comes from TenantMixin: NULL for the platform roles
    # (`system_admin`, `owner`), set for every school-level account - that is the
    # tenant boundary the session is bound to on each request.

    #: Both indexes are **partial**, which is what lets the platform accounts (no
    #: school) and the school accounts (one school each) each keep their own rule:
    #: a school's address is unique within it, and a platform address is unique
    #: across the platform.
    __table_args__ = (
        Index(
            "uq_user_school_email",
            "school_id",
            "email",
            unique=True,
            postgresql_where=text("school_id IS NOT NULL"),
        ),
        Index(
            "uq_user_platform_email",
            "email",
            unique=True,
            postgresql_where=text("school_id IS NULL"),
        ),
    )


class UserCreate(CanonicalRequest, UserBase):
    password: str
    #: Roles to grant on creation. A person may hold several; the first one is
    #: stored as their primary role.
    roles: list[RoleEnum] = Field(default_factory=lambda: [RoleEnum.staff])


class UserRead(UserBase):
    id: UUID
