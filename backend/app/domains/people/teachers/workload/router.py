"""The workload tab's API: the school's rule, one person's week, its analytics.

Mount order inside this router mirrors the hub's rule: the fixed paths
(`/analytics`, `/rules`) are declared before `/{teacher_id}/…`, so FastAPI never
tries to read "analytics" as a UUID.

There is deliberately **no `GET /teachers/workload`** here. The matrix is the
hub's read - it is built from the directory's own people, and moving it would
have changed a URL the screen already uses. This sub-router owns the four things
the matrix cannot answer: the capacity rule, one person's week, the duties on
their file and the counts above the table.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission
from app.domains.people.staff.models import Employee

from ..profile.service import require_employee
from . import service
from .schemas import (
    StaffDutyCreate,
    StaffDutyRead,
    StaffWeekRead,
    WorkloadAnalytics,
    WorkloadRuleRead,
    WorkloadRuleWrite,
)

router = APIRouter()

_can_view = RequirePermission("teachers.view_workload")
#: A narrower right than reading the matrix: setting "a full week is 24 periods"
#: and handing out duties is the office's decision about everybody's time.
_can_manage = RequirePermission("teachers.manage_workload")


def _employee(session: Session, employee_id: UUID, user) -> Employee:
    """The person, if this caller may see them - `404` otherwise."""
    return require_employee(session, employee_id, user)


# --- the tiles and the rule ------------------------------------------------


@router.get("/analytics", response_model=WorkloadAnalytics)
def read_workload_analytics(
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """The tiles above the matrix: average load, overloads, department split.

    Counted on the server from the same rows the table shows, so a filtered or
    paged table cannot change the numbers above it.
    """
    return service.analytics(session)


@router.get("/rules", response_model=WorkloadRuleRead)
def read_workload_rule(
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """What a full week is, for the capacity dialog to open with.

    Readable by anyone who may read the matrix: the percentage on the bar is a
    share of this number, and a reader who cannot see the denominator is being
    shown a figure they cannot check.
    """
    return service.read_rule(session)


@router.put("/rules", response_model=WorkloadRuleRead)
def save_workload_rule(
    payload: WorkloadRuleWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Set the school's full week and its two thresholds. One row, upserted."""
    return service.set_rule(session, payload, current_user)


# --- one person's week -----------------------------------------------------


@router.get("/{teacher_id}/week", response_model=StaffWeekRead)
def read_staff_week(
    teacher_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """The grid: every day, the periods in it, and the duties beside them."""
    return service.staff_week(session, teacher_id, current_user)


@router.get("/{teacher_id}/duties", response_model=list[StaffDutyRead])
def read_staff_duties(
    teacher_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """This person's duties, Monday first - the list the drawer edits."""
    employee = _employee(session, teacher_id, current_user)
    return service.duty_reads(session, employee.id)


@router.post(
    "/{teacher_id}/duties",
    response_model=StaffDutyRead,
    status_code=http.HTTP_201_CREATED,
)
def add_staff_duty(
    teacher_id: UUID,
    payload: StaffDutyCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Add a duty. `409` when it is already on the file, `409` for a leaver."""
    employee = _employee(session, teacher_id, current_user)
    return service.add_duty(session, employee, payload, current_user)


@router.delete("/{teacher_id}/duties/{duty_id}", status_code=http.HTTP_204_NO_CONTENT)
def remove_staff_duty(
    teacher_id: UUID,
    duty_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Remove a duty. The row id is looked up **within this employee** (`404`)."""
    employee = _employee(session, teacher_id, current_user)
    service.remove_duty(session, employee, duty_id, current_user)
