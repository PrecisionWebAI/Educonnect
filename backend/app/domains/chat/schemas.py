from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from .models import ChatMessageBase, ChatThreadBase


class ChatThreadCreate(ChatThreadBase):
    participant_user_ids: list[UUID]


class ChatThreadRead(ChatThreadBase):
    id: UUID


class ChatMessageCreate(BaseModel):
    content_text: str
    attachment_url: str | None = None


class ChatMessageRead(ChatMessageBase):
    id: UUID
    created_at: datetime
    sender_name: str | None = None
    sender_role: str | None = None
