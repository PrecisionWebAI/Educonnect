from datetime import datetime

from sqlmodel import Field, SQLModel


class ChatThreadParticipant(SQLModel, table=True):
    thread_id: int = Field(foreign_key="chatthread.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)


class ChatThreadBase(SQLModel):
    name: str | None = None
    is_group: bool = False


class ChatThread(ChatThreadBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ChatMessageBase(SQLModel):
    thread_id: int = Field(foreign_key="chatthread.id")
    sender_id: int = Field(foreign_key="user.id")
    content_text: str
    attachment_url: str | None = None


class ChatMessage(ChatMessageBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
