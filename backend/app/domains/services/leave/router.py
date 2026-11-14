"""The leave API: both screens' reads, the workflow, and the school's policy.

Three groups of routes, and the fixed paths come first: `/policies`, `/balances`
and `/requests` are declared before anything that could swallow them, the same rule
`people/teachers/api.py` follows for its hub.

Two guards are deliberately *not* the obvious codename:

* **cancel** is guarded by `leave.read` and decided in the service, because the rule
  is "the person who filed it, or the office" - a single office codename on the
  route would either lock an applicant out of withdrawing their own request or hand
  every `leave.read` holder the right to cancel a colleague's;
* **deciding** your own request is refused in the service (`403`), because that is
  a property of the row, not of the caller's rights.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service, workflow
from .schemas import (
    LeaveApplicationItem,
    LeaveApplyIn,
    LeaveBalanceRow,
    LeaveBalancesRead,
    LeaveBalanceWrite,
    LeaveDecisionIn,
    LeavePoliciesWrite,
    LeavePolicyRead,
    LeaveRequestRead,
    LeaveTabRow,
    StaffLeaveRow,
    VisibleKinds,
)

#: The 0.10 tabs. `kind` is a filter the service applies **inside** the caller's
#: scope, so an unknown word is a `422` here rather than an ignored parameter.
KindFilter = Literal["staff", "student", "all"]

router = APIRouter()

_can_read = RequirePermission("leave.read")
#: Filing leave. A teacher holds this for **their own** request; the office may file
#: for somebody else, which `workflow._staff_target` checks.
_can_apply = RequirePermission("leave.create")
_can_approve = RequirePermission("leave.approve")
_can_reject = RequirePermission("leave.reject")
#: The school's leave types and their grants, and one person's override.
_can_policy = RequirePermission("leave.manage_policy")


# --- the school's policy ----------------------------------------------------


@router.get("/policies", response_model=list[LeavePolicyRead])
def read_policies(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every leave type the school grants, with its annual days.

    With no policy written yet this answers the **defaults** (`labels.DEFAULT_POLICIES`)
    rather than an empty list, so the apply form has something to offer on day one.
    """
    return service.policies_read(session)


@router.put("/policies", response_model=list[LeavePolicyRead])
def write_policies(
    payload: LeavePoliciesWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_can_policy),
):
    """Upsert leave types. Types not in the payload keep their row (`403` for a non-office role)."""
    return workflow.save_policies(session, payload, current_user)


@router.delete("/policies/{leave_type}", status_code=204)
def remove_policy(
    leave_type: str,
    session: Session = Depends(get_session),
    current_user=Depends(_can_policy),
):
    """Retire a leave type. `409` while requests still use it - set its days to 0 instead."""
    workflow.delete_policy(session, leave_type, current_user)


# --- balances ---------------------------------------------------------------


@router.get("/balances", response_model=LeaveBalancesRead)
def read_balances(
    year: int | None = None,
    employee_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every person in scope x every type, with days used, pending and left.

    `year` defaults to the current year; `employee_id` narrows to one person. A
    teacher-only account gets its own row, because the service applies the same
    scope the directory does.
    """
    return service.balance_register(
        session,
        year=year or date.today().year,
        employee_id=employee_id,
        user=current_user,
    )


@router.put("/balances/{employee_id}", response_model=LeaveBalanceRow)
def write_balance(
    employee_id: UUID,
    payload: LeaveBalanceWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_can_policy),
):
    """Grant or correct one person's days for one type and year (`403` for a non-office role)."""
    return workflow.save_balance(session, employee_id, payload, current_user)


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
    status: str | None = None,
    year: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Staff leave requests, newest first, each with the balance behind it.

    `status` filters by the five words a request may hold; `year` filters on the
    start date - the same key the balance counts by. The list is narrowed to the
    caller's scope, so a teacher-only account reads its own requests.
    """
    return service.list_staff_leave(
        session,
        status=status,
        year=year,
        user_ids=service.visible_user_ids(session, current_user),
    )


@router.get("/requests", response_model=list[LeaveTabRow])
def read_leave_tabs(
    kind: KindFilter = "all",
    status: str | None = None,
    year: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The Staff and Student tabs (0.10) - one table, two filtered views.

    `kind` is a filter, not a permission: the rows are still narrowed by the
    caller's scope, so `kind=student` does not widen what a teacher may read.
    """
    return service.tab_requests(
        session, kind=kind, status=status, year=year, user=current_user
    )


@router.get("/visible-kinds", response_model=VisibleKinds)
def read_visible_kinds(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Which tabs to draw: the office gets both, staff the Staff tab, a child the Student tab."""
    return VisibleKinds(kinds=service.visible_kinds(session, current_user))


# --- the workflow -----------------------------------------------------------


@router.post("/requests", response_model=LeaveRequestRead, status_code=201)
def apply_for_leave(
    payload: LeaveApplyIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_apply),
):
    """File a leave - a staff member's (with the balance checked) or a student's.

    `409` for a clash with an existing live leave, for a leaver, or for a request
    that would take the person past their entitlement; `422` for an unknown leave
    type, which names the types the school does grant.
    """
    return workflow.apply_leave(session, payload, current_user)


@router.get("/requests/{request_id}", response_model=LeaveRequestRead)
def read_request(
    request_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """One request by its own id (`404` when the caller may not see the person)."""
    return workflow.read_request(session, request_id, current_user)


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestRead)
def approve_request(
    request_id: UUID,
    payload: LeaveDecisionIn | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_approve),
):
    """Approve a pending request. Idempotent: approving twice is the same answer."""
    return workflow.decide(
        session,
        request_id,
        action="approve",
        note=payload.note if payload is not None else None,
        user=current_user,
    )


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestRead)
def reject_request(
    request_id: UUID,
    payload: LeaveDecisionIn | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_reject),
):
    """Reject a pending request, with the office's reason (`409` once approved)."""
    return workflow.decide(
        session,
        request_id,
        action="reject",
        note=payload.note if payload is not None else None,
        user=current_user,
    )


@router.post("/requests/{request_id}/cancel", response_model=LeaveRequestRead)
def cancel_request(
    request_id: UUID,
    payload: LeaveDecisionIn | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Withdraw a pending or approved leave - by the person who filed it, or the office.

    Guarded by `leave.read` and decided in the service: the rule is ownership, not a
    codename (see the module docstring). A cancelled leave stops making the day
    `On Leave` the moment it is saved, because the register derives that word.
    """
    return workflow.decide(
        session,
        request_id,
        action="cancel",
        note=payload.note if payload is not None else None,
        user=current_user,
    )
