"""Reads and writes for the appraisal season - set-shaped, like the rest of the hub.

A season is forty appraisals at once: the queue reads every row in one query, then
the goals for all of them in a second, and the names in a third. A query per person is
how a screen that opens in 200 ms takes four seconds against a hosted database.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import repository as teachers_repository

from .models import Appraisal, AppraisalCycle, AppraisalGoal, TrainingRecord

# --- cycles -----------------------------------------------------------------


def cycles(session: Session) -> list[AppraisalCycle]:
    """Every season, newest window first."""
    return list(
        session.exec(
            select(AppraisalCycle).order_by(
                AppraisalCycle.start_date.desc()  # type: ignore[attr-defined]
            )
        ).all()
    )


def cycle(session: Session, cycle_id: UUID) -> AppraisalCycle | None:
    return session.get(AppraisalCycle, cycle_id)


def cycle_by_name(session: Session, name: str) -> AppraisalCycle | None:
    return session.exec(
        select(AppraisalCycle).where(AppraisalCycle.name == name)
    ).first()


def row_counts(session: Session, cycle_id: UUID) -> dict[str, int]:
    """`{status: count}` for one cycle, so a cycle card needs no second call."""
    counts = dict.fromkeys(labels.APPRAISAL_STATUSES, 0)
    for appraisal in appraisals_in(session, cycle_id):
        counts[appraisal.status] = counts.get(appraisal.status, 0) + 1
    return counts


# --- appraisals -------------------------------------------------------------


def appraisals_in(
    session: Session, cycle_id: UUID, employee_ids: list[UUID] | None = None
) -> list[Appraisal]:
    statement = select(Appraisal).where(Appraisal.cycle_id == cycle_id)
    if employee_ids is not None:
        if not employee_ids:
            return []
        statement = statement.where(Appraisal.employee_id.in_(employee_ids))
    return list(session.exec(statement).all())


def appraisal(session: Session, appraisal_id: UUID) -> Appraisal | None:
    return session.get(Appraisal, appraisal_id)


def appraisal_for(
    session: Session, *, cycle_id: UUID, employee_id: UUID
) -> Appraisal | None:
    return session.exec(
        select(Appraisal).where(
            Appraisal.cycle_id == cycle_id, Appraisal.employee_id == employee_id
        )
    ).first()


def roll(session: Session) -> list[Employee]:
    """Everybody on the teaching roll - the people a season covers.

    The directory's own roll (`teaching_employees`), so the appraisal queue and the
    staff list cannot disagree about who works here.
    """
    return [
        employee
        for employee in teachers_repository.teaching_employees(session)
        if not labels.serves_read_only(
            deactivated_at=employee.deactivated_at, left_on=employee.left_on
        )
    ]


# --- goals and training -----------------------------------------------------


def goals_for(
    session: Session, appraisal_ids: list[UUID]
) -> dict[UUID, list[AppraisalGoal]]:
    """`{appraisal_id: [goal, ...]}` in one query, oldest first."""
    wanted = [
        appraisal_id for appraisal_id in dict.fromkeys(appraisal_ids) if appraisal_id
    ]
    if not wanted:
        return {}
    rows = session.exec(
        select(AppraisalGoal)
        .where(AppraisalGoal.appraisal_id.in_(wanted))
        .order_by(AppraisalGoal.created_at)  # type: ignore[attr-defined]
    ).all()
    grouped: dict[UUID, list[AppraisalGoal]] = {}
    for goal in rows:
        grouped.setdefault(goal.appraisal_id, []).append(goal)
    return grouped


def goal(session: Session, goal_id: UUID) -> AppraisalGoal | None:
    return session.get(AppraisalGoal, goal_id)


def training(session: Session, employee_id: UUID) -> list[TrainingRecord]:
    """One person's training, newest first."""
    return list(
        session.exec(
            select(TrainingRecord)
            .where(TrainingRecord.employee_id == employee_id)
            .order_by(TrainingRecord.on_date.desc())  # type: ignore[attr-defined]
        ).all()
    )


def training_between(
    session: Session, employee_id: UUID, start: date, end: date
) -> list[TrainingRecord]:
    """Training inside a window - what an appraisal can point at."""
    return [
        row for row in training(session, employee_id) if start <= row.on_date <= end
    ]
