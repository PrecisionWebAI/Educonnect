"""Queries behind the Dashboard screens that used to answer with fixtures.

The main board returned invented KPIs ("1,284 students", "93.1% attendance",
"17 pending approvals"), a fixed attendance trend, class report, upcoming list
and three notices. All of that is now read from the real tables:

  * Total Students        - `studentprofile`
  * Attendance Today      - `attendancerecord` (today's present / total)
  * Fees Collected        - `feetransaction`
  * Pending Approvals     - `leaverequest` (Pending)
  * Open Tickets          - `supportticket` (not Resolved)
  * Notices               - `notification` (the signed-in user's own)

The trend / class-report / upcoming panels have no source table yet, so they
return empty lists instead of invented rows - an empty chart beats a fake one.
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.finance.models import FeeTransaction
from app.domains.operations.models import LeaveRequest, Notification, SupportTicket
from app.domains.students.models import StudentProfile
from app.domains.users.models import User

from .schemas import (
    AccountantSummary,
    ApprovalItem,
    DashboardData,
    Kpi,
    NoticeItem,
    SubjectLeaveItem,
)


def _count(session: Session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


def _fmt_dt(dt) -> str:
    return dt.strftime("%Y/%m/%d %H:%M") if dt else ""


def dashboard_data(session: Session, user: User) -> DashboardData:
    total_students = _count(session, StudentProfile)

    today = date.today()
    total_today = session.exec(
        select(func.count()).select_from(AttendanceRecord).where(
            AttendanceRecord.date == today
        )
    ).one()
    present_today = session.exec(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.date == today,
            AttendanceRecord.status.in_(
                [AttendanceStatus.present, AttendanceStatus.half_day]
            ),
        )
    ).one()
    attendance_pct = (present_today / total_today * 100) if total_today else 0.0

    fees_collected = session.exec(
        select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0.0))
    ).one()

    pending_approvals = session.exec(
        select(func.count())
        .select_from(LeaveRequest)
        .where(LeaveRequest.status == "Pending")
    ).one()

    open_tickets = session.exec(
        select(func.count())
        .select_from(SupportTicket)
        .where(SupportTicket.status != "Resolved")
    ).one()

    notices = [
        NoticeItem(title=n.title, body=n.body, time=_fmt_dt(n.created_at))
        for n in session.exec(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
        ).all()
    ]

    return DashboardData(
        greeting="Good morning",
        kpis=[
            Kpi(label="Total Students", value=str(total_students), delta=0.0, icon="students"),
            Kpi(label="Attendance Today", value=f"{attendance_pct:.1f}%", delta=0.0, icon="attendance"),
            Kpi(label="Fees Collected", value=f"₹{fees_collected:,.0f}", delta=0.0, icon="fees"),
            Kpi(label="Pending Approvals", value=str(pending_approvals), delta=0.0, icon="approvals"),
            Kpi(label="Open Tickets", value=str(open_tickets), delta=0.0, icon="tickets"),
        ],
        attendanceTrend=[],
        classReport=[],
        upcoming=[],
        notices=notices,
    )


def approvals(session: Session) -> list[ApprovalItem]:
    """Pending leave requests + open tickets become the approvals feed."""
    items: list[ApprovalItem] = []
    for request in session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.status == "Pending", LeaveRequest.student_id != None)  # noqa: E711
        .order_by(LeaveRequest.created_at.desc())
    ).all():
        requester = session.get(User, request.requester_user_id)
        name = requester.full_name if requester else "—"
        items.append(
            ApprovalItem(
                id=request.id or 0,
                kind="Leave",
                summary=f"{name} - {request.leave_type} leave",
                requester=name,
                time=_fmt_dt(request.created_at),
            )
        )
    for ticket in session.exec(
        select(SupportTicket)
        .where(SupportTicket.status == "Open")
        .order_by(SupportTicket.created_at.desc())
    ).all():
        reporter = session.get(User, ticket.reporter_user_id)
        name = reporter.full_name if reporter else "—"
        items.append(
            ApprovalItem(
                id=ticket.id or 0,
                kind="Ticket",
                summary=ticket.subject,
                requester=name,
                time=_fmt_dt(ticket.created_at),
            )
        )
    return items


def subject_leaves(session: Session) -> list[SubjectLeaveItem]:
    """Student leaves shown against the subject/class leave board."""
    items: list[SubjectLeaveItem] = []
    for request in session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.student_id != None)  # noqa: E711
        .order_by(LeaveRequest.from_date.desc())
    ).all():
        student = session.get(StudentProfile, request.student_id)
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        items.append(
            SubjectLeaveItem(
                id=request.id or 0,
                student=user.full_name if user else "—",
                type=request.leave_type,
                range=f"{request.from_date.strftime('%d %b')} - {request.to_date.strftime('%d %b')}",
            )
        )
    return items


def accountant_summary(session: Session) -> AccountantSummary:
    """Fees and payroll figures for the accountant's board."""
    today = date.today()
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)

    collected_today = session.exec(
        select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0.0)).where(
            FeeTransaction.date == today
        )
    ).one()
    collected_month = session.exec(
        select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0.0)).where(
            FeeTransaction.date >= month_start, FeeTransaction.date < next_month
        )
    ).one()

    pending_dues = session.exec(
        select(func.count()).select_from(SupportTicket).where(
            SupportTicket.category == "Accounts"
        )
    ).one()

    from app.domains.salary.models import SalaryPayment

    payroll_processing = session.exec(
        select(func.count())
        .select_from(SalaryPayment)
        .where(SalaryPayment.status == "Processing")
    ).one()

    return AccountantSummary(
        collectedToday=f"₹{collected_today:,.0f}",
        collectedMonth=f"₹{collected_month:,.0f}",
        pendingDues=pending_dues,
        payrollRun=f"Processing ({payroll_processing})" if payroll_processing else "None in progress",
    )

