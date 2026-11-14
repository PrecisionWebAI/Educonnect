"""The appraisal season: the window, the person's own words, the reviewer's, the lock.

Five rules, each of which a school has argued about in front of me:

* **a cycle is a window, and only an `Open` one can be filled in.** A season created
  by mistake stays `Draft` and costs nobody a form; closing it keeps every appraisal.
* **everybody on the roll gets a row.** Opening a cycle creates one appraisal per
  teaching employee, so the queue is the same list as the staff directory minus the
  leavers - not "whoever remembered to open the form".
* **the person drafts, the reviewer rates, the office finalises.** Three different
  rights in one row: `appraisals.self` on your own, `appraisals.review` on your
  department (or the school), `appraisals.manage` for the lock.
* **finalising is the end.** A finalized appraisal is `409` to every write, including
  the reviewer's, because the number has been told to somebody and a record that can
  change afterwards is not a record.
* **a goal nobody judged is `null`, not failed.** `achieved` stays `None` until a
  reviewer says otherwise - the same rule the leave balance follows for `0`.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.admin.users.models import User
from app.domains.auth.models import utcnow
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers import scope as teachers_scope
from app.domains.people.teachers.profile.repository import employee_names

from . import repository
from .models import Appraisal, AppraisalCycle, AppraisalGoal, TrainingRecord
from .schemas import (
    AppraisalRead,
    CycleRead,
    GoalRead,
    QueueRead,
    TrainingRead,
)

#: Roles that see and sign the whole school's season.
OFFICE_ROLES = frozenset(
    {"system_admin", "director", "school_admin", "principal", "vice_principal"}
)
#: Roles that review - the office, plus a head of department inside their department.
REVIEW_ROLES = OFFICE_ROLES | {"hod"}


def _held(session: Session, user: User | None) -> set[str]:
    return teachers_scope.held_roles(session, user)


def _require_office(session: Session, user: User | None) -> None:
    if not _held(session, user) & OFFICE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Your role may not open, close or finalise an appraisal season.",
        )


def _own_employee(session: Session, user: User | None) -> Employee | None:
    """The employee row behind the caller, if they have one."""
    if user is None:
        return None
    return teachers_repository.get_teacher_by_user_id(session, user.id)


def _scope_ids(session: Session, user: User | None) -> set[UUID] | None:
    """Which employees this caller may see in a season (`None` = the whole school).

    The office sees everything; a head of department sees their department; anybody
    else sees their own row. A caller with no employee row and no office role sees
    nothing rather than everything - the failure has to be closed.
    """
    held = _held(session, user)
    if held & OFFICE_ROLES:
        return None
    own = _own_employee(session, user)
    if "hod" in held and own is not None and own.department:
        department = own.department.strip().lower()
        return {
            employee.id
            for employee in repository.roll(session)
            if (employee.department or "").strip().lower() == department
        }
    return {own.id} if own is not None else set()


def _may_review(session: Session, user: User | None, employee: Employee) -> bool:
    """Whether this caller may put a rating on this person's appraisal."""
    held = _held(session, user)
    if held & OFFICE_ROLES:
        return True
    if "hod" not in held:
        return False
    own = _own_employee(session, user)
    if own is None or not own.department or not employee.department:
        return False
    if own.id == employee.id:
        # A head of department does not review themselves: somebody above them does.
        return False
    return own.department.strip().lower() == employee.department.strip().lower()


# --- reads ------------------------------------------------------------------


def _cycle_read(session: Session, cycle: AppraisalCycle) -> CycleRead:
    counts = repository.row_counts(session, cycle.id)
    return CycleRead(
        id=cycle.id,
        name=cycle.name,
        start_date=cycle.start_date,
        end_date=cycle.end_date,
        status=cycle.status,
        note=cycle.note,
        appraisals=sum(counts.values()),
        submitted=counts.get(labels.APPRAISAL_SUBMITTED, 0)
        + counts.get(labels.APPRAISAL_REVIEWED, 0)
        + counts.get(labels.APPRAISAL_FINALIZED, 0),
        finalized=counts.get(labels.APPRAISAL_FINALIZED, 0),
    )


def cycles(session: Session, user: User | None) -> list[CycleRead]:
    """Every season, newest first. The list is the same for everybody who may read."""
    return [_cycle_read(session, cycle) for cycle in repository.cycles(session)]


