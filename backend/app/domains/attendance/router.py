from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    AttendanceBulkCreate,
    AttendanceRecordRead,
    IrregularStudentRead,
    LeaveSyncRowRead,
)

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


@router.get("", response_model=list[AttendanceRecordRead])
def read_all_attendance(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """
    List all attendance records with pagination.
    """
    return service.get_all_attendance(session=session, skip=skip, limit=limit)


@router.get("/irregular", response_model=list[IrregularStudentRead])
def read_irregular_students(session: Session = Depends(get_session)):
    return [
        IrregularStudentRead(
            id=1,
            name="A. Verma",
            className="8A",
            absences=12,
            pattern="Mon + Fri absences",
            risk="High",
        ),
        IrregularStudentRead(
            id=2,
            name="R. Singh",
            className="9C",
            absences=9,
            pattern="Post-lunch absences",
            risk="Medium",
        ),
        IrregularStudentRead(
            id=3,
            name="S. Das",
            className="7B",
            absences=4,
            pattern="Scattered",
            risk="Low",
        ),
    ]


@router.get("/leave-sync", response_model=list[LeaveSyncRowRead])
def read_leave_sync(session: Session = Depends(get_session)):
    return [
        LeaveSyncRowRead(
            id=1,
            student="A. Verma",
            className="8A",
            from_date="Aug 29",
            days=2,
            autoMarked="Approved leave",
            status="Synced",
        ),
        LeaveSyncRowRead(
            id=2,
            student="M. Rao",
            className="10B",
            from_date="Sep 1",
            days=1,
            autoMarked="Awaiting approval",
            status="Pending",
        ),
        LeaveSyncRowRead(
            id=3,
            student="P. Gupta",
            className="6A",
            from_date="Aug 25",
            days=3,
            autoMarked="Teacher override",
            status="Overridden",
        ),
    ]
