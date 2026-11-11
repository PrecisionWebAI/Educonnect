from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import BookIssue, LibraryBook

router = APIRouter()

_can_read = RequirePermission("library.read")


@router.get("/books", response_model=list[LibraryBook])
def read_library_books(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The catalogue: one row per title, with the copies currently available."""
    return service.list_library_books(session=session)


@router.get("/issues", response_model=list[BookIssue])
def read_book_issues(
    student_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The loan register. `student_id` is the borrower the caller is asking about."""
    return service.list_library_issues(session=session)
