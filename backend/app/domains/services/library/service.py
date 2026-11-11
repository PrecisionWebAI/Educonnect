"""Library reads: the catalogue and the loan register, from real rows.

`/library/books` and `/library/issues` used to answer with invented copies; the
tables (`librarybook`, `libraryissue`) already hold what the screen shows, so these
read them and join the book title and the borrower's name.
"""

from sqlmodel import Session, select

from app.core.formatting import day
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User

from .models import LibraryBook as LibraryBookModel
from .models import LibraryIssue
from .schemas import BookIssue, LibraryBook


def list_library_books(session: Session) -> list[LibraryBook]:
    """The catalogue from `librarybook`, alphabetical by title."""
    statement = select(LibraryBookModel).order_by(LibraryBookModel.title)  # type: ignore[arg-type]
    return [
        LibraryBook(
            id=book.id,  # type: ignore[arg-type]
            isbn=book.isbn,
            title=book.title,
            author=book.author,
            category=book.category,
            copies=book.copies,
            available=book.available,
            overdue=book.available < book.copies,
        )
        for book in session.exec(statement).all()
    ]


def list_library_issues(session: Session) -> list[BookIssue]:
    """Issued copies from `libraryissue`, soonest due first, with book + borrower."""
    statement = select(LibraryIssue).order_by(LibraryIssue.due_date)  # type: ignore[arg-type]
    items: list[BookIssue] = []
    for issue in session.exec(statement).all():
        book = session.get(LibraryBookModel, issue.book_id)
        student = session.get(Student, issue.student_id) if issue.student_id else None
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        items.append(
            BookIssue(
                id=issue.id,  # type: ignore[arg-type]
                book=book.title if book else "",
                student=user.full_name if user else "",
                issued=day(issue.issued_date),
                due=day(issue.due_date),
                status=issue.status,
            )
        )
    return items
