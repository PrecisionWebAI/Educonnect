"""The school (tenant): the registration record every school-owned row belongs to.

One row per registered school. `code` is the slug the logins are built from -
school `abc` gets `admin@abc` - so it is kept short, lowercase and unique.

Platform roles (`system_admin`, `owner`) have no school; a `school_admin` always
has exactly one, and that is the boundary its permissions apply inside.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.domains.auth.models import utcnow


class SchoolBase(SQLModel):
    #: The school's name, as it appears on its letterhead.
    name: str = Field(unique=True, index=True)
    #: Slug used to build logins: `abc` -> `admin@abc`.
    code: str = Field(unique=True, index=True)
    #: The school's own contact address (not the admin's login).
    email: str = Field(unique=True, index=True)
    phone: str | None = None
    address: str | None = None
    #: A suspended school keeps its data but none of its logins work.
    is_active: bool = True


class School(SchoolBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class SchoolCreate(SchoolBase):
    """What registering a school sends."""


class SchoolRead(SchoolBase):
    id: int
