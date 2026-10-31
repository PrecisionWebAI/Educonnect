"""Queries behind the Operations screens that used to answer with fixtures.

The Classroom screen is the first of them: `/operations/classroom/classes` and
`/operations/classroom/lesson-detail` returned invented cards ("Physics -
Class 10A", "M. Iyer", 42 students) and a fixed "Ohm Law and Circuits" lesson.
The school already stores all of it - who teaches what (`teacherassignment`),
when (`timetableperiod`), the roll (`studentprofile`), the newest homework
(`homeworkassignment`) and the content library (`examsource`) - so these
functions read those tables instead of making it up.
"""

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academics.models import Classroom, Section, Subject
from app.domains.auth.roles import has_role
from app.domains.exams.models import ExamSource, SourceType
from app.domains.homework.models import HomeworkAssignment
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import TeacherAssignment, TeacherProfile
from app.domains.timetable.models import TimetablePeriod
from app.domains.users.models import User

from .schemas import ClassroomItem, LessonDetail, LessonResource

#: Roles that look after the whole school, so their Classroom screen lists every
#: class instead of only the ones they teach themselves.
SCHOOL_WIDE_ROLES = ("system_admin", "school_admin", "principal", "vice_principal", "hod")

#: `examsource.source_type` -> the label the lesson card shows for a resource.
RESOURCE_LABELS: dict[str, str] = {
    SourceType.pdf.value: "PDF",
    SourceType.image.value: "Image",
    SourceType.url.value: "Link",
    SourceType.text.value: "Notes",
    SourceType.bank.value: "Question bank",
}


def _strength_by_section(session: Session) -> dict[int, int]:
    """{section_id: students} - the roll printed on every card."""
    rows = session.exec(
        select(StudentProfile.section_id, func.count()).group_by(
            StudentProfile.section_id
        )
    ).all()
    return {
        int(section_id): int(count)
        for section_id, count in rows
        if section_id is not None
    }


def _teaching_rows(
    session: Session, user: User
) -> list[tuple[TeacherAssignment, Classroom, Section, Subject, User]]:
    """The (assignment, class, section, subject, teacher) rows this person may see.

    A teacher sees only their own assignments; an admin-type role sees the whole
    school's, which is what the screen means by "all classes".
    """
    statement = (
        select(TeacherAssignment, Classroom, Section, Subject, User)
        .join(Classroom, TeacherAssignment.classroom_id == Classroom.id)
        .join(Section, TeacherAssignment.section_id == Section.id)
        .join(Subject, TeacherAssignment.subject_id == Subject.id)
        .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
        .join(User, TeacherProfile.user_id == User.id)
        .order_by(Classroom.level, Section.name, Subject.name)
    )
    if not has_role(user, *SCHOOL_WIDE_ROLES):
        profile = session.exec(
            select(TeacherProfile).where(TeacherProfile.user_id == user.id)
        ).first()
        if profile is None or profile.id is None:
            return []
        statement = statement.where(TeacherAssignment.teacher_id == profile.id)
    return list(session.exec(statement).all())


def _next_period(
    session: Session, section_id: int, subject_id: int
) -> TimetablePeriod | None:
    """The first period of the week for that subject in that section."""
    return session.exec(
        select(TimetablePeriod)
        .where(
            TimetablePeriod.section_id == section_id,
            TimetablePeriod.subject_id == subject_id,
        )
        .order_by(  # type: ignore[arg-type]
            TimetablePeriod.day_of_week, TimetablePeriod.start_time
        )
    ).first()


def _latest_homework(
    session: Session, section_id: int, subject_id: int
) -> HomeworkAssignment | None:
    return session.exec(
        select(HomeworkAssignment)
        .where(
            HomeworkAssignment.section_id == section_id,
            HomeworkAssignment.subject_id == subject_id,
        )
        .order_by(HomeworkAssignment.due_date.desc())  # type: ignore[attr-defined]
    ).first()


def classroom_cards(session: Session, user: User) -> list[ClassroomItem]:
    """One card per class-section-subject the person teaches."""
    strengths = _strength_by_section(session)
    cards: list[ClassroomItem] = []
    for assignment, classroom, section, subject, teacher_user in _teaching_rows(
        session, user
    ):
        period = _next_period(session, section.id, subject.id)  # type: ignore[arg-type]
        homework = _latest_homework(session, section.id, subject.id)  # type: ignore[arg-type]
        if period is not None:
            next_lesson = (
                f"{subject.name} · "
                f"{period.day_of_week.value.title()} {period.start_time:%H:%M}"
            )
            if period.room:
                next_lesson = f"{next_lesson} · {period.room}"
        elif homework is not None:
            next_lesson = homework.title
        else:
            next_lesson = "Not scheduled yet"
        cards.append(
            ClassroomItem(
                id=assignment.id or 0,
                title=f"{subject.name} - {classroom.name}-{section.name}",
                subject=subject.name,
                className=f"{classroom.name}-{section.name}",
                teacher=teacher_user.full_name,
                nextLesson=next_lesson,
                students=strengths.get(section.id, 0),  # type: ignore[arg-type]
            )
        )
    return cards


