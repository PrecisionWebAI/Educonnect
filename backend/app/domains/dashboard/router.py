from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session

from .schemas import (
    AccountantSummary,
    ApprovalItem,
    ChildSummary,
    ClassAttendanceStat,
    ClassReportItem,
    DashboardData,
    HomeworkStatusItem,
    Kpi,
    MeetingReminderItem,
    NoticeItem,
    OperationsBoard,
    PaperDraftItem,
    PaperReviewItem,
    QbHealthItem,
    RecentGradeItem,
    StudentHomeworkItem,
    StudentPortalData,
    SubjectLeaveItem,
    SubjectPerf,
    TodayClassItem,
    TrendItem,
    UpcomingItem,
)

router = APIRouter()


@router.get("", response_model=DashboardData)
def read_dashboard(session: Session = Depends(get_session)):
    return DashboardData(
        greeting="Good morning",
        kpis=[
            Kpi(label="Total Students", value="1,284", delta=4.2, icon="students"),
            Kpi(label="Attendance Today", value="93.1%", delta=1.8, icon="attendance"),
            Kpi(label="Avg. Marks (Term 1)", value="82.4%", delta=2.6, icon="marks"),
            Kpi(label="Fees Collected", value="48.2L", delta=12.4, icon="fees"),
            Kpi(label="Pending Approvals", value="17", delta=-5.0, icon="approvals"),
            Kpi(label="Open Tickets", value="23", delta=3.0, icon="tickets"),
        ],
        attendanceTrend=[
            TrendItem(label="Mon", value=92),
            TrendItem(label="Tue", value=95),
            TrendItem(label="Wed", value=94),
            TrendItem(label="Thu", value=98),
            TrendItem(label="Fri", value=96),
            TrendItem(label="Sat", value=98),
        ],
        classReport=[
            ClassReportItem(name="10-A", attending=97, marks=88),
            ClassReportItem(name="10-B", attending=94, marks=84),
            ClassReportItem(name="9-A", attending=96, marks=81),
            ClassReportItem(name="9-B", attending=91, marks=79),
            ClassReportItem(name="7-C", attending=95, marks=86),
        ],
        upcoming=[
            UpcomingItem(title="Term 1 Exams begin", when="22 Aug 2026", type="Exam"),
            UpcomingItem(
                title="Parent Teacher Meeting", when="28 Aug 2026", type="Meeting"
            ),
            UpcomingItem(
                title="Sports Day rehearsals", when="2 Sep 2026", type="Event"
            ),
        ],
        notices=[
            NoticeItem(
                title="Fee payment window opens",
                body="Term 2 fees can be paid online from next week.",
                time="2h ago",
            ),
            NoticeItem(
                title="Mid-term marks entry due",
                body="All subject teachers to complete grade entry by Friday.",
                time="5h ago",
            ),
            NoticeItem(
                title="Transport route D time change",
                body="Route D return timing moves to 4:30 PM.",
                time="Yesterday",
            ),
        ],
    )


@router.get("/approvals", response_model=list[ApprovalItem])
def read_approvals(session: Session = Depends(get_session)):
    return [
        ApprovalItem(
            id=1,
            kind="Leave",
            summary="Diya Sharma - Sick leave",
            requester="Diya",
            time="1h ago",
        ),
        ApprovalItem(
            id=2,
            kind="Fee waiver",
            summary="Sibling discount - S. Verma family",
            requester="S. Verma",
            time="3h ago",
        ),
        ApprovalItem(
            id=3,
            kind="Mark dispute",
            summary="Physics Term-1 recheck (74 to 79)",
            requester="Arjun",
            time="5h ago",
        ),
        ApprovalItem(
            id=4,
            kind="Paper approval",
            summary="Term-2 Physics paper draft",
            requester="P. Menon",
            time="Yesterday",
        ),
    ]


@router.get("/operations", response_model=OperationsBoard)
def read_operations_board(session: Session = Depends(get_session)):
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
def read_class_attendance(session: Session = Depends(get_session)):
    return [
        ClassAttendanceStat(id=1, name="10-A", present=40, total=42),
        ClassAttendanceStat(id=2, name="10-B", present=38, total=40),
        ClassAttendanceStat(id=3, name="9-A", present=41, total=45),
        ClassAttendanceStat(id=4, name="9-B", present=33, total=38),
        ClassAttendanceStat(id=5, name="7-C", present=33, total=35),
    ]


@router.get("/subject-perf", response_model=list[SubjectPerf])
def read_subject_perf(session: Session = Depends(get_session)):
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


@router.get("/qb-health", response_model=list[QbHealthItem])
def read_qb_health(session: Session = Depends(get_session)):
    return [
        QbHealthItem(subject="Mathematics", mcq=45, theory=12, flagged=False),
        QbHealthItem(subject="Physics", mcq=30, theory=8, flagged=True),
        QbHealthItem(subject="Chemistry", mcq=22, theory=6, flagged=False),
    ]


@router.get("/today-classes", response_model=list[TodayClassItem])
def read_today_classes(session: Session = Depends(get_session)):
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
def read_homework_status(session: Session = Depends(get_session)):
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
def read_subject_leaves(session: Session = Depends(get_session)):
    return [
        SubjectLeaveItem(
            id=1, student="Vivaan Patel", type="Medical", range="19-21 Aug"
        ),
        SubjectLeaveItem(id=2, student="Saanvi Gupta", type="OD", range="20 Aug"),
    ]


@router.get("/meeting-reminders", response_model=list[MeetingReminderItem])
def read_meeting_reminders(session: Session = Depends(get_session)):
    return [
        MeetingReminderItem(id=1, parent="H. Patel", time="Today 3:30 PM"),
        MeetingReminderItem(id=2, parent="V. Singh", time="Fri 11 AM"),
    ]


@router.get("/paper-drafts", response_model=list[PaperDraftItem])
def read_paper_drafts(session: Session = Depends(get_session)):
    return [
        PaperDraftItem(
            id=1, subject="Physics", title="Term-2 Unit Test", status="Draft"
        ),
        PaperDraftItem(
            id=2, subject="Physics", title="MCQ Bank - Current", status="Pending edit"
        ),
    ]


@router.get("/student-portal", response_model=StudentPortalData)
def read_student_portal(session: Session = Depends(get_session)):
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
def read_parent_data(session: Session = Depends(get_session)):
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
def read_accountant_summary(session: Session = Depends(get_session)):
    return AccountantSummary(
        collectedToday="46,200",
        collectedMonth="48.2L",
        pendingDues=23,
        payrollRun="Processing (86%)",
    )


@router.get("/paper-reviews", response_model=list[PaperReviewItem])
def read_paper_reviews(session: Session = Depends(get_session)):
    return [
        PaperReviewItem(
            id=1,
            title="Term-2 Physics draft",
            subject="Physics",
            author="P. Menon",
            due="Today",
        ),
        PaperReviewItem(
            id=2,
            title="Chemistry MCQs",
            subject="Chemistry",
            author="R. Khanna",
            due="Tomorrow",
        ),
    ]
