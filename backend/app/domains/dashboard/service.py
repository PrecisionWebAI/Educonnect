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


def operations_board(session: Session) -> "OperationsBoard":
    """Live operations counts + upcoming meetings."""
    from app.domains.operations.models import Meeting
    from app.domains.teachers.models import TeacherAssignment, TeacherProfile

    from .schemas import OperationsBoard

    teachers_total = session.exec(select(func.count()).select_from(TeacherProfile)).one()
    running_classes = session.exec(
        select(func.count(func.distinct(TeacherAssignment.section_id)))
    ).one()
    upcoming = [
        {"title": m.title, "when": f"{m.meeting_date.strftime('%d %b')} {m.meeting_time}"}
        for m in session.exec(select(Meeting).order_by(Meeting.meeting_date)).all()
    ]
    return OperationsBoard(
        runningClasses=int(running_classes),
        presentTeachers=0,  # no staff-attendance table yet
        teachersTotal=int(teachers_total),
        substitutes=0,  # no substitution table yet
        upcomingEvents=upcoming,
    )


def class_attendance(session: Session) -> list["ClassAttendanceStat"]:
    """Today's present/total per class-section, from real attendance rows."""
    from app.domains.academics.models import Classroom, Section

    from .schemas import ClassAttendanceStat

    today = date.today()
    totals = session.exec(
        select(
            AttendanceRecord.classroom_id,
            AttendanceRecord.section_id,
            func.count(),
        )
        .where(AttendanceRecord.date == today)
        .group_by(AttendanceRecord.classroom_id, AttendanceRecord.section_id)
    ).all()
    presents = {
        (row[0], row[1]): int(row[2])
        for row in session.exec(
            select(
                AttendanceRecord.classroom_id,
                AttendanceRecord.section_id,
                func.count(),
            )
            .where(
                AttendanceRecord.date == today,
                AttendanceRecord.status.in_(
                    [AttendanceStatus.present, AttendanceStatus.half_day]
                ),
            )
            .group_by(AttendanceRecord.classroom_id, AttendanceRecord.section_id)
        ).all()
    }

    result: list[ClassAttendanceStat] = []
    for index, (classroom_id, section_id, total) in enumerate(totals, start=1):
        classroom = session.get(Classroom, classroom_id)
        section = session.get(Section, section_id) if section_id else None
        name = classroom.name if classroom else ""
        if section:
            name = f"{name}-{section.name}"
        result.append(
            ClassAttendanceStat(
                id=index,
                name=name,
                present=presents.get((classroom_id, section_id), 0),
                total=int(total),
            )
        )
    return result


def subject_perf(session: Session) -> list["SubjectPerf"]:
    """No exam-marks table exists yet, so there is no real subject performance."""
    return []


def today_classes(session: Session) -> list["TodayClassItem"]:
    """Today's periods, from the timetable."""
    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.timetable.models import TimetablePeriod

    from .schemas import TodayClassItem

    today_name = date.today().strftime("%A").lower()
    periods = session.exec(
        select(TimetablePeriod).order_by(TimetablePeriod.start_time)
    ).all()

    items: list[TodayClassItem] = []
    for period in periods:
        if period.day_of_week.value != today_name:
            continue
        classroom = session.get(Classroom, period.classroom_id)
        section = session.get(Section, period.section_id) if period.section_id else None
        subject = session.get(Subject, period.subject_id)
        class_name = classroom.name if classroom else ""
        if section:
            class_name = f"{class_name}-{section.name}"
        items.append(
            TodayClassItem(
                id=period.id or 0,
                subject=subject.name if subject else "",
                className=class_name,
                period=f"{period.start_time.strftime('%H:%M')}",
                room=period.room or "",
            )
        )
    return items


def homework_status(session: Session) -> list["HomeworkStatusItem"]:
    """Assigned vs submitted per class+subject, from homework tables."""
    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.homework.models import HomeworkAssignment, HomeworkSubmission
    from app.domains.students.models import StudentProfile

    from .schemas import HomeworkStatusItem

    items: list[HomeworkStatusItem] = []
    for homework in session.exec(select(HomeworkAssignment)).all():
        classroom = session.get(Classroom, homework.classroom_id)
        section = session.get(Section, homework.section_id) if homework.section_id else None
        subject = session.get(Subject, homework.subject_id)
        class_name = classroom.name if classroom else ""
        if section:
            class_name = f"{class_name}-{section.name}"
        assigned = session.exec(
            select(func.count())
            .select_from(StudentProfile)
            .where(StudentProfile.section_id == homework.section_id)
        ).one()
        submitted = session.exec(
            select(func.count())
            .select_from(HomeworkSubmission)
            .where(HomeworkSubmission.homework_id == homework.id)
        ).one()
        items.append(
            HomeworkStatusItem(
                className=class_name,
                subject=subject.name if subject else "",
                assigned=int(assigned),
                submitted=int(submitted),
            )
        )
    return items


def meeting_reminders(session: Session) -> list["MeetingReminderItem"]:
    """Meetings shown as reminders (the person + time)."""
    from app.domains.operations.models import Meeting

    from .schemas import MeetingReminderItem

    return [
        MeetingReminderItem(
            id=m.id or 0,
            parent=m.with_whom,
            time=f"{m.meeting_date.strftime('%d %b')} {m.meeting_time}",
        )
        for m in session.exec(select(Meeting).order_by(Meeting.meeting_date)).all()
    ]


