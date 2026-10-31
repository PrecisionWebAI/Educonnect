from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
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
def read_leave_applications(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("leave.read")),
):
    return service.list_leave_applications(session=session, student_id=student_id)


@router.get("/leave/staff-requests", response_model=list[StaffLeaveRow])
def read_staff_leave_requests(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("leave.read")),
):
    return service.list_staff_leave(session=session)


# Meetings
@router.get("/meetings", response_model=list[MeetingItem])
def read_meetings(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("ptm.read")),
):
    return service.list_meetings(session=session)


# Tickets
@router.get("/tickets", response_model=list[TicketItem])
def read_tickets(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("messages.read")),
):
    return service.list_tickets(session=session)


# Reports
@router.get("/reports/cards", response_model=list[ReportCard])
def read_report_cards(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    return service.list_report_cards(session=session)


@router.get("/reports/data-quality", response_model=list[DataQualityRow])
def read_data_quality(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("analytics.read")),
):
    return service.list_data_quality(session=session)


@router.get("/reports/education", response_model=list[EducationReportRow])
def read_education_reports(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    return service.list_education_reports(session=session)


# Settings
@router.get("/settings/users", response_model=list[SettingUser])
def read_setting_users(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("settings.read")),
):
    return service.list_setting_users(session=session)


@router.get("/settings/school-info", response_model=list[SchoolInfo])
def read_school_info(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("settings.read")),
):
    return service.list_school_info(session=session, user=current_user)


@router.get("/settings/security-logs", response_model=list[SecurityLog])
def read_security_logs(session: Session = Depends(get_session)):
    return service.list_security_logs(session=session)


@router.get("/settings/gateways", response_model=list[GatewayStatus])
def read_gateways(session: Session = Depends(get_session)):
    return service.list_gateways(session=session)


# Copilot
@router.get("/copilot/automations", response_model=list[CopilotAutomation])
def read_copilot_automations(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("ai_copilot.use")),
):
    return service.list_copilot_automations(session=session)


@router.get("/copilot/suggestions", response_model=list[CopilotSuggestion])
def read_copilot_suggestions(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("ai_copilot.use")),
):
    return service.list_copilot_suggestions(session=session)


@router.get("/copilot/commands", response_model=list[PaletteCommand])
def read_palette_commands(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("ai_copilot.use")),
):
    return service.list_palette_commands(session=session)


# Library
@router.get("/library/books", response_model=list[LibraryBook])
def read_library_books(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("library.read")),
):
    return service.list_library_books(session=session)


@router.get("/library/issues", response_model=list[BookIssue])
def read_book_issues(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("library.read")),
):
    return service.list_library_issues(session=session)


# Transport
@router.get("/transport/routes", response_model=list[TransportRoute])
def read_transport_routes(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("transport.read")),
):
    return service.list_transport_routes(session=session)


@router.get("/transport/buses", response_model=list[Bus])
def read_buses(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("transport.read")),
):
    return service.list_buses(session=session)


# Classroom
@router.get("/classroom/classes", response_model=list[ClassroomItem])
def read_classrooms(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """The class-section-subject cards for this person, from `teacherassignment`.

    This endpoint used to return three invented cards ("Physics - Class 10A",
    "M. Iyer", 42 students). It now reads who actually teaches what: an admin-type
    role sees the whole school, a teacher sees their own classes.
    """
    return service.classroom_cards(session=session, user=current_user)


@router.get("/classroom/lesson-detail", response_model=LessonDetail)
def read_lesson_detail(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """The next lesson for the first class this person teaches.

    Composed from real rows: the timetable period, the class's content-library
    sources (chapters -> topics, sources -> resources) and its newest homework.
    """
    return service.lesson_detail(session=session, user=current_user)


# Notifications
@router.get("/notifications", response_model=list[NotificationItem])
def read_notifications(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("messages.read")),
):
    return service.list_notifications(session=session, user=current_user)


@router.post("/notifications/mark-read")
def mark_notifications_read(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("messages.read")),
):
    return service.mark_notifications_read(session=session, user=current_user)


# Chat files
@router.get("/chat/files", response_model=list[ChatFile])
def read_chat_files(session: Session = Depends(get_session)):
    return service.list_chat_files(session=session)
