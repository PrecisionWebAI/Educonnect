from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AccountantSummary,
    ApprovalItem,
    ChildSummary,
    ClassAttendanceStat,
    DashboardData,
    HomeworkStatusItem,
    MeetingReminderItem,
    OperationsBoard,
    RecentGradeItem,
    StudentHomeworkItem,
    StudentPortalData,
    SubjectLeaveItem,
    SubjectPerf,
    TodayClassItem,
)

router = APIRouter()


@router.get("", response_model=DashboardData)
def read_dashboard(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.dashboard_data(session=session, user=current_user)


@router.get("/approvals", response_model=list[ApprovalItem])
def read_approvals(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.approvals(session=session)


@router.get("/operations", response_model=OperationsBoard)
def read_operations_board(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return OperationsBoard(
        runningClasses=18,
        presentTeachers=21,
        teachersTotal=24,
        substitutes=3,
        upcomingEvents=[
            {"title": "PTM - Class 10", "when": "Today 4 PM"},
            {"title": "Science Exhibit", "when": "Fri 9 AM"},
        ],
    )


@router.get("/class-attendance", response_model=list[ClassAttendanceStat])
def read_class_attendance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return [
        ClassAttendanceStat(id=1, name="10-A", present=40, total=42),
        ClassAttendanceStat(id=2, name="10-B", present=38, total=40),
        ClassAttendanceStat(id=3, name="9-A", present=41, total=45),
        ClassAttendanceStat(id=4, name="9-B", present=33, total=38),
        ClassAttendanceStat(id=5, name="7-C", present=33, total=35),
    ]


@router.get("/subject-perf", response_model=list[SubjectPerf])
def read_subject_perf(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("analytics.read")),
):
    return [
        SubjectPerf(
            subject="Mathematics",
            className="10-A",
            average=88,
            weakTopic="Trigonometry",
        ),
        SubjectPerf(
            subject="Physics", className="10-A", average=82, weakTopic="Electricity"
        ),
        SubjectPerf(
            subject="Chemistry", className="10-B", average=84, weakTopic="Organic"
        ),
        SubjectPerf(
            subject="English", className="9-B", average=79, weakTopic="Grammar"
        ),
    ]


@router.get("/today-classes", response_model=list[TodayClassItem])
def read_today_classes(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    return [
        TodayClassItem(
            id=1, subject="Mathematics", className="10-A", period="P1", room="Rm-201"
        ),
        TodayClassItem(
            id=2, subject="Physics", className="10-A", period="P2", room="Lab-3"
        ),
        TodayClassItem(
            id=3, subject="Chemistry", className="10-B", period="P4", room="Lab-1"
        ),
    ]


@router.get("/homework-status", response_model=list[HomeworkStatusItem])
def read_homework_status(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return [
        HomeworkStatusItem(
            className="10-A", subject="Mathematics", assigned=42, submitted=38
        ),
        HomeworkStatusItem(
            className="10-A", subject="Physics", assigned=42, submitted=34
        ),
        HomeworkStatusItem(
            className="10-B", subject="Chemistry", assigned=40, submitted=34
        ),
    ]


@router.get("/subject-leaves", response_model=list[SubjectLeaveItem])
def read_subject_leaves(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("leave.read")),
):
    return service.subject_leaves(session=session)


@router.get("/meeting-reminders", response_model=list[MeetingReminderItem])
def read_meeting_reminders(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("ptm.read")),
):
    return [
        MeetingReminderItem(id=1, parent="H. Patel", time="Today 3:30 PM"),
        MeetingReminderItem(id=2, parent="V. Singh", time="Fri 11 AM"),
    ]


@router.get("/student-portal", response_model=StudentPortalData)
def read_student_portal(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return StudentPortalData(
        name="Aarav Mehta",
        className="10",
        section="A",
        attendancePct=94,
        avgMarks=88,
        rank=4,
        todaySchedule=[
            TodayClassItem(
                id=1,
                subject="Mathematics",
                className="10-A",
                period="P1",
                room="Rm-201",
            ),
            TodayClassItem(
                id=2, subject="Physics", className="10-A", period="P2", room="Lab-3"
            ),
            TodayClassItem(
                id=3, subject="English", className="10-A", period="P5", room="Rm-105"
            ),
        ],
        homework=[
            StudentHomeworkItem(
                id=1,
                title="Trigonometry worksheet",
                subject="Mathematics",
                due="Today",
                done=False,
            ),
            StudentHomeworkItem(
                id=2,
                title="Electricity circuit lab",
                subject="Physics",
                due="Tomorrow",
                done=False,
            ),
            StudentHomeworkItem(
                id=3,
                title="Essay - My School",
                subject="English",
                due="Completed",
                done=True,
            ),
        ],
        recentGrades=[
            RecentGradeItem(subject="Mathematics", score=88, max=100),
            RecentGradeItem(subject="Physics", score=82, max=100),
            RecentGradeItem(subject="English", score=79, max=100),
            RecentGradeItem(subject="Chemistry", score=91, max=100),
        ],
        leaves=[
            {"id": 1, "type": "Medical", "range": "19-21 Aug", "status": "Approved"},
            {"id": 2, "type": "OD", "range": "2 Aug", "status": "Rejected"},
            {"id": 3, "type": "Medical", "range": "26 Aug", "status": "Pending"},
        ],
        tickets=[
            {"id": 1, "title": "Marks dispute - Physics", "status": "In Progress"},
            {"id": 2, "title": "Library fine query", "status": "Resolved"},
        ],
    )


@router.get("/parent-data", response_model=list[ChildSummary])
def read_parent_data(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return [
        ChildSummary(
            id=1,
            name="Aarav Mehta",
            className="10",
            section="A",
            attendancePct=94,
            avgMarks=88,
            feeStatus="On track",
            pendingHw=2,
        ),
        ChildSummary(
            id=2,
            name="Diya Sharma",
            className="10",
            section="A",
            attendancePct=88,
            avgMarks=81,
            feeStatus="Due",
            pendingHw=1,
        ),
    ]


@router.get("/accountant-summary", response_model=AccountantSummary)
def read_accountant_summary(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.accountant_summary(session=session)
