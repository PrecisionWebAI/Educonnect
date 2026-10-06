"""Request/response models for the super-admin "switch account" feature."""

from pydantic import BaseModel


class ImpersonationRequest(BaseModel):
    """Body of `POST /auth/impersonate`."""

    user_id: int
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

    id: int
    email: str
    full_name: str
    roles: list[str]
    role: str
    role_label: str


class ImpersonationRoles(BaseModel):
    roles: list[ImpersonationRoleOption]


class ImpersonationTargets(BaseModel):
    users: list[ImpersonationTarget]
