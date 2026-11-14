"""The Teachers & Staff screen's API.

Order matters: the fixed paths (`/summary`, `/workload`, `/performance`) are
declared before `/{teacher_id}`, or FastAPI would try to read "summary" as a
UUID. Guards are per-route: reading the directory, looking at a load, and adding
a profile are three different rights.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .profile.schemas import AuditRead
from .schemas import (
    StaffProfile,
    StaffSummary,
    TeacherCreate,
    TeacherRead,
    WorkloadMatrixRow,
)
from .staff_attendance import service as attendance_service
from .staff_attendance.schemas import StaffMonthRead
from .workload import service as workload_service
from .workload.schemas import StaffWeekRead

router = APIRouter()

_can_read = RequirePermission("teachers.read")
_can_view_workload = RequirePermission("teachers.view_workload")
_can_create = RequirePermission("teachers.create")
#: Reading who changed what is a narrower right than reading the directory: the
#: audit feed names every edited profile in the school.
_can_audit = RequirePermission("teachers.audit_read")

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


@router.get("/audit", response_model=list[AuditRead])
def read_staff_audit(
    employee_id: UUID | None = Query(
        default=None, description="Only this person's lines."
    ),
    section: str | None = Query(
        default=None, description="employment / qualification / document / kyc …"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user=Depends(_can_audit),
):
    """Who changed what on a staff profile, newest first.

    Append-only: there is no route that edits or deletes a line, the way the
    employment history is corrected by adding the next event. Restricted to the
    roles that may read it (`teachers.audit_read`) - the feed names every profile
    in the school, so the directory right is not enough.
    """
    return service.staff_audit(
        session, employee_id=employee_id, section=section, limit=limit, offset=offset
    )


# --- the caller's own view --------------------------------------------------
#
# Phase 9: a teacher-only account gets "my" reads instead of the directory. Each of
# these is the same service call the office makes, with the employee id taken from the
# token rather than from the URL - so a teacher cannot reach a colleague by guessing an
# id, and the office routes keep their own (narrower) permissions. `teachers.read` is
# the only right needed: reading your own week is not "viewing the workload matrix".


@router.get("/me", response_model=TeacherRead)
def read_me(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The caller's own directory row (`404` for an account with no staff record)."""
    return service.get_own(session=session, user=current_user)


@router.get("/me/week", response_model=StaffWeekRead)
def read_my_week(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The caller's own teaching week, from the timetable.

    Deliberately **not** guarded by `teachers.view_workload`: that right says "read
    the school's load matrix", and a person reading their own Monday is a different
    question - the same distinction `scope.may_upload_documents` draws for papers.
    """
    employee = service.own_employee(session, current_user)
    return workload_service.staff_week(session, employee.id, current_user)


@router.get("/me/attendance", response_model=StaffMonthRead)
def read_my_attendance(
    month: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The caller's own month in the staff register (`YYYY-MM`, defaults to today's).

    `staff_attendance.read` belongs to the office because it reads **everybody's**
    register; a person reading their own month does not need it. The service still
    applies its own scope check, which is what keeps this honest.
    """
    employee = service.own_employee(session, current_user)
    return attendance_service.month(
        session,
        employee.id,
        month or date.today().strftime("%Y-%m"),
        current_user,
    )


@router.get("/{teacher_id}/profile", response_model=StaffProfile)
def read_teacher_profile(
    teacher_id: UUID,
    reveal: bool = Query(
        default=False,
        description=(
            "Show full Aadhaar / PAN / bank numbers. Needs `teachers.view_kyc`, "
            "and the reveal is written to the staff audit trail."
        ),
    ),
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """One person's profile: the post, the roll facts and the lists.

    One call, not six: the drawer opens them together, and a teacher asking for a
    colleague's profile gets `404` - same rule as the row above. The KYC block is
    masked unless `reveal=true` **and** the caller holds `teachers.view_kyc`.
    """
    return service.teacher_profile(
        session=session, teacher_id=teacher_id, user=current_user, reveal=reveal
    )


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
