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


class Meeting(MeetingBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TransportRouteBase(SQLModel):
    name: str
    bus_id: str  # "B-01"
    driver: str
    stops: int = 0
    students: int = 0
    status: str = "Active"


class TransportRoute(TransportRouteBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class BusBase(SQLModel):
    name: str
    plate: str
    route: str
    capacity: int = 0
    occupied: int = 0
    status: str = "Parked"


class Bus(BusBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class SecurityLogBase(SQLModel):
    event: str
    user: str  # the login/email as shown on the screen
    when: str  # "Today, 09:12"


class SecurityLog(SecurityLogBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class GatewayStatusBase(SQLModel):
    name: str
    type: str
    status: str
    quota: str


class GatewayStatus(GatewayStatusBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class PaletteCommandBase(SQLModel):
    label: str
    shortcut: str
    category: str


class PaletteCommand(PaletteCommandBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ReportCardBase(SQLModel):
    title: str
    metric: str
    value: str
    trend: str
    tone: str  # "green" / "red" / "amber"


class ReportCard(ReportCardBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class DataQualityBase(SQLModel):
    area: str
    score: int
    issue: str
    status: str  # Healthy / Attention / Critical


class DataQuality(DataQualityBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class EducationReportBase(SQLModel):
    metric: str
    class_name: str
    value: str
    trend: str


class EducationReport(EducationReportBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class CopilotAutomationBase(SQLModel):
    title: str
    schedule: str
    last_run: str
    active: bool = True


class CopilotAutomation(CopilotAutomationBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class CopilotSuggestionBase(SQLModel):
    prompt: str
    tag: str


class CopilotSuggestion(CopilotSuggestionBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ChatFileBase(SQLModel):
    name: str
    shared_by: str
    size: str
    when: str


class ChatFile(ChatFileBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)