def student_portal(session: Session, user: User) -> "StudentPortalData":
    """The signed-in student's own portal, from their real rows."""
    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.homework.models import HomeworkAssignment, HomeworkSubmission
    from app.domains.operations.models import LeaveRequest, SupportTicket
    from app.domains.timetable.models import TimetablePeriod

    from .schemas import StudentHomeworkItem, StudentPortalData, TodayClassItem

    student = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    ).first()
    if student is None:
        return StudentPortalData(
            name="", className="", section="", attendancePct=0, avgMarks=0, rank=0,
            todaySchedule=[], homework=[], recentGrades=[], leaves=[], tickets=[],
        )

    classroom = session.get(Classroom, student.classroom_id) if student.classroom_id else None
    section = session.get(Section, student.section_id) if student.section_id else None

    total_att = session.exec(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(AttendanceRecord.student_id == student.id)
    ).one()
    present_att = session.exec(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.status.in_(
                [AttendanceStatus.present, AttendanceStatus.half_day]
            ),
        )
    ).one()
    attendance_pct = (present_att / total_att * 100) if total_att else 0.0

    today_name = date.today().strftime("%A").lower()
    schedule: list[TodayClassItem] = []
    for period in session.exec(
        select(TimetablePeriod).order_by(TimetablePeriod.start_time)
    ).all():
        if period.day_of_week.value != today_name or period.section_id != student.section_id:
            continue
        subject = session.get(Subject, period.subject_id)
        class_name = (classroom.name if classroom else "") + (f"-{section.name}" if section else "")
        schedule.append(
            TodayClassItem(
                id=period.id or 0,
                subject=subject.name if subject else "",
                className=class_name,
                period=f"{period.start_time.strftime('%H:%M')}",
                room=period.room or "",
            )
        )

    homework: list[StudentHomeworkItem] = []
    for hw in session.exec(
        select(HomeworkAssignment).where(
            HomeworkAssignment.classroom_id == student.classroom_id,
            (HomeworkAssignment.section_id == student.section_id)
            | (HomeworkAssignment.section_id == None),  # noqa: E711
        )
    ).all():
        subject = session.get(Subject, hw.subject_id)
        done = (
            session.exec(
                select(HomeworkSubmission).where(
                    HomeworkSubmission.homework_id == hw.id,
                    HomeworkSubmission.student_id == student.id,
                )
            ).first()
            is not None
        )
        homework.append(
            StudentHomeworkItem(
                id=hw.id or 0,
                title=hw.title,
                subject=subject.name if subject else "",
                due=hw.due_date.strftime("%d %b"),
                done=done,
            )
        )

    leaves = [
        {
            "id": r.id or 0,
            "type": r.leave_type,
            "range": f"{r.from_date.strftime('%d %b')} - {r.to_date.strftime('%d %b')}",
            "status": r.status,
        }
        for r in session.exec(
            select(LeaveRequest).where(LeaveRequest.student_id == student.id)
        ).all()
    ]
    tickets = [
        {"id": t.id or 0, "title": t.subject, "status": t.status}
        for t in session.exec(
            select(SupportTicket).where(SupportTicket.reporter_user_id == user.id)
        ).all()
    ]

    return StudentPortalData(
        name=user.full_name,
        className=classroom.name if classroom else "",
        section=section.name if section else "",
        attendancePct=round(attendance_pct, 1),
        avgMarks=0,  # no exam-marks table yet
        rank=0,  # no exam-marks table yet
        todaySchedule=schedule,
        homework=homework,
        recentGrades=[],  # no exam-marks table yet
        leaves=leaves,
        tickets=tickets,
    )


def parent_data(session: Session, user: User) -> list["ChildSummary"]:
    """The signed-in parent's children, from their real student rows."""
    from app.domains.academics.models import Classroom, Section
    from app.domains.homework.models import HomeworkAssignment, HomeworkSubmission
    from app.domains.students.models import StudentParentRelationship

    from .schemas import ChildSummary

    relationships = session.exec(
        select(StudentParentRelationship).where(
            StudentParentRelationship.parent_user_id == user.id
        )
    ).all()

    result: list[ChildSummary] = []
    for relationship in relationships:
        student = session.get(StudentProfile, relationship.student_id)
        if student is None:
            continue
        child_user = session.get(User, student.user_id)
        classroom = session.get(Classroom, student.classroom_id) if student.classroom_id else None
        section = session.get(Section, student.section_id) if student.section_id else None

        total_att = session.exec(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(AttendanceRecord.student_id == student.id)
        ).one()
        present_att = session.exec(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.status.in_(
                    [AttendanceStatus.present, AttendanceStatus.half_day]
                ),
            )
        ).one()
        attendance_pct = (present_att / total_att * 100) if total_att else 0.0

        assigned = session.exec(
            select(HomeworkAssignment.id).where(
                HomeworkAssignment.classroom_id == student.classroom_id,
                (HomeworkAssignment.section_id == student.section_id)
                | (HomeworkAssignment.section_id == None),  # noqa: E711
            )
        ).all()
        submitted = session.exec(
            select(HomeworkSubmission.homework_id).where(
                HomeworkSubmission.student_id == student.id,
                HomeworkSubmission.homework_id.in_(assigned),
            )
        ).all()
        pending_hw = max(0, len(assigned) - len(set(submitted)))

        result.append(
            ChildSummary(
                id=student.id or 0,
                name=child_user.full_name if child_user else "",
                className=classroom.name if classroom else "",
                section=section.name if section else "",
                attendancePct=round(attendance_pct, 1),
                avgMarks=0,  # no exam-marks table yet
                feeStatus="",  # no fee-default mapping yet
                pendingHw=pending_hw,
            )
        )
    return result





