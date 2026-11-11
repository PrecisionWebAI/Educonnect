from uuid import UUID

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: UUID
    title: str
    body: str
    kind: str
    time: str
    read: bool
    to: str | None = None
