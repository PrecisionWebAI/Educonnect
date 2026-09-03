from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import AttendanceBulkCreate, AttendanceRecordRead

router = APIRouter()

StaffRoles = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director, RoleEnum.teacher]
)


@router.post(
    "/bulk",
    response_model=list[AttendanceRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def mark_attendance_bulk(
    bulk_data: AttendanceBulkCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Mark attendance for an entire class/section on a specific date.
    Teachers and Admins can do this.
    """
    return service.bulk_create_attendance(session=session, bulk_data=bulk_data)


@router.get(
    "/class/{class_id}/section/{section_id}", response_model=list[AttendanceRecordRead]
)
def read_attendance_by_class(
    class_id: int,
    section_id: int,
    target_date: date,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
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
    # Could protect this so only the student, their parent, or staff can view
):
    """
    Fetch the attendance history for a single student.
    """
    return service.get_attendance_by_student(session=session, student_id=student_id)
