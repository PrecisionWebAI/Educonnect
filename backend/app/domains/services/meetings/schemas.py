from uuid import UUID

from pydantic import BaseModel


class MeetingItem(BaseModel):
    id: UUID
    title: str
    with_whom: str
    date: str
    time: str
    room: str
    type: str
