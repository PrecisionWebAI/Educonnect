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
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class LeaveRequestBase(SQLModel):
    #: Set for a student leave, NULL for a staff leave (the two share one table:
    #: both screens show the same "request -> approve/reject" flow).
    student_id: UUID | None = Field(default=None, foreign_key="student.id")
    #: The person who filed it (the guardian/student for a student leave, the
    #: staff member for a staff leave).
    requester_user_id: UUID = Field(foreign_key="user.id")
    leave_type: str  # "Medical" / "Personal" / "Casual" / "Sick" / "Earned" / "OD"
    from_date: date
    to_date: date
    days: int
    reason: str | None = None
    status: str = Field(default="Pending")  # "Pending" / "Approved" / "Rejected"


class LeaveRequest(LeaveRequestBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SupportTicketBase(SQLModel):
    subject: str
    category: str  # "IT" / "Accounts" / "Facility" / ...
    priority: str = Field(default="Medium")  # "High" / "Medium" / "Low"
    status: str = Field(default="Open")  # "Open" / "In Progress" / "Resolved"
    reporter_user_id: UUID = Field(foreign_key="user.id")
    assignee: str | None = None  # free text ("Tech Desk", "Finance")


class SupportTicket(SupportTicketBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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


class NotificationBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id")
    title: str
    body: str
    kind: str  # "Attendance" / "Homework" / "Fee" / ...
    read: bool = Field(default=False)


class Notification(NotificationBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# The remaining Operations screens: meetings, transport, settings, reports,
# copilot, chat files.
# ---------------------------------------------------------------------------


class MeetingBase(SQLModel):
    title: str
    with_whom: str
    meeting_date: date
    meeting_time: str  # "4 PM"
    room: str | None = None
    status: str = Field(default="Scheduled")  # Scheduled / Pending / Done


class Meeting(MeetingBase, TenantMixin, UUIDMixin, table=True):
    pass


class TransportRouteBase(SQLModel):
    name: str
    bus_id: str  # "B-01"
    driver: str
    stops: int = 0
    students: int = 0
    status: str = "Active"


class TransportRoute(TransportRouteBase, TenantMixin, UUIDMixin, table=True):
    pass


class BusBase(SQLModel):
    name: str
    plate: str
    route: str
    capacity: int = 0
    occupied: int = 0
    status: str = "Parked"


class Bus(BusBase, TenantMixin, UUIDMixin, table=True):
    pass


class SecurityLogBase(SQLModel):
    event: str
    user: str  # the login/email as shown on the screen
    when: str  # "Today, 09:12"


class SecurityLog(SecurityLogBase, TenantMixin, UUIDMixin, table=True):
    pass


class GatewayStatusBase(SQLModel):
    name: str
    type: str
    status: str
    quota: str


class GatewayStatus(GatewayStatusBase, TenantMixin, UUIDMixin, table=True):
    pass


class PaletteCommandBase(SQLModel):
    label: str
    shortcut: str
    category: str


class PaletteCommand(PaletteCommandBase, TenantMixin, UUIDMixin, table=True):
    pass


class ReportCardBase(SQLModel):
    title: str
    metric: str
    value: str
    trend: str
    tone: str  # "green" / "red" / "amber"


class ReportCard(ReportCardBase, TenantMixin, UUIDMixin, table=True):
    pass


class DataQualityBase(SQLModel):
    area: str
    score: int
    issue: str
    status: str  # Healthy / Attention / Critical


class DataQuality(DataQualityBase, TenantMixin, UUIDMixin, table=True):
    pass


class EducationReportBase(SQLModel):
    metric: str
    class_name: str
    #: The class the metric is scoped to - a `classname` row. The wording above is
    #: kept for the report's "Scope" column and for rows written before this column.
    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    value: str
    trend: str


class EducationReport(EducationReportBase, TenantMixin, UUIDMixin, table=True):
    pass


class CopilotAutomationBase(SQLModel):
    title: str
    schedule: str
    last_run: str
    active: bool = True


class CopilotAutomation(CopilotAutomationBase, TenantMixin, UUIDMixin, table=True):
    pass


class CopilotSuggestionBase(SQLModel):
    prompt: str
    tag: str


class CopilotSuggestion(CopilotSuggestionBase, TenantMixin, UUIDMixin, table=True):
    pass


class ChatFileBase(SQLModel):
    name: str
    shared_by: str
    size: str
    when: str


class ChatFile(ChatFileBase, TenantMixin, UUIDMixin, table=True):
    pass
