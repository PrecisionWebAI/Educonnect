from uuid import UUID
from pydantic import BaseModel


class LeaveApplicationItem(BaseModel):
    id: UUID
    student: str
    className: str
    type: str
    from_date: str
    to_date: str
    reason: str
    days: int
    status: str
    submittedAt: str


class StaffLeaveRow(BaseModel):
    id: UUID
    name: str
    role: str
    type: str
    from_date: str
    days: int
    balance: int
    status: str


class MeetingItem(BaseModel):
    id: UUID
    title: str
    with_whom: str
    date: str
    time: str
    room: str
    type: str


class TicketItem(BaseModel):
    id: UUID
    subject: str
    category: str
    priority: str
    status: str
    reporter: str
    assignee: str
    updated: str


class ReportCard(BaseModel):
    id: UUID
    title: str
    metric: str
    value: str
    trend: str
    tone: str


class DataQualityRow(BaseModel):
    id: UUID
    area: str
    score: int
    issue: str
    status: str


class EducationReportRow(BaseModel):
    id: UUID
    metric: str
    className: str
    value: str
    trend: str


class SettingUser(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    status: str


class SchoolInfo(BaseModel):
    #: These are fields of one school, not rows, so the key is the field name.
    id: str
    label: str
    value: str


class SecurityLog(BaseModel):
    id: UUID
    event: str
    user: str
    when: str


class GatewayStatus(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    quota: str


class CopilotAutomation(BaseModel):
    id: UUID
    title: str
    schedule: str
    lastRun: str
    active: bool


class CopilotSuggestion(BaseModel):
    id: UUID
    prompt: str
    tag: str


class PaletteCommand(BaseModel):
    id: UUID
    label: str
    shortcut: str
    category: str


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


class TransportRoute(BaseModel):
    id: UUID
    name: str
    busId: str
    driver: str
    stops: int
    students: int
    status: str


class Bus(BaseModel):
    id: UUID
    name: str
    plate: str
    route: str
    capacity: int
    occupied: int
    status: str


class ClassroomItem(BaseModel):
    id: UUID
    title: str
    subject: str
    className: str
    teacher: str
    nextLesson: str
    students: int


class LessonResource(BaseModel):
    id: UUID
    type: str
    title: str


class LessonDetail(BaseModel):
    #: `None` when nothing is scheduled - there is no lesson row to point at.
    id: UUID | None = None
    title: str
    subject: str
    className: str
    duration: str
    topics: list[str]
    resources: list[LessonResource]
    homework: str


class NotificationItem(BaseModel):
    id: UUID
    title: str
    body: str
    kind: str
    time: str
    read: bool
    to: str | None = None


class ChatFile(BaseModel):
    id: UUID
    name: str
    sharedBy: str
    size: str
    when: str
