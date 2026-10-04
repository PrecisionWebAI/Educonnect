"""User (identity) - one login per person.

There is deliberately **no `role` column** (see `info/db_mapping.txt` LAYER 0):
a person holds one or more roles, and those live in `user_role`
(`app/domains/auth/models.py`). Everything that used to read `user.role` now
reads the loaded role set instead.
"""

import enum
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.domains.auth.models import utcnow


class RoleEnum(enum.StrEnum):
    """The seeded role codenames (`role.codename`).

    Convenience for code that must name a role; the database stores roles as
    rows, so this enum is never a column type and adding a role is still just an
    INSERT into `role` (this enum only needs to grow when code refers to it).
    """

    system_admin = "system_admin"
    owner = "owner"
    principal = "principal"
    vice_principal = "vice_principal"
    hod = "hod"
    teacher = "teacher"
    class_teacher = "class_teacher"
    subject_teacher = "subject_teacher"
    accountant = "accountant"
    librarian = "librarian"
    transport = "transport"
    staff = "staff"
    student = "student"
    guardian = "guardian"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: str
    is_active: bool = True


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utcnow)
    #: The person's real-world email. The **login** email is a generated school
    #: address (`stu.…` for a student, `gau.…` for a guardian), so the contact
    #: email is kept separately - it is what recognises "this is the same parent"
    #: when a second child is admitted, and where a password reset would go.
    contact_email: str | None = Field(default=None, index=True)


class UserCreate(UserBase):
    password: str
    #: Roles to grant on creation. A person may hold several; the first one is
    #: stored as their primary role.
    roles: list[RoleEnum] = Field(default_factory=lambda: [RoleEnum.staff])


class UserRead(UserBase):
    id: int
