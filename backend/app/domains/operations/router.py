from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session

from .schemas import (
    BookIssue,
    Bus,
    ChatFile,
    ClassroomItem,
    CopilotAutomation,
    CopilotSuggestion,
    DataQualityRow,
    EducationReportRow,
    GatewayStatus,
    LeaveApplicationItem,
    LessonDetail,
    LessonResource,
    LibraryBook,
    MeetingItem,
    NotificationItem,
    PaletteCommand,
    ReportCard,
    SchoolInfo,
    SecurityLog,
    SettingUser,
    StaffLeaveRow,
    TicketItem,
    TransportRoute,
)

router = APIRouter()


# Leave
@router.get("/leave/applications", response_model=list[LeaveApplicationItem])
def read_leave_applications(session: Session = Depends(get_session)):
    return [
        LeaveApplicationItem(
            id=1,
            type="Medical",
            student="Aarav Mehta",
            className="10-A",
            from_date="2026/09/05",
            to_date="2026/09/06",
            days=2,
            reason="Fever",
            status="Pending",
            submittedAt="2h ago",
        ),
        LeaveApplicationItem(
            id=2,
            type="Personal",
            student="Diya Sharma",
            className="10-A",
            from_date="2026/09/10",
            to_date="2026/09/10",
            days=1,
            reason="Family function",
            status="Approved",
            submittedAt="Yesterday",
        ),
    ]


@router.get("/leave/staff-requests", response_model=list[StaffLeaveRow])
def read_staff_leave_requests(session: Session = Depends(get_session)):
    return [
        StaffLeaveRow(
            id=1,
            name="P. Iyer",
            role="Teacher",
            type="Casual",
            from_date="Sep 4",
            days=1,
            balance=6,
            status="Pending",
        ),
        StaffLeaveRow(
            id=2,
            name="S. Bose",
            role="Staff",
            type="Sick",
            from_date="Aug 28",
            days=3,
            balance=4,
            status="Approved",
        ),
        StaffLeaveRow(
            id=3,
            name="K. Nair",
            role="Teacher",
            type="Earned",
            from_date="Oct 10",
            days=5,
            balance=9,
            status="Rejected",
        ),
    ]


# Meetings
@router.get("/meetings", response_model=list[MeetingItem])
def read_meetings(session: Session = Depends(get_session)):
    return [
        MeetingItem(
            id=1,
            title="PTM - Class 10",
            with_whom="H. Patel",
            date="2026/08/28",
            time="4 PM",
            room="Hall A",
            type="Scheduled",
        ),
        MeetingItem(
            id=2,
            title="Science Exhibit Planning",
            with_whom="Staff Team",
            date="2026/09/04",
            time="11 AM",
            room="Lab-2",
            type="Pending",
        ),
        MeetingItem(
            id=3,
            title="Board Review",
            with_whom="Principal",
            date="2026/09/10",
            time="2 PM",
            room="Office",
            type="Done",
        ),
    ]


# Tickets
@router.get("/tickets", response_model=list[TicketItem])
def read_tickets(session: Session = Depends(get_session)):
    return [
        TicketItem(
            id=1,
            subject="Printer not working in Rm-201",
            category="IT",
            priority="High",
            status="In Progress",
            reporter="P. Menon",
            assignee="Tech Desk",
            updated="1h",
        ),
        TicketItem(
            id=2,
            subject="Fee receipt not generated",
            category="Accounts",
            priority="Medium",
            status="Open",
            reporter="N. Joshi",
            assignee="Finance",
            updated="3h",
        ),
        TicketItem(
            id=3,
            subject="AC cooling issue in Hall A",
            category="Facility",
            priority="Medium",
            status="In Progress",
            reporter="S. Kapoor",
            assignee="Maintenance",
            updated="Yesterday",
        ),
    ]


# Reports
@router.get("/reports/cards", response_model=list[ReportCard])
def read_report_cards(session: Session = Depends(get_session)):
    return [
        ReportCard(
            id=1,
            title="Fee Collection",
            metric="Collected vs Billed",
            value="92.4%",
            trend="+3.1% vs last term",
            tone="green",
        ),
        ReportCard(
            id=2,
            title="Attendance Health",
            metric="Avg daily attendance",
            value="94.1%",
            trend="-0.8% vs last month",
            tone="amber",
        ),
        ReportCard(
            id=3,
            title="Exam Performance",
            metric="Average score",
            value="71.8%",
            trend="+2.4% vs last exam",
            tone="teal",
        ),
        ReportCard(
            id=4,
            title="Fee Defaulter Rate",
            metric="Overdue accounts",
            value="7.6%",
            trend="+1.2% vs last term",
            tone="red",
        ),
    ]


