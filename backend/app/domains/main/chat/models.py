from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.admin.users.models import User  # noqa: F401


class ChatThreadParticipant(TenantMixin, UUIDMixin, table=True):
    """Who is in a thread.

    Carries its own UUID `id` like every other table; `UNIQUE(thread_id, user_id)`
    states the real rule - a person joins a thread once.
    """

    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_chatparticipant_thread_user"),
    )

    thread_id: UUID = Field(foreign_key="chatthread.id")
    user_id: UUID = Field(foreign_key="app_user.id")


class ChatThreadBase(SQLModel):
    name: str | None = None
    is_group: bool = False


class ChatThread(ChatThreadBase, TenantMixin, UUIDMixin, table=True):
    pass


class ChatMessageBase(SQLModel):
    thread_id: UUID = Field(foreign_key="chatthread.id")
    sender_id: UUID = Field(foreign_key="app_user.id")
    content_text: str
    attachment_url: str | None = None


class ChatMessage(ChatMessageBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatFileBase(SQLModel):
    name: str
    shared_by: str
    size: str
    #: When it was shared. Was `when` - a keyword (Rule 6).
    shared_at: str


class ChatFile(ChatFileBase, TenantMixin, UUIDMixin, table=True):
    pass
