from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AttendanceBulkCreate,
    AttendanceRecordRead,
    IrregularStudentRead,
    LeaveSyncRowRead,
)

router = APIRouter()

# Removed StaffRoles


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
    """
    Mark attendance for an entire class/section on a specific date.
    Teachers and Admins can do this.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    # Extract scopes from the body
    class_id = bulk_data.classroom_id
    subject_id = bulk_data.subject_id

    # Additional explicit scope validation since body params aren't extracted by RequirePermission yet
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

    return service.bulk_create_attendance(
        session=session, bulk_data=bulk_data, current_user=current_user
    )


@router.get(
    "/class/{class_id}/section/{section_id}", response_model=list[AttendanceRecordRead]
)
def read_attendance_by_class(
    class_id: int,
    section_id: int,
    target_date: date,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("attendance.read")),
):
    """
    Fetch the attendance records for a specific date (to load the attendance register).
    """
    return service.get_attendance_by_class_and_date(
        session=session,
        class_id=class_id,
        section_id=section_id,
        target_date=target_date,
    )


@router.get("/student/{student_id}", response_model=list[AttendanceRecordRead])
def read_attendance_by_student(
    student_id: int,
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
def read_irregular_students(session: Session = Depends(get_session)):
    return service.list_irregular(session=session)


@router.get("/leave-sync", response_model=list[LeaveSyncRowRead])
def read_leave_sync(session: Session = Depends(get_session)):
    return service.list_leave_sync(session=session)