def lesson_detail(session: Session, user: User) -> LessonDetail:
    """The lesson for the first class the person teaches, from real rows."""
    rows = _teaching_rows(session, user)
    if not rows:
        # Nobody has been assigned to this person (or the school has no
        # assignments yet): an empty lesson beats an invented one.
        return LessonDetail(
            id=0,
            title="No lesson scheduled",
            subject="",
            className="",
            duration="",
            topics=[],
            resources=[],
            homework="No homework set yet",
        )

    _, classroom, section, subject, _ = rows[0]
    period = _next_period(session, section.id, subject.id)  # type: ignore[arg-type]
    homework = _latest_homework(session, section.id, subject.id)  # type: ignore[arg-type]
    sources = list(
        session.exec(
            select(ExamSource).where(
                ExamSource.classroom_id == classroom.id,
                ExamSource.subject_id == subject.id,
            )
        ).all()
    )

    # The chapters of the class's own library sources become the topic list.
    topics: list[str] = []
    for source in sources:
        for chapter in source.chapters or []:
            if chapter not in topics:
                topics.append(chapter)

    duration = ""
    if period is not None:
        minutes = (
            period.end_time.hour * 60
            + period.end_time.minute
            - period.start_time.hour * 60
            - period.start_time.minute
        )
        if minutes > 0:
            duration = f"{minutes} min"

    return LessonDetail(
        id=section.id or 0,
        title=f"{subject.name} - {classroom.name}-{section.name}",
        subject=subject.name,
        className=f"{classroom.name}-{section.name}",
        duration=duration,
        topics=topics[:6],
        resources=[
            LessonResource(
                id=source.id or 0,
                type=RESOURCE_LABELS.get(source.source_type.value, "Resource"),
                title=source.title,
            )
            for source in sources[:4]
        ],
        homework=homework.title if homework is not None else "No homework set yet",
    )


# ---------------------------------------------------------------------------
# Leave, tickets, library, notifications - the screens that used to be fixtures.
# ---------------------------------------------------------------------------


def _fmt_dt(dt) -> str:
    """A display timestamp for a row; empty string when the row has none."""
    return dt.strftime("%Y/%m/%d %H:%M") if dt else ""


def _class_label(session: Session, student: StudentProfile | None) -> str:
    if student is None:
        return ""
    classroom = session.get(Classroom, student.classroom_id) if student.classroom_id else None
    section = session.get(Section, student.section_id) if student.section_id else None
    name = classroom.name if classroom else ""
    return f"{name}-{section.name}" if section else name


def list_leave_applications(
    session: Session, student_id: int | None = None
) -> list["LeaveApplicationItem"]:
    """Student leave requests from `leaverequest` (staff leaves have no student)."""
    from .models import LeaveRequest
    from .schemas import LeaveApplicationItem

    statement = select(LeaveRequest).where(
        LeaveRequest.student_id != None  # noqa: E711
    )
    if student_id is not None:
        statement = statement.where(LeaveRequest.student_id == student_id)
    statement = statement.order_by(LeaveRequest.created_at.desc())

    items: list[LeaveApplicationItem] = []
    for request in session.exec(statement).all():
        student = session.get(StudentProfile, request.student_id)
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        items.append(
            LeaveApplicationItem(
                id=request.id or 0,
                student=user.full_name if user else "",
                className=_class_label(session, student),
                type=request.leave_type,
                from_date=request.from_date.strftime("%Y/%m/%d"),
                to_date=request.to_date.strftime("%Y/%m/%d"),
                reason=request.reason or "",
                days=request.days,
                status=request.status,
                submittedAt=_fmt_dt(request.created_at),
            )
        )
    return items


def list_staff_leave(session: Session) -> list["StaffLeaveRow"]:
    """Staff leave requests from `leaverequest` (student_id is NULL)."""
    from app.domains.auth.roles import primary_role_name

    from .models import LeaveRequest
    from .schemas import StaffLeaveRow

    statement = (
        select(LeaveRequest)
        .where(LeaveRequest.student_id == None)  # noqa: E711
        .order_by(LeaveRequest.created_at.desc())
    )

    items: list[StaffLeaveRow] = []
    for request in session.exec(statement).all():
        user = session.get(User, request.requester_user_id)
        items.append(
            StaffLeaveRow(
                id=request.id or 0,
                name=user.full_name if user else "",
                role=primary_role_name(session, request.requester_user_id) or "Staff",
                type=request.leave_type,
                from_date=request.from_date.strftime("%b %d"),
                days=request.days,
                balance=0,  # no leave-balance table yet
                status=request.status,
            )
        )
    return items


