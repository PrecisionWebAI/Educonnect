"""Tables behind the remaining Operations screens (leave, tickets, library,
notifications).

These screens previously answered with hard-coded rows because the database had
nowhere to store what they collect. Each table is tenant-scoped (`TenantMixin`)
like every other school-owned table, so the session listeners stamp `school_id`
and filter reads automatically.

Status/type columns are plain text on purpose (not enums): the stored value is
the value the screen shows, which keeps the UI labels ("Pending", "Medical",
"In Progress") identical to the database instead of mapping them back and forth.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.core.tenancy import TenantMixin


class LeaveRequestBase(SQLModel):
    #: Set for a student leave, NULL for a staff leave (the two share one table:
    #: both screens show the same "request -> approve/reject" flow).
    student_id: int | None = Field(default=None, foreign_key="studentprofile.id")
    #: The person who filed it (the guardian/student for a student leave, the
    #: staff member for a staff leave).
    requester_user_id: int = Field(foreign_key="user.id")
    leave_type: str  # "Medical" / "Personal" / "Casual" / "Sick" / "Earned" / "OD"
    from_date: date
    to_date: date
    days: int
    reason: str | None = None
    status: str = Field(default="Pending")  # "Pending" / "Approved" / "Rejected"


class LeaveRequest(LeaveRequestBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SupportTicketBase(SQLModel):
    subject: str
    category: str  # "IT" / "Accounts" / "Facility" / ...
    priority: str = Field(default="Medium")  # "High" / "Medium" / "Low"
    status: str = Field(default="Open")  # "Open" / "In Progress" / "Resolved"
    reporter_user_id: int = Field(foreign_key="user.id")
    assignee: str | None = None  # free text ("Tech Desk", "Finance")


class SupportTicket(SupportTicketBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LibraryBookBase(SQLModel):
    isbn: str
    title: str
    author: str
    category: str
    copies: int = Field(default=1)
    available: int = Field(default=1)


class LibraryBook(LibraryBookBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class LibraryIssueBase(SQLModel):
    book_id: int = Field(foreign_key="librarybook.id")
    student_id: int = Field(foreign_key="studentprofile.id")
    issued_date: date
    due_date: date
    status: str = Field(default="Issued")  # "Issued" / "Returned" / "Overdue"


class LibraryIssue(LibraryIssueBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class NotificationBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    title: str
    body: str
    kind: str  # "Attendance" / "Homework" / "Fee" / ...
    read: bool = Field(default=False)


class Notification(NotificationBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