def _reads(
    session: Session, cycle: AppraisalCycle, rows: list[Appraisal]
) -> list[AppraisalRead]:
    """One season's rows in the reply shape - names, goals and calls in four queries."""
    if not rows:
        return []
    employees = {employee.id: employee for employee in repository.roll(session)}
    for row in rows:
        if row.employee_id not in employees:
            found = session.get(Employee, row.employee_id)
            if found is not None:
                employees[found.id] = found

    names = employee_names(
        session,
        [row.employee_id for row in rows]
        + [row.reviewer_employee_id for row in rows if row.reviewer_employee_id],
    )
    goals = repository.goals_for(session, [row.id for row in rows])

    reads: list[AppraisalRead] = []
    for row in rows:
        employee = employees.get(row.employee_id)
        own_goals = goals.get(row.id, [])
        judged = [goal for goal in own_goals if goal.achieved is not None]
        reads.append(
            AppraisalRead(
                id=row.id,
                cycle_id=cycle.id,
                cycle_name=cycle.name,
                employee_id=row.employee_id,
                employee_code=employee.employee_code if employee else "",
                name=names.get(row.employee_id)
                or (employee.employee_code if employee else ""),
                department=employee.department if employee else None,
                status=row.status,
                status_label=row.status,
                self_rating=row.self_rating,
                self_note=row.self_note,
                reviewer_rating=row.reviewer_rating,
                reviewer_note=row.reviewer_note,
                reviewer_name=(
                    names.get(row.reviewer_employee_id)
                    if row.reviewer_employee_id
                    else None
                ),
                submitted_at=row.submitted_at,
                reviewed_at=row.reviewed_at,
                finalized_at=row.finalized_at,
                goals=[
                    GoalRead(
                        id=goal.id,
                        title=goal.title,
                        target=goal.target,
                        achieved=goal.achieved,
                        weight=goal.weight,
                    )
                    for goal in own_goals
                ],
                goals_total=len(own_goals),
                goals_judged=len(judged),
                goals_achieved=len([goal for goal in judged if goal.achieved]),
            )
        )
    return reads


def queue(session: Session, cycle_id: UUID, user: User | None) -> QueueRead:
    """The season's appraisals at the caller's scope, plus their own row.

    A head of department reads their department, a teacher reads themselves, the
    office reads the school - and `mine` is always the caller's own appraisal, so the
    screen can show "your appraisal" without a second request.
    """
    cycle = repository.cycle(session, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Appraisal cycle not found")

    visible = _scope_ids(session, user)
    rows = repository.appraisals_in(
        session, cycle.id, list(visible) if visible is not None else None
    )
    reads = _reads(session, cycle, rows)
    reads.sort(key=lambda row: row.name.lower())

    own = _own_employee(session, user)
    mine = next(
        (row for row in reads if own is not None and row.employee_id == own.id), None
    )
    if mine is None and own is not None:
        single = repository.appraisal_for(
            session, cycle_id=cycle.id, employee_id=own.id
        )
        if single is not None:
            mine = _reads(session, cycle, [single])[0]

    return QueueRead(
        cycle=_cycle_read(session, cycle),
        rows=reads,
        total=len(reads),
        mine=mine,
    )


# --- the season -------------------------------------------------------------


def create_cycle(session: Session, payload, user: User | None) -> CycleRead:
    """Plan a season. It starts as `Draft`, so nobody is asked to fill it in yet."""
    _require_office(session, user)
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="The window ends before it starts.")
    if repository.cycle_by_name(session, payload.name.strip()) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A cycle named {payload.name!r} already exists.",
        )
    cycle = AppraisalCycle(
        name=payload.name.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=labels.CYCLE_DRAFT,
        note=payload.note,
        created_by_user_id=user.id if user is not None else None,
    )
    session.add(cycle)
    session.commit()
    session.refresh(cycle)
    return _cycle_read(session, cycle)


#: Which cycle moves are allowed. A closed year can be re-opened (`Open`), because
#: schools do reopen a season to add somebody - but a row already finalized stays
#: final: `decide`/`review` refuse on the row, not on the cycle.
_CYCLE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    labels.CYCLE_DRAFT: (labels.CYCLE_OPEN,),
    labels.CYCLE_OPEN: (labels.CYCLE_CLOSED,),
    labels.CYCLE_CLOSED: (labels.CYCLE_OPEN,),
}


