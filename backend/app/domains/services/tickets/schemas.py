from uuid import UUID

from pydantic import BaseModel


class TicketItem(BaseModel):
    id: UUID
    subject: str
    category: str
    priority: str
    status: str
    reporter: str
    assignee: str
    updated: str
