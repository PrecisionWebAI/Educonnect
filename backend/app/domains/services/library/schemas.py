from uuid import UUID

from pydantic import BaseModel


class LibraryBook(BaseModel):
    id: UUID
    isbn: str
    title: str
    author: str
    category: str
    copies: int
    available: int
    overdue: bool | None = None


class BookIssue(BaseModel):
    id: UUID
    book: str
    student: str
    issued: str
    due: str
    status: str
