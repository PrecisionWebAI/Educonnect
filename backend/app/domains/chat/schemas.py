from datetime import datetime

from pydantic import BaseModel

from .models import ChatMessageBase, ChatThreadBase


class ChatThreadCreate(ChatThreadBase):
    participant_user_ids: list[int]


class ChatThreadRead(ChatThreadBase):
    id: int


class ChatMessageCreate(BaseModel):
    content_text: str
    attachment_url: str | None = None


class ChatMessageRead(ChatMessageBase):
    id: int
    created_at: datetime
