from typing import Any

from pydantic import BaseModel


class Kpi(BaseModel):
    label: str
    value: str
    delta: float
    icon: str
    hint: str | None = None


class TrendItem(BaseModel):
    label: str
    value: float


class ClassReportItem(BaseModel):
    name: str
    attending: float
    marks: float


class UpcomingItem(BaseModel):
    title: str
    when: str
    type: str


class NoticeItem(BaseModel):
    title: str
    body: str
    time: str


class DashboardData(BaseModel):
    greeting: str
    kpis: list[Kpi]
    attendanceTrend: list[TrendItem]
    classReport: list[ClassReportItem]
    upcoming: list[UpcomingItem]
    notices: list[NoticeItem]


class ApprovalItem(BaseModel):
    id: int
    kind: str
    summary: str
    requester: str
    time: str


class OperationsBoard(BaseModel):
    runningClasses: int
    presentTeachers: int
    teachersTotal: int
    substitutes: int
    upcomingEvents: list[dict[str, str]]


class ClassAttendanceStat(BaseModel):
    id: int
    name: str
    present: int
    total: int


class SubjectPerf(BaseModel):
    subject: str
    className: str
    average: float
    weakTopic: str


class QbHealthItem(BaseModel):
    subject: str
    mcq: int
    theory: int
    flagged: bool


class PaperReviewItem(BaseModel):
    id: int
    title: str
    subject: str
    author: str
    due: str


class TodayClassItem(BaseModel):
    id: int
    subject: str
    className: str
    period: str
    room: str


class HomeworkStatusItem(BaseModel):
    className: str
    subject: str
    assigned: int
    submitted: int


class SubjectLeaveItem(BaseModel):
    id: int
    student: str
    type: str
    range: str


class MeetingReminderItem(BaseModel):
    id: int
    parent: str
    time: str


class PaperDraftItem(BaseModel):
    id: int
    subject: str
    title: str
    status: str


class StudentHomeworkItem(BaseModel):
    id: int
    title: str
    subject: str
    due: str
    done: bool


class RecentGradeItem(BaseModel):
    subject: str
    score: float
    max: float


class StudentPortalData(BaseModel):
    name: str
    className: str
    section: str
    attendancePct: float
    avgMarks: float
    rank: int
    todaySchedule: list[TodayClassItem]
    homework: list[StudentHomeworkItem]
    recentGrades: list[RecentGradeItem]
    leaves: list[dict[str, Any]]
    tickets: list[dict[str, Any]]


class ChildSummary(BaseModel):
    id: int
    name: str
    className: str
    section: str
    attendancePct: float
    avgMarks: float
    feeStatus: str
    pendingHw: int


class AccountantSummary(BaseModel):
    collectedToday: str
    collectedMonth: str
    pendingDues: int
    payrollRun: str
