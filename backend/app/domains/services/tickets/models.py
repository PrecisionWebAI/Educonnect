"""The help desk.

`category`, `priority` and `status` are plain text on purpose (not enums): the
stored value is the value the screen shows, so the UI labels ("In Progress",
"High") are the same words the office typed.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class SupportTicketBase(SQLModel):
    subject: str
    category: str  # "IT" / "Accounts" / "Facility" / ...
    priority: str = Field(default="Medium")  # "High" / "Medium" / "Low"
    status: str = Field(default="Open")  # "Open" / "In Progress" / "Resolved"
    reporter_user_id: UUID = Field(foreign_key="user.id")
    assignee: str | None = None  # free text ("Tech Desk", "Finance")


class SupportTicket(SupportTicketBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