@router.get("/reports/data-quality", response_model=list[DataQualityRow])
def read_data_quality(session: Session = Depends(get_session)):
    return [
        DataQualityRow(
            id=1,
            area="Student records",
            score=98,
            issue="3 profiles missing guardian phone",
            status="Healthy",
        ),
        DataQualityRow(
            id=2,
            area="Fee ledger",
            score=91,
            issue="12 receipts pending reconciliation",
            status="Attention",
        ),
        DataQualityRow(
            id=3,
            area="Attendance logs",
            score=96,
            issue="2 backdated entries flagged",
            status="Healthy",
        ),
        DataQualityRow(
            id=4,
            area="Exam marks entry",
            score=62,
            issue="8A-B term marks incomplete",
            status="Critical",
        ),
    ]


@router.get("/reports/education", response_model=list[EducationReportRow])
def read_education_reports(session: Session = Depends(get_session)):
    return [
        EducationReportRow(
            id=1,
            metric="Pass rate",
            className="School-wide",
            value="91.4%",
            trend="+2.2% vs last term",
        ),
        EducationReportRow(
            id=2,
            metric="Subject avg — Maths",
            className="9C",
            value="64%",
            trend="-3% — needs remedial",
        ),
        EducationReportRow(
            id=3,
            metric="Top-performing subject",
            className="10B",
            value="Science (82%)",
            trend="Stable",
        ),
        EducationReportRow(
            id=4,
            metric="Students at risk",
            className="8A",
            value="3",
            trend="+1 vs last month",
        ),
    ]


# Settings
@router.get("/settings/users", response_model=list[SettingUser])
def read_setting_users(session: Session = Depends(get_session)):
    return [
        SettingUser(
            id=1,
            name="R. Sharma",
            email="r.sharma@school.edu",
            role="Admin",
            status="Active",
        ),
        SettingUser(
            id=2,
            name="P. Iyer",
            email="p.iyer@school.edu",
            role="Teacher",
            status="Active",
        ),
        SettingUser(
            id=3,
            name="M. Khan",
            email="m.khan@school.edu",
            role="Accountant",
            status="Active",
        ),
        SettingUser(
            id=4,
            name="S. Bose",
            email="s.bose@school.edu",
            role="Staff",
            status="Invited",
        ),
        SettingUser(
            id=5,
            name="K. Nair",
            email="k.nair@school.edu",
            role="Staff",
            status="Disabled",
        ),
    ]


@router.get("/settings/school-info", response_model=list[SchoolInfo])
def read_school_info(session: Session = Depends(get_session)):
    return [
        SchoolInfo(id=1, label="School name", value="Educonnect Public School"),
        SchoolInfo(id=2, label="Affiliation", value="CBSE — 1130456"),
        SchoolInfo(id=3, label="Academic session", value="2026-27"),
        SchoolInfo(id=4, label="Address", value="Sector 12, Pune, Maharashtra"),
        SchoolInfo(id=5, label="Contact", value="+91 98200 11223"),
    ]


@router.get("/settings/security-logs", response_model=list[SecurityLog])
def read_security_logs(session: Session = Depends(get_session)):
    return [
        SecurityLog(
            id=1,
            event="Password changed",
            user="r.sharma@school.edu",
            when="Today, 09:12",
        ),
        SecurityLog(
            id=2,
            event="New device sign-in",
            user="p.iyer@school.edu",
            when="Yesterday, 17:40",
        ),
        SecurityLog(
            id=3,
            event="Role updated to Accountant",
            user="m.khan@school.edu",
            when="Aug 28",
        ),
        SecurityLog(
            id=4,
            event="Failed login attempts (5)",
            user="k.nair@school.edu",
            when="Aug 26",
        ),
    ]


@router.get("/settings/gateways", response_model=list[GatewayStatus])
def read_gateways(session: Session = Depends(get_session)):
    return [
        GatewayStatus(
            id=1,
            name="WhatsApp Business",
            type="Messaging",
            status="Connected",
            quota="4,210 / 10,000 today",
        ),
        GatewayStatus(
            id=2,
            name="SMS Gateway",
            type="Messaging",
            status="Connected",
            quota="1,050 / 5,000 today",
        ),
        GatewayStatus(
            id=3,
            name="Razorpay",
            type="Payments",
            status="Degraded",
            quota="UPI slow — monitoring",
        ),
        GatewayStatus(
            id=4,
            name="Email (SMTP)",
            type="Messaging",
            status="Connected",
            quota="820 / 8,000 today",
        ),
    ]


