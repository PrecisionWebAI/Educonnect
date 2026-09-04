from pydantic import BaseModel


class LeaveApplicationItem(BaseModel):
    id: int
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
    id: int
    name: str
    role: str
    type: str
    from_date: str
    days: int
    balance: int
    status: str


class MeetingItem(BaseModel):
    id: int
    title: str
    with_whom: str
    date: str
    time: str
    room: str
    type: str


class TicketItem(BaseModel):
    id: int
    subject: str
    category: str
    priority: str
    status: str
    reporter: str
    assignee: str
    updated: str


class ReportCard(BaseModel):
    id: int
    title: str
    metric: str
    value: str
    trend: str
    tone: str


class DataQualityRow(BaseModel):
    id: int
    area: str
    score: int
    issue: str
    status: str


class EducationReportRow(BaseModel):
    id: int
    metric: str
    className: str
    value: str
    trend: str


class SettingUser(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str


class SchoolInfo(BaseModel):
    id: int
    label: str
    value: str


class SecurityLog(BaseModel):
    id: int
    event: str
    user: str
    when: str


class GatewayStatus(BaseModel):
    id: int
    name: str
    type: str
    status: str
    quota: str


class CopilotAutomation(BaseModel):
    id: int
    title: str
    schedule: str
    lastRun: str
    active: bool


class CopilotSuggestion(BaseModel):
    id: int
    prompt: str
    tag: str


class PaletteCommand(BaseModel):
    id: int
    label: str
    shortcut: str
    category: str


class LibraryBook(BaseModel):
    id: int
    isbn: str
    title: str
    author: str
    category: str
    copies: int
    available: int
    overdue: bool | None = None


class BookIssue(BaseModel):
    id: int
    book: str
    student: str
    issued: str
    due: str
    status: str


class TransportRoute(BaseModel):
    id: int
    name: str
    busId: str
    driver: str
    stops: int
    students: int
    status: str


class Bus(BaseModel):
    id: int
    name: str
    plate: str
    route: str
    capacity: int
    occupied: int
    status: str


class ClassroomItem(BaseModel):
    id: int
    title: str
    subject: str
    className: str
    teacher: str
    nextLesson: str
    students: int


class LessonResource(BaseModel):
    id: int
    type: str
    title: str


class LessonDetail(BaseModel):
    id: int
    title: str
    subject: str
    className: str
    duration: str
    topics: list[str]
    resources: list[LessonResource]
    homework: str


class NotificationItem(BaseModel):
    id: int
    title: str
    body: str
    kind: str
    time: str
    read: bool
    to: str | None = None


class ChatFile(BaseModel):
    id: int
    name: str
    sharedBy: str
    size: str
    when: str
