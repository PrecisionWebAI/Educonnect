from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import register as register_service
from . import service
from .models import AttendanceRecord
from .schemas import (
    AttendanceBulkCreate,
    AttendanceRecordRead,
    AttentionRowRead,
    ClosedDayRead,
    IrregularStudentRead,
    LeaveSyncRowRead,
    RegisterRead,
    SectionSummaryRead,
    SectionTrendRead,
)

router = APIRouter()


def _as_read(
    session: Session, records: list[AttendanceRecord]
) -> list[AttendanceRecordRead]:
    """The save answers with the same shape the reads use (one row per child)."""
    return [service.build_record_read(session, record) for record in records]


@router.post(
    "/bulk",
    response_model=list[AttendanceRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def mark_attendance_bulk(
    bulk_data: AttendanceBulkCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.mark")),
):
    """Save a whole class-section's register for one day.

    Saving the same day twice **updates** it (one row per child/day/subject), and every
    status change leaves an audit row naming who made it. A closed day (Sunday, a
    holiday) is refused with `409` naming the day.
    """
    from app.domains.academic.classroom.academics.models import Section
    from app.domains.auth.service import AuthorizationService

    # The class comes from the section, so the caller names the section and the
    # scope check resolves the class it belongs to.
    section = session.get(Section, bulk_data.section_id)
    class_id = section.class_id if section else None
    subject_id = bulk_data.subject_id

    if not AuthorizationService.can(
        current_user,
        "attendance.mark",
        session=session,
        class_id=class_id,
        subject_id=subject_id,
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to mark attendance for this scope."
        )

    saved = register_service.save_register(session, bulk_data, user=current_user)
    return _as_read(session, saved)


@router.get(
    "/class/{class_id}/section/{section_id}", response_model=list[AttendanceRecordRead]
)
def read_attendance_by_class(
    class_id: UUID,
    section_id: UUID,
    target_date: date,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    Fetch the attendance records for a specific date (to load the attendance register).

    `class_id` stays in the path for the existing callers, but the lookup is by
    section - the class is `section.class_id`.
    """
    return service.get_attendance_by_section_and_date(
        session=session,
        section_id=section_id,
        target_date=target_date,
    )


@router.get("/student/{student_id}", response_model=list[AttendanceRecordRead])
def read_attendance_by_student(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    Fetch the attendance history for a single student.
    """
    return service.get_attendance_by_student(session=session, student_id=student_id)


@router.get("", response_model=list[AttendanceRecordRead])
def read_all_attendance(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    List all attendance records with pagination.
    """
    return service.get_all_attendance(session=session, skip=skip, limit=limit)


@router.get("/irregular", response_model=list[IrregularStudentRead])
def read_irregular_students(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return service.list_irregular(session=session)


@router.get("/leave-sync", response_model=list[LeaveSyncRowRead])
def read_leave_sync(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    return service.list_leave_sync(session=session)


# ---------------------------------------------------------------------------
# The register the Attendance tab actually draws (Phase 2)
#
# `?date=`, `?from=&to=` are the words the UI already uses; the parameters are
# named `on_date`/`from_date` here because `date` is also a type.
# ---------------------------------------------------------------------------


@router.get("/section/{section_id}", response_model=RegisterRead)
def read_section_register(
    section_id: UUID,
    on_date: date = Query(alias="date"),
    subject_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """The class-section's roll for one day: everyone, marked or not.

    This is the read the screen was missing - it used to draw a roster from the
    student list and then forget to ask what had been saved. `closed_reason` says when
    the day is a Sunday or a holiday, and a child on approved leave comes back as
    `leave` with the request's id.
    """
    return register_service.register(
        session=session, section_id=section_id, on_date=on_date, subject_id=subject_id
    )


@router.get("/section/{section_id}/summary", response_model=SectionSummaryRead)
def read_section_summary(
    section_id: UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    subject_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Per-student present/absent/leave days and percentage over a range."""
    return register_service.section_summary(
        session=session,
        section_id=section_id,
        start=from_date,
        end=to_date,
        subject_id=subject_id,
    )


@router.get("/section/{section_id}/trend", response_model=SectionTrendRead)
def read_section_trend(
    section_id: UUID,
    days: int = Query(default=7, ge=1, le=90),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """The section's present percentage per open day (holidays and Sundays skipped)."""
    return register_service.section_trend(
        session=session, section_id=section_id, days=days
    )


@router.get("/section/{section_id}/attention", response_model=list[AttentionRowRead])
def read_section_attention(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Children below the school's threshold, or absent too many open days in a row."""
    return register_service.section_attention(session=session, section_id=section_id)


@router.get("/closed-days", response_model=list[ClosedDayRead])
def read_closed_days(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """Sundays and holidays in a range - what the register's date picker greys out.

    The reason is the words the screen prints ("Sunday", "Diwali break"), so the
    calendar and the toolbar cannot explain the same closed day differently.
    """
    return register_service.closed_days(session=session, start=from_date, end=to_date)