# Copilot
@router.get("/copilot/automations", response_model=list[CopilotAutomation])
def read_copilot_automations(session: Session = Depends(get_session)):
    return [
        CopilotAutomation(
            id=1,
            title="Daily attendance digest to class teachers",
            schedule="Every day 08:00",
            lastRun="Today, 08:00",
            active=True,
        ),
        CopilotAutomation(
            id=2,
            title="Fee reminder for overdue accounts",
            schedule="Every Monday 10:00",
            lastRun="Aug 31",
            active=True,
        ),
        CopilotAutomation(
            id=3,
            title="Weekly homework submission summary",
            schedule="Every Friday 16:00",
            lastRun="Aug 29",
            active=True,
        ),
        CopilotAutomation(
            id=4,
            title="Low-stock alert for library",
            schedule="Monthly, 1st",
            lastRun="Aug 1",
            active=False,
        ),
    ]


@router.get("/copilot/suggestions", response_model=list[CopilotSuggestion])
def read_copilot_suggestions(session: Session = Depends(get_session)):
    return [
        CopilotSuggestion(
            id=1, prompt="Summarise today's attendance gaps by class", tag="Attendance"
        ),
        CopilotSuggestion(
            id=2, prompt="Draft a fee reminder for defaulters", tag="Finance"
        ),
        CopilotSuggestion(
            id=3, prompt="Generate a revision worksheet for 8A Science", tag="Academics"
        ),
        CopilotSuggestion(
            id=4, prompt="Which students need counselling this week?", tag="Wellbeing"
        ),
    ]


@router.get("/copilot/commands", response_model=list[PaletteCommand])
def read_palette_commands(session: Session = Depends(get_session)):
    return [
        PaletteCommand(
            id=1, label="Mark attendance", shortcut="G A", category="Navigate"
        ),
        PaletteCommand(
            id=2, label="Raise a ticket", shortcut="G T", category="Navigate"
        ),
        PaletteCommand(id=3, label="Collect fee", shortcut="G F", category="Navigate"),
        PaletteCommand(id=4, label="Summarise today", shortcut="⌘ ⇧ S", category="AI"),
        PaletteCommand(
            id=5, label="Draft fee reminder", shortcut="⌘ ⇧ F", category="AI"
        ),
    ]


# Library
@router.get("/library/books", response_model=list[LibraryBook])
def read_library_books(session: Session = Depends(get_session)):
    return [
        LibraryBook(
            id=1,
            isbn="978-0141036144",
            title="1984",
            author="George Orwell",
            category="Fiction",
            copies=12,
            available=8,
        ),
        LibraryBook(
            id=2,
            isbn="978-0061120084",
            title="To Kill a Mockingbird",
            author="Harper Lee",
            category="Fiction",
            copies=10,
            available=4,
        ),
        LibraryBook(
            id=3,
            isbn="978-8126521195",
            title="Wings of Fire",
            author="A.P.J. Abdul Kalam",
            category="Biography",
            copies=15,
            available=12,
        ),
        LibraryBook(
            id=4,
            isbn="978-8172234980",
            title="Discovery of India",
            author="Jawaharlal Nehru",
            category="History",
            copies=6,
            available=2,
        ),
        LibraryBook(
            id=5,
            isbn="978-0140283332",
            title="A Brief History of Time",
            author="Stephen Hawking",
            category="Science",
            copies=8,
            available=5,
        ),
    ]


@router.get("/library/issues", response_model=list[BookIssue])
def read_book_issues(session: Session = Depends(get_session)):
    return [
        BookIssue(
            id=1,
            book="1984",
            student="Aarav Mehta",
            issued="2026-08-20",
            due="2026-09-03",
            status="Overdue",
        ),
        BookIssue(
            id=2,
            book="Wings of Fire",
            student="Ishita Rao",
            issued="2026-08-27",
            due="2026-09-10",
            status="Borrowed",
        ),
        BookIssue(
            id=3,
            book="Discovery of India",
            student="Ananya Das",
            issued="2026-08-28",
            due="2026-09-11",
            status="Borrowed",
        ),
        BookIssue(
            id=4,
            book="1984",
            student="Rohan Gupta",
            issued="2026-08-15",
            due="2026-08-29",
            status="Overdue",
        ),
    ]


