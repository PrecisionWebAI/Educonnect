"""Library tables: the catalogue and the loan register.

Both are tenant-scoped (`TenantMixin`) like every other school-owned table, so the
session listeners stamp `school_id` and filter reads automatically - a librarian in
one school never sees another school's copies.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class LibraryBookBase(SQLModel):
    isbn: str
    title: str
    author: str
    category: str
    copies: int = Field(default=1)
    available: int = Field(default=1)


class LibraryBook(LibraryBookBase, TenantMixin, UUIDMixin, table=True):
    pass


class LibraryIssueBase(SQLModel):
    book_id: UUID = Field(foreign_key="librarybook.id")
    student_id: UUID = Field(foreign_key="student.id")
    issued_date: date
    due_date: date
    status: str = Field(default="Issued")  # "Issued" / "Returned" / "Overdue"


class LibraryIssue(LibraryIssueBase, TenantMixin, UUIDMixin, table=True):
    pass
