"""The notification rows one person receives.

Tenant-scoped (`TenantMixin`) like every other school-owned table, and owned by
`user_id` on top of that: the screen shows only the signed-in person's rows.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class NotificationBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id")
    title: str
    body: str
    kind: str  # "Attendance" / "Homework" / "Fee" / ...
    read: bool = Field(default=False)


class Notification(NotificationBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