# Transport
@router.get("/transport/routes", response_model=list[TransportRoute])
def read_transport_routes(session: Session = Depends(get_session)):
    return [
        TransportRoute(
            id=1,
            name="Route A North",
            busId="B-01",
            driver="R. Sharma",
            stops=8,
            students=45,
            status="Active",
        ),
        TransportRoute(
            id=2,
            name="Route B East",
            busId="B-02",
            driver="S. Verma",
            stops=6,
            students=38,
            status="Active",
        ),
        TransportRoute(
            id=3,
            name="Route C South",
            busId="B-03",
            driver="M. Khan",
            stops=7,
            students=40,
            status="Idle",
        ),
        TransportRoute(
            id=4,
            name="Route D West",
            busId="B-04",
            driver="A. Singh",
            stops=5,
            students=32,
            status="Active",
        ),
    ]


@router.get("/transport/buses", response_model=list[Bus])
def read_buses(session: Session = Depends(get_session)):
    return [
        Bus(
            id=1,
            name="B-01",
            plate="MH-01-AB-1234",
            route="Route A North",
            capacity=50,
            occupied=45,
            status="En route",
        ),
        Bus(
            id=2,
            name="B-02",
            plate="MH-01-CD-5678",
            route="Route B East",
            capacity=45,
            occupied=38,
            status="En route",
        ),
        Bus(
            id=3,
            name="B-03",
            plate="MH-01-EF-9012",
            route="Route C South",
            capacity=50,
            occupied=20,
            status="Parked",
        ),
        Bus(
            id=4,
            name="B-04",
            plate="MH-01-GH-3456",
            route="Route D West",
            capacity=40,
            occupied=32,
            status="Service",
        ),
    ]


# Classroom
@router.get("/classroom/classes", response_model=list[ClassroomItem])
def read_classrooms(session: Session = Depends(get_session)):
    return [
        ClassroomItem(
            id=1,
            title="Physics - Class 10A",
            subject="Physics",
            className="10-A",
            teacher="P. Menon",
            nextLesson="Electricity - Ohm law",
            students=42,
        ),
        ClassroomItem(
            id=2,
            title="Mathematics - Class 10A",
            subject="Mathematics",
            className="10-A",
            teacher="M. Iyer",
            nextLesson="Trigonometry - Ratios",
            students=42,
        ),
        ClassroomItem(
            id=3,
            title="English - Class 9B",
            subject="English",
            className="9-B",
            teacher="S. Das",
            nextLesson="Essay writing",
            students=38,
        ),
    ]


@router.get("/classroom/lesson-detail", response_model=LessonDetail)
def read_lesson_detail(session: Session = Depends(get_session)):
    return LessonDetail(
        id=1,
        title="Ohm Law and Circuits",
        subject="Physics",
        className="10-A",
        duration="45 min",
        topics=["Current and voltage", "Resistance", "Ohm law", "Series circuits"],
        resources=[
            LessonResource(id=1, type="Video", title="Introduction to circuits"),
            LessonResource(id=2, type="PDF", title="Ohm law notes"),
            LessonResource(id=3, type="Quiz", title="Quick check - 5 questions"),
        ],
        homework="Solve numericals 1-10 from the worksheet.",
    )


# Notifications
@router.get("/notifications", response_model=list[NotificationItem])
def read_notifications(session: Session = Depends(get_session)):
    return [
        NotificationItem(
            id=1,
            kind="Attendance",
            title="Diya absent",
            body="Periods 2-3 physical",
            time="10m",
            read=False,
            to="Teacher",
        ),
        NotificationItem(
            id=2,
            kind="Homework",
            title="Hw reminder",
            body="Trig sheet due tomorrow",
            time="35m",
            read=True,
            to="Teacher",
        ),
    ]


@router.post("/notifications/mark-read")
def mark_notifications_read():
    return {"status": "ok"}


# Chat files
@router.get("/chat/files", response_model=list[ChatFile])
def read_chat_files(session: Session = Depends(get_session)):
    return [
        ChatFile(
            id=1,
            name="8A-science-worksheet.pdf",
            sharedBy="P. Iyer",
            size="1.2 MB",
            when="2h ago",
        ),
        ChatFile(
            id=2,
            name="fee-structure-2026.xlsx",
            sharedBy="M. Khan",
            size="480 KB",
            when="Yesterday",
        ),
        ChatFile(
            id=3,
            name="excursion-permission-slip.pdf",
            sharedBy="R. Sharma",
            size="310 KB",
            when="Aug 30",
        ),
    ]