def list_tickets(session: Session) -> list["TicketItem"]:
    """Support tickets from `supportticket`."""
    from .models import SupportTicket
    from .schemas import TicketItem

    statement = select(SupportTicket).order_by(SupportTicket.updated_at.desc())
    items: list[TicketItem] = []
    for ticket in session.exec(statement).all():
        user = session.get(User, ticket.reporter_user_id)
        items.append(
            TicketItem(
                id=ticket.id or 0,
                subject=ticket.subject,
                category=ticket.category,
                priority=ticket.priority,
                status=ticket.status,
                reporter=user.full_name if user else "",
                assignee=ticket.assignee or "",
                updated=_fmt_dt(ticket.updated_at),
            )
        )
    return items


def list_library_books(session: Session) -> list["LibraryBook"]:
    """The catalogue from `librarybook`."""
    from .models import LibraryBook as LibraryBookModel
    from .schemas import LibraryBook

    statement = select(LibraryBookModel).order_by(LibraryBookModel.title)
    return [
        LibraryBook(
            id=book.id or 0,
            isbn=book.isbn,
            title=book.title,
            author=book.author,
            category=book.category,
            copies=book.copies,
            available=book.available,
            overdue=book.available < book.copies,
        )
        for book in session.exec(statement).all()
    ]


def list_library_issues(session: Session) -> list["BookIssue"]:
    """Issued books from `libraryissue`, joined to book + student names."""
    from .models import LibraryBook as LibraryBookModel
    from .models import LibraryIssue
    from .schemas import BookIssue

    statement = select(LibraryIssue).order_by(LibraryIssue.due_date)
    items: list[BookIssue] = []
    for issue in session.exec(statement).all():
        book = session.get(LibraryBookModel, issue.book_id)
        student = session.get(StudentProfile, issue.student_id) if issue.student_id else None
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        items.append(
            BookIssue(
                id=issue.id or 0,
                book=book.title if book else "",
                student=user.full_name if user else "",
                issued=issue.issued_date.strftime("%Y/%m/%d"),
                due=issue.due_date.strftime("%Y/%m/%d"),
                status=issue.status,
            )
        )
    return items


def list_notifications(session: Session, user: User) -> list["NotificationItem"]:
    """The current user's notifications from `notification`."""
    from .models import Notification
    from .schemas import NotificationItem

    statement = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
    )
    return [
        NotificationItem(
            id=n.id or 0,
            title=n.title,
            body=n.body,
            kind=n.kind,
            time=_fmt_dt(n.created_at),
            read=n.read,
            to=None,
        )
        for n in session.exec(statement).all()
    ]


def mark_notifications_read(session: Session, user: User) -> dict:
    """Mark every unread notification for the current user as read."""
    from .models import Notification

    statement = select(Notification).where(
        Notification.user_id == user.id, Notification.read == False  # noqa: E712
    )
    updated = 0
    for notification in session.exec(statement).all():
        notification.read = True
        session.add(notification)
        updated += 1
    session.commit()
    return {"status": "ok", "updated": updated}


def list_meetings(session: Session) -> list["MeetingItem"]:
    """Meetings from the `meeting` table."""
    from .models import Meeting
    from .schemas import MeetingItem

    return [
        MeetingItem(
            id=m.id or 0,
            title=m.title,
            with_whom=m.with_whom,
            date=m.meeting_date.strftime("%Y/%m/%d"),
            time=m.meeting_time,
            room=m.room or "",
            type=m.status,
        )
        for m in session.exec(select(Meeting).order_by(Meeting.meeting_date)).all()
    ]


def list_report_cards(session: Session) -> list["ReportCard"]:
    """Report cards from the `reportcard` table."""
    from .models import ReportCard as ReportCardModel
    from .schemas import ReportCard

    return [
        ReportCard(
            id=r.id or 0,
            title=r.title,
            metric=r.metric,
            value=r.value,
            trend=r.trend,
            tone=r.tone,
        )
        for r in session.exec(select(ReportCardModel)).all()
    ]


def list_data_quality(session: Session) -> list["DataQualityRow"]:
    """Data-quality rows from the `dataquality` table."""
    from .models import DataQuality
    from .schemas import DataQualityRow

    return [
        DataQualityRow(
            id=d.id or 0,
            area=d.area,
            score=d.score,
            issue=d.issue,
            status=d.status,
        )
        for d in session.exec(select(DataQuality)).all()
    ]


def list_education_reports(session: Session) -> list["EducationReportRow"]:
    """Education report rows from the `educationreport` table."""
    from .models import EducationReport
    from .schemas import EducationReportRow

    return [
        EducationReportRow(
            id=e.id or 0,
            metric=e.metric,
            className=e.class_name,
            value=e.value,
            trend=e.trend,
        )
        for e in session.exec(select(EducationReport)).all()
    ]