def set_cycle_status(
    session: Session, cycle_id: UUID, status: str, user: User | None
) -> CycleRead:
    """Move a season: `Draft -> Open -> Closed`, and `Closed -> Open` to reopen it.

    Opening it is what **creates the rows** - one draft appraisal per person on the
    roll - so the queue is the staff list, not whoever remembered a form.
    """
    _require_office(session, user)
    cycle = repository.cycle(session, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Appraisal cycle not found")
    if status not in labels.APPRAISAL_CYCLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unknown cycle status. Expected one of: "
                + ", ".join(labels.APPRAISAL_CYCLE_STATUSES)
            ),
        )
    if status == cycle.status:
        return _cycle_read(session, cycle)
    if status not in _CYCLE_TRANSITIONS[cycle.status]:
        raise HTTPException(
            status_code=409,
            detail=f"A {cycle.status} cycle cannot become {status}.",
        )

    cycle.status = status
    session.add(cycle)
    if status == labels.CYCLE_OPEN:
        existing = {
            row.employee_id for row in repository.appraisals_in(session, cycle.id)
        }
        for employee in repository.roll(session):
            if employee.id in existing:
                continue
            session.add(Appraisal(cycle_id=cycle.id, employee_id=employee.id))
    session.commit()
    session.refresh(cycle)
    return _cycle_read(session, cycle)


# --- one person's appraisal -------------------------------------------------


def _require_row(
    session: Session, appraisal_id: UUID
) -> tuple[Appraisal, AppraisalCycle, Employee]:
    """The row, its cycle and its person - `404` when any of them is gone."""
    row = repository.appraisal(session, appraisal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Appraisal not found")
    cycle = repository.cycle(session, row.cycle_id)
    employee = session.get(Employee, row.employee_id)
    if cycle is None or employee is None:
        raise HTTPException(status_code=404, detail="Appraisal not found")
    return row, cycle, employee


def _require_open_season(cycle: AppraisalCycle) -> None:
    if cycle.status != labels.CYCLE_OPEN:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This season is {cycle.status}, so appraisals cannot be filled in. "
                "The office opens it first."
            ),
        )


def _require_unlocked(row: Appraisal) -> None:
    if row.status in labels.APPRAISAL_LOCKED:
        raise HTTPException(
            status_code=409,
            detail=(
                "This appraisal is finalized - the rating has been communicated, so it "
                "is read-only."
            ),
        )


def save_self(
    session: Session, appraisal_id: UUID, payload, user: User | None
) -> AppraisalRead:
    """Save your own rating, note and goals. Replaces the goal list.

    Only the person themselves may do this (an office role is not a licence to write
    somebody's self-assessment), only while the season is open, and only until the
    reviewer has recorded a rating - after that the person's words are the record of
    what they said, not a draft.
    """
    row, cycle, employee = _require_row(session, appraisal_id)
    own = _own_employee(session, user)
    if own is None or own.id != employee.id:
        raise HTTPException(
            status_code=403,
            detail="Only the person this appraisal is about may fill it in.",
        )
    _require_open_season(cycle)
    _require_unlocked(row)
    if row.status == labels.APPRAISAL_REVIEWED:
        raise HTTPException(
            status_code=409,
            detail="The reviewer has already rated this appraisal; it can no longer be edited.",
        )

    row.self_rating = payload.self_rating
    row.self_note = payload.self_note
    row.status = labels.APPRAISAL_DRAFT
    session.add(row)

    for goal in repository.goals_for(session, [row.id]).get(row.id, []):
        session.delete(goal)
    for goal in payload.goals:
        session.add(
            AppraisalGoal(
                appraisal_id=row.id,
                title=goal.title.strip(),
                target=goal.target,
                weight=goal.weight,
            )
        )
    session.commit()
    session.refresh(row)
    return _reads(session, cycle, [row])[0]


def submit(session: Session, appraisal_id: UUID, user: User | None) -> AppraisalRead:
    """Send it to the reviewer. Idempotent while it is still `Submitted`."""
    row, cycle, employee = _require_row(session, appraisal_id)
    own = _own_employee(session, user)
    if own is None or own.id != employee.id:
        raise HTTPException(
            status_code=403,
            detail="Only the person this appraisal is about may submit it.",
        )
    _require_open_season(cycle)
    _require_unlocked(row)
    if row.status == labels.APPRAISAL_SUBMITTED:
        return _reads(session, cycle, [row])[0]
    if row.status != labels.APPRAISAL_DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"This appraisal is {row.status}; it cannot be submitted again.",
        )
    if row.self_rating is None:
        raise HTTPException(
            status_code=409,
            detail="Fill in your own rating before submitting - the reviewer needs it.",
        )

    row.status = labels.APPRAISAL_SUBMITTED
    row.submitted_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _reads(session, cycle, [row])[0]


