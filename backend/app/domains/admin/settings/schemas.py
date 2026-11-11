from uuid import UUID

from pydantic import BaseModel


class SettingUser(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    status: str


class SchoolInfo(BaseModel):
    #: These are fields of one school, not rows, so the key is the field name.
    id: str
    label: str
    value: str


class SecurityLog(BaseModel):
    id: UUID
    event: str
    user: str
    when: str


class GatewayStatus(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    quota: str
