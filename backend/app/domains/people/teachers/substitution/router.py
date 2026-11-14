"""The cover board's API: the day, one period's candidates, and the three writes.

Four routes, and the fixed ones come first - `/candidates` is declared before
`/assignments/{assignment_id}`, so a segment can never be read as a UUID (the same
rule `staff_attendance/router.py` and the teachers hub follow).

The board is a **read of a derived thing**: it writes nothing, so opening the screen
a hundred times leaves no rows behind. Rows appear only when somebody arranges a
cover (`POST /assignments`), signs it (`POST .../approve`) or withdraws it (`DELETE`).
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    SubstitutionAssignIn,
    SubstitutionAssignmentRead,
    SubstitutionBoardRead,
    SubstitutionCandidatesRead,
    SubstitutionDecisionIn,
)

router = APIRouter()

_can_read = RequirePermission("substitutions.read")
#: Arranging cover. An HOD holds it for their own department, decided in the service.
_can_assign = RequirePermission("substitutions.assign")
#: Signing it off - the office's, never a department's.
_can_approve = RequirePermission("substitutions.approve")


@router.get("", response_model=SubstitutionBoardRead)
def read_board(
    on_date: date | None = Query(default=None, alias="date"),
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The day's cover sheet: who is away, their periods, what is still open.

    `date` defaults to today - the office opens this in the morning. The parameter is
    aliased because `date` is also the type, and a query string cannot be called
    `date_`.
    """
    return service.board(session, on_date or date.today(), current_user)


@router.get("/candidates", response_model=SubstitutionCandidatesRead)
def read_candidates(
    period_id: UUID,
    on_date: date = Query(alias="date"),
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Who can cover one period, with the reason for every yes and every no.

    `409` when that period is not taught on that weekday, `404` when the person who
    teaches it is out of the caller's scope.
    """
    return service.candidates_for(session, period_id, on_date, current_user)


@router.post("/assignments", response_model=SubstitutionAssignmentRead, status_code=201)
def assign_period(
    payload: SubstitutionAssignIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_assign),
):
    """Arrange cover for one period and notify the substitute.

    `409` when the slot already has somebody, when the chosen colleague cannot take
    it (the answer names why: on leave, teaching another class, already covering),
    or when the period is not the absent teacher's on that weekday. `404` when the
    person has no absence recorded that day.
    """
    return service.assign(session, payload, current_user)


@router.post(
    "/assignments/{assignment_id}/approve", response_model=SubstitutionAssignmentRead
)
def approve_assignment(
    assignment_id: UUID,
    payload: SubstitutionDecisionIn | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_approve),
):
    """Sign a cover off. Approving twice is the same answer (`403` for a department)."""
    return service.approve(
        session,
        assignment_id,
        payload.note if payload is not None else None,
        current_user,
    )


@router.delete("/assignments/{assignment_id}", status_code=204)
def withdraw_assignment(
    assignment_id: UUID,
    payload: SubstitutionDecisionIn | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_assign),
):
    """Withdraw a cover, freeing the slot, and tell the substitute it is off.

    A body on a `DELETE` is unusual but allowed by the HTTP spec, and it is the only
    place to put the office's reason; the screen sends it, and the audit line quotes
    it.
    """
    service.remove(
        session,
        assignment_id,
        payload.note if payload is not None else None,
        current_user,
    )