def review(
    session: Session, appraisal_id: UUID, payload, user: User | None
) -> AppraisalRead:
    """Record the reviewer's rating. A reviewer may correct it until it is finalized.

    `self` is not required to have been submitted first? It **is**: reviewing a draft
    would put a rating on somebody who has not said anything yet, and the two notes
    are supposed to be about the same conversation.
    """
    row, cycle, employee = _require_row(session, appraisal_id)
    if not _may_review(session, user, employee):
        raise HTTPException(
            status_code=403,
            detail=(
                "Your role may not review this appraisal - an HOD reviews their own "
                "department, the office reviews the school, and nobody reviews themselves."
            ),
        )
    _require_unlocked(row)
    if row.status == labels.APPRAISAL_DRAFT:
        raise HTTPException(
            status_code=409,
            detail="This appraisal has not been submitted by the person yet.",
        )

    reviewer = _own_employee(session, user)
    row.reviewer_rating = payload.reviewer_rating
    row.reviewer_note = payload.reviewer_note
    row.reviewer_employee_id = reviewer.id if reviewer is not None else None
    row.status = labels.APPRAISAL_REVIEWED
    row.reviewed_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _reads(session, cycle, [row])[0]


def decide_goal(
    session: Session, goal_id: UUID, achieved: bool, user: User | None
) -> AppraisalRead:
    """Mark one goal achieved (or not). The reviewer's call, not the author's."""
    goal = repository.goal(session, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    row, cycle, employee = _require_row(session, goal.appraisal_id)
    if not _may_review(session, user, employee):
        raise HTTPException(
            status_code=403, detail="Your role may not judge this appraisal's goals."
        )
    _require_unlocked(row)

    goal.achieved = achieved
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return _reads(session, cycle, [row])[0]


def finalize(session: Session, appraisal_id: UUID, user: User | None) -> AppraisalRead:
    """Lock the appraisal. Approving twice is the same answer.

    Only a **reviewed** appraisal can be finalized: the officer signing the season off
    is signing a number somebody has already discussed with the person, not a draft.
    """
    row, cycle, _employee = _require_row(session, appraisal_id)
    _require_office(session, user)
    if row.status == labels.APPRAISAL_FINALIZED:
        return _reads(session, cycle, [row])[0]
    if row.status != labels.APPRAISAL_REVIEWED:
        raise HTTPException(
            status_code=409,
            detail=(
                "Only a reviewed appraisal can be finalized - the reviewer has to "
                f"record a rating first (this one is {row.status})."
            ),
        )

    row.status = labels.APPRAISAL_FINALIZED
    row.finalized_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _reads(session, cycle, [row])[0]


# --- training ---------------------------------------------------------------


def training(
    session: Session, employee_id: UUID, user: User | None
) -> list[TrainingRead]:
    """One person's training, at the caller's scope (`404` outside it)."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    visible = _scope_ids(session, user)
    if visible is not None and employee.id not in visible:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return [
        TrainingRead(
            id=row.id,
            employee_id=row.employee_id,
            title=row.title,
            provider=row.provider,
            on_date=row.on_date,
            hours=row.hours,
            note=row.note,
        )
        for row in repository.training(session, employee.id)
    ]


def add_training(
    session: Session, employee_id: UUID, payload, user: User | None
) -> TrainingRead:
    """Record what somebody attended. The office's book, like the register."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if not _held(session, user) & (OFFICE_ROLES | {"hod"}):
        raise HTTPException(
            status_code=403, detail="Your role may not record staff training."
        )
    if "hod" in _held(session, user) and not _may_review(session, user, employee):
        raise HTTPException(
            status_code=403,
            detail="A head of department records training inside their own department.",
        )
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail="This person is off the staff roll, so their record is read-only.",
        )

    row = TrainingRecord(
        employee_id=employee.id,
        title=payload.title.strip(),
        provider=payload.provider,
        on_date=payload.on_date,
        hours=payload.hours,
        note=payload.note,
        created_by_user_id=user.id if user is not None else None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return TrainingRead(
        id=row.id,
        employee_id=row.employee_id,
        title=row.title,
        provider=row.provider,
        on_date=row.on_date,
        hours=row.hours,
        note=row.note,
    )
