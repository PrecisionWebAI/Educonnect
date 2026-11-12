"""The Teachers & Staff screen's API.

Order matters: the fixed paths (`/summary`, `/workload`, `/performance`) are
declared before `/{teacher_id}`, or FastAPI would try to read "summary" as a
UUID. Guards are per-route: reading the directory, looking at a load, and adding
a profile are three different rights.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    StaffPerformance,
    StaffSummary,
    TeacherCreate,
    TeacherRead,
    WorkloadMatrixRow,
)

router = APIRouter()

_can_read = RequirePermission("teachers.read")
_can_view_workload = RequirePermission("teachers.view_workload")
_can_create = RequirePermission("teachers.create")

#: What the screen's status filter sends. A word outside this set is a bug in the
#: caller, and answering `422` is clearer than silently ignoring it.
StatusFilter = Literal["Active", "On Leave", "Inactive"]


@router.get("", response_model=list[TeacherRead])
def read_teachers(
    q: str | None = Query(
        default=None, description="Name, employee code, department, email or phone."
    ),
    department: str | None = None,
    status: StatusFilter | None = None,
    skip: int = 0,
    limit: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The staff directory, filtered and scoped on the server.

    `limit` is optional on purpose: the screen pages in the browser and the tiles
    above it count the whole school, so a default cap here would quietly hide
    staff. A teacher-only account gets its own row - see `scope`.
    """
    return service.get_teachers(
        session=session,
        user=current_user,
        q=q,
        department=department,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TeacherRead, status_code=http.HTTP_201_CREATED)
def create_teacher(
    teacher_in: TeacherCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_create),
):
    """Add a teacher profile for a login that already exists."""
    teacher = service.create_teacher(session=session, teacher_in=teacher_in)
    return service.get_teacher(session=session, teacher_id=teacher.id)


@router.get("/summary", response_model=StaffSummary)
def read_staff_summary(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The tiles above the directory, counted over the whole teaching roll."""
    return service.staff_summary(session=session)


@router.get("/workload", response_model=list[WorkloadMatrixRow])
def read_workload_matrix(
    session: Session = Depends(get_session),
    current_user=Depends(_can_view_workload),
):
    """Every teacher's periods against the timetable's own week."""
    return service.workload_matrix(session=session)


@router.get("/performance", response_model=list[StaffPerformance])
def read_staff_performance(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Ratings from the anonymous reviews - viewing is a read, not a workload right."""
    return service.staff_performance(session=session)


@router.get("/{teacher_id}", response_model=TeacherRead)
def read_teacher(
    teacher_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """One teacher, if this caller may see them (`404` otherwise, not `403`)."""
    return service.get_teacher(
        session=session, teacher_id=teacher_id, user=current_user
    )
