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
    return service.operations_board(session=session)


@router.get("/class-attendance", response_model=list[ClassAttendanceStat])
def read_class_attendance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return service.class_attendance(session=session)


@router.get("/subject-perf", response_model=list[SubjectPerf])
def read_subject_perf(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("analytics.read")),
):
    return service.subject_perf(session=session)


@router.get("/today-classes", response_model=list[TodayClassItem])
def read_today_classes(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("timetable.read")),
):
    return service.today_classes(session=session)


@router.get("/homework-status", response_model=list[HomeworkStatusItem])
def read_homework_status(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return service.homework_status(session=session)


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
    return service.meeting_reminders(session=session)


@router.get("/student-portal", response_model=StudentPortalData)
def read_student_portal(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.student_portal(session=session, user=current_user)


@router.get("/parent-data", response_model=list[ChildSummary])
def read_parent_data(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.parent_data(session=session, user=current_user)


@router.get("/accountant-summary", response_model=AccountantSummary)
def read_accountant_summary(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("dashboard.read")),
):
    return service.accountant_summary(session=session)
