"""The appraisal API: seasons, the queue, the person's form, the reviewer's call.

Every path is fixed except the id segments (`/cycles/{id}`, `/{id}/self`,
`/goals/{id}`), and the fixed paths are declared first - the same rule every router in
this hub follows.

The three write groups map to the three rights, and they are **different people**:
`/self` and `/submit` are the appraisee's (the service refuses anybody else),
`/review` and `/goals` are the reviewer's, and `/cycles` + `/finalize` are the
office's. A route guard that let an HOD finalize their own department would make the
lock decorative.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AppraisalRead,
    CycleIn,
    CycleRead,
    CycleStatusIn,
    GoalVerdictIn,
    QueueRead,
    ReviewIn,
    SelfAssessmentIn,
    TrainingIn,
    TrainingRead,
)

router = APIRouter()

_can_read = RequirePermission("appraisals.read")
#: Filling in **your own** appraisal. The service checks it is yours.
_can_self = RequirePermission("appraisals.self")
#: Rating somebody else's (an HOD: their department; the office: the school).
_can_review = RequirePermission("appraisals.review")
#: Opening/closing a season and finalising an appraisal - the lock.
_can_manage = RequirePermission("appraisals.manage")
_can_train = RequirePermission("training.manage")


@router.get("/cycles", response_model=list[CycleRead])
def read_cycles(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every season, newest window first, with its progress counts."""
    return service.cycles(session, current_user)


@router.post("/cycles", response_model=CycleRead, status_code=201)
def open_cycle(
    payload: CycleIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Plan a season (`Draft`). `409` when the name is taken (`403` for a non-office role)."""
    return service.create_cycle(session, payload, current_user)


@router.post("/cycles/{cycle_id}/status", response_model=CycleRead)
def move_cycle(
    cycle_id: UUID,
    payload: CycleStatusIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """`Draft -> Open -> Closed` (and `Closed -> Open` to reopen).

    Opening it creates one draft appraisal per person on the roll - the queue is the
    staff list, not whoever remembered the form.
    """
    return service.set_cycle_status(session, cycle_id, payload.status, current_user)


@router.get("/cycles/{cycle_id}", response_model=QueueRead)
def read_queue(
    cycle_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The season at the caller's scope, plus their own appraisal (`404` unknown id)."""
    return service.queue(session, cycle_id, current_user)


@router.post("/{appraisal_id}/self", response_model=AppraisalRead)
def save_self(
    appraisal_id: UUID,
    payload: SelfAssessmentIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_self),
):
    """Save **your own** rating, note and goals (`403` for anybody else's).

    `409` once the reviewer has rated it, once the appraisal is finalized, or when the
    season is not open.
    """
    return service.save_self(session, appraisal_id, payload, current_user)


@router.post("/{appraisal_id}/submit", response_model=AppraisalRead)
def submit_appraisal(
    appraisal_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_self),
):
    """Send it to the reviewer. Idempotent; `409` without a rating or after review."""
    return service.submit(session, appraisal_id, current_user)


@router.post("/{appraisal_id}/review", response_model=AppraisalRead)
def review_appraisal(
    appraisal_id: UUID,
    payload: ReviewIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_review),
):
    """Record the reviewer's rating (`403` outside your department; `409` on a draft)."""
    return service.review(session, appraisal_id, payload, current_user)


@router.post("/{appraisal_id}/finalize", response_model=AppraisalRead)
def finalize_appraisal(
    appraisal_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Lock it. Idempotent; only a **reviewed** appraisal can be finalized (`409`)."""
    return service.finalize(session, appraisal_id, current_user)


@router.patch("/goals/{goal_id}", response_model=AppraisalRead)
def judge_goal(
    goal_id: UUID,
    payload: GoalVerdictIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_review),
):
    """Mark one goal achieved - or not. A finalized appraisal is `409`."""
    return service.decide_goal(session, goal_id, payload.achieved, current_user)


@router.get("/employees/{employee_id}/training", response_model=list[TrainingRead])
def read_training(
    employee_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """One person's training, newest first, at the caller's scope."""
    return service.training(session, employee_id, current_user)


@router.post(
    "/employees/{employee_id}/training", response_model=TrainingRead, status_code=201
)
def record_training(
    employee_id: UUID,
    payload: TrainingIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_train),
):
    """Record what somebody attended (`403` outside an HOD's department; `409` on a leaver)."""
    return service.add_training(session, employee_id, payload, current_user)
