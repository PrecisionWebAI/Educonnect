from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import LeaveApplicationItem, StaffLeaveRow

router = APIRouter()

_can_read = RequirePermission("leave.read")


@router.get("/applications", response_model=list[LeaveApplicationItem])
def read_leave_applications(
    student_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Student leave applications, newest first (`student_id` narrows to one student)."""
    return service.list_leave_applications(session=session, student_id=student_id)


@router.get("/staff-requests", response_model=list[StaffLeaveRow])
def read_staff_leave_requests(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Staff leave requests, newest first."""
    return service.list_staff_leave(session=session)
