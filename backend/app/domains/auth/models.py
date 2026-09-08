"""
DB models for the permission catalog and role→permission assignments.
These replace the static ROLE_PERMISSIONS_MAP in permissions.py.
"""

from sqlmodel import Field, SQLModel


class Permission(SQLModel, table=True):
    """Catalog of every available permission string in the system."""

    id: int | None = Field(default=None, primary_key=True)
    # e.g. "students.read"
    codename: str = Field(unique=True, index=True)
    # e.g. "Students"
    category: str = Field(default="General")
    # e.g. "Read Students"
    label: str = Field(default="")


class RolePermission(SQLModel, table=True):
    """Join table: which permissions are granted to a given role."""

    id: int | None = Field(default=None, primary_key=True)
    # e.g. "admin", "teacher" — matches RoleEnum.value
    role: str = Field(index=True)
    permission_id: int = Field(foreign_key="permission.id", index=True)