def list_setting_users(session: Session) -> list["SettingUser"]:
    """Settings > Users, from the real `user` table."""
    from app.domains.auth.roles import primary_role_name

    from .schemas import SettingUser

    return [
        SettingUser(
            id=u.id or 0,
            name=u.full_name,
            email=u.email,
            role=primary_role_name(session, u.id) or "Staff",
            status="Active" if u.is_active else "Disabled",
        )
        for u in session.exec(select(User).order_by(User.full_name)).all()
    ]


def list_school_info(session: Session, user: User) -> list["SchoolInfo"]:
    """Settings > School info, from the real `school` table."""
    from app.domains.schools.models import School

    from .schemas import SchoolInfo

    school = session.get(School, user.school_id) if user.school_id else None
    if school is None:
        return []
    return [
        SchoolInfo(id=1, label="School name", value=school.name),
        SchoolInfo(id=2, label="School code", value=school.code),
        SchoolInfo(id=3, label="Contact email", value=school.email),
        SchoolInfo(id=4, label="Phone", value=school.phone or ""),
        SchoolInfo(id=5, label="Address", value=school.address or ""),
    ]


def list_security_logs(session: Session) -> list["SecurityLog"]:
    """Security logs from the `securitylog` table."""
    from .models import SecurityLog as SecurityLogModel
    from .schemas import SecurityLog

    return [
        SecurityLog(
            id=s.id or 0,
            event=s.event,
            user=s.user,
            when=s.when,
        )
        for s in session.exec(select(SecurityLogModel)).all()
    ]


def list_gateways(session: Session) -> list["GatewayStatus"]:
    """Gateway statuses from the `gatewaystatus` table."""
    from .models import GatewayStatus as GatewayStatusModel
    from .schemas import GatewayStatus

    return [
        GatewayStatus(
            id=g.id or 0,
            name=g.name,
            type=g.type,
            status=g.status,
            quota=g.quota,
        )
        for g in session.exec(select(GatewayStatusModel)).all()
    ]


def list_copilot_automations(session: Session) -> list["CopilotAutomation"]:
    """Copilot automations from the `copilotautomation` table."""
    from .models import CopilotAutomation as CopilotAutomationModel
    from .schemas import CopilotAutomation

    return [
        CopilotAutomation(
            id=a.id or 0,
            title=a.title,
            schedule=a.schedule,
            lastRun=a.last_run,
            active=a.active,
        )
        for a in session.exec(select(CopilotAutomationModel)).all()
    ]


def list_copilot_suggestions(session: Session) -> list["CopilotSuggestion"]:
    """Copilot prompt suggestions from the `copilotsuggestion` table."""
    from .models import CopilotSuggestion as CopilotSuggestionModel
    from .schemas import CopilotSuggestion

    return [
        CopilotSuggestion(id=s.id or 0, prompt=s.prompt, tag=s.tag)
        for s in session.exec(select(CopilotSuggestionModel)).all()
    ]


def list_palette_commands(session: Session) -> list["PaletteCommand"]:
    """Command-palette entries from the `palettecommand` table."""
    from .models import PaletteCommand as PaletteCommandModel
    from .schemas import PaletteCommand

    return [
        PaletteCommand(
            id=p.id or 0,
            label=p.label,
            shortcut=p.shortcut,
            category=p.category,
        )
        for p in session.exec(select(PaletteCommandModel)).all()
    ]


def list_transport_routes(session: Session) -> list["TransportRoute"]:
    """Transport routes from the `transportroute` table."""
    from .models import TransportRoute as TransportRouteModel
    from .schemas import TransportRoute

    return [
        TransportRoute(
            id=r.id or 0,
            name=r.name,
            busId=r.bus_id,
            driver=r.driver,
            stops=r.stops,
            students=r.students,
            status=r.status,
        )
        for r in session.exec(select(TransportRouteModel)).all()
    ]


def list_buses(session: Session) -> list["Bus"]:
    """Buses from the `bus` table."""
    from .models import Bus as BusModel
    from .schemas import Bus

    return [
        Bus(
            id=b.id or 0,
            name=b.name,
            plate=b.plate,
            route=b.route,
            capacity=b.capacity,
            occupied=b.occupied,
            status=b.status,
        )
        for b in session.exec(select(BusModel)).all()
    ]


def list_chat_files(session: Session) -> list["ChatFile"]:
    """Shared chat files from the `chatfile` table."""
    from .models import ChatFile as ChatFileModel
    from .schemas import ChatFile

    return [
        ChatFile(
            id=f.id or 0,
            name=f.name,
            sharedBy=f.shared_by,
            size=f.size,
            when=f.when,
        )
        for f in session.exec(select(ChatFileModel)).all()
    ]



