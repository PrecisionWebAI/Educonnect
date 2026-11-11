"""Request/response models for the super-admin "switch account" feature."""

from uuid import UUID

from pydantic import BaseModel


class ImpersonationRequest(BaseModel):
    """Body of `POST /auth/impersonate`."""

    user_id: UUID
    #: Optional note kept on the audit row ("checking a parent's fee view").
    reason: str | None = None


class ImpersonationRoleOption(BaseModel):
    """One entry of the role dropdown: a role and how many active people hold it."""

    codename: str
    label: str
    users: int


class ImpersonationTarget(BaseModel):
    """One entry of the people dropdown.

    `role_label` is what the UI shows *under* the person's name, so the picker does
    not have to turn a codename into a readable role itself.
    """

    id: UUID
    email: str
    full_name: str
    roles: list[str]
    role: str
    role_label: str


class ImpersonationRoles(BaseModel):
    roles: list[ImpersonationRoleOption]


class ImpersonationTargets(BaseModel):
    users: list[ImpersonationTarget]


class ScopeSchool(BaseModel):
    """One entry of the school dropdown in "switch account".

    `students` is what the picker shows next to the name, so a platform admin can
    tell an empty school from a populated one before switching into it.
    """

    id: UUID
    code: str
    name: str
    students: int


class ScopeSchools(BaseModel):
    schools: list[ScopeSchool]


class SchoolScopeRequest(BaseModel):
    """Body of `POST /auth/scope/school`.

    `None` is the way back to the platform-wide view - the same token a fresh
    login would give the administrator, with no `sch` claim.
    """

    school_id: UUID | None = None
