from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.text import CanonicalRequest

from .models import ChatMessageBase, ChatThreadBase


class ChatThreadCreate(CanonicalRequest, ChatThreadBase):
    participant_user_ids: list[UUID]


class ChatThreadRead(ChatThreadBase):
    id: UUID


class ChatMessageCreate(CanonicalRequest):
    content_text: str
    attachment_url: str | None = None


class ChatMessageRead(ChatMessageBase):
    id: UUID
    created_at: datetime
    sender_name: str | None = None
    sender_role: str | None = None


class ChatFile(BaseModel):
    id: UUID
    name: str
    sharedBy: str
    size: str
    #: Renamed from `when` - a keyword (Rule 6). Camel like `sharedBy`: this payload
    #: has always been camelCase on the wire.
    sharedAt: str
