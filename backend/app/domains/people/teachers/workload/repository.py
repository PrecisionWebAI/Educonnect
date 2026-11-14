"""Reads and lookups for the capacity rule, the duties and one person's week.

Every duty statement is scoped **by `employee_id`**, not by row id alone: the path
is `/teachers/workload/{id}/duties/{duty}`, and looking the duty up by its own id
would let a caller who may manage employee A delete a duty that belongs to
employee B. The tenant listener narrows both to the session's school, so a
cross-school id finds nothing (`404`).

The week is read in **two** statements (the timetable's periods, the duties) and
assembled in Python: a grid is asked for one person at a time, and a `UNION` of
two tables with different columns would need every column cast to text to sort.
"""

from datetime import date, time
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.domains.academic.classroom.academics.models import Classroom, Subject
from app.domains.academic.classroom.homework.models import ClassLog
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.auth.models import utcnow
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.substitution.models import SubstitutionAssignment

from .. import labels
from .. import repository as teachers_repository
from .models import StaffDuty, StaffWorkloadRule
from .schemas import WorkloadRuleWrite

# --- what the week actually taught (Phase 5) -------------------------------


def completed_counts(
    session: Session, teacher_ids: list[UUID], start: date, end: date
) -> dict[UUID, int]:
    """{employee_id: periods taught inside the window}.

    "Completed" means **periods** now that `classlog` is per-period (one line per
    period, `uq_classlog_classroom_date_period`). A school that still writes the
    register-style day line (`timetableperiod_id IS NULL`) is counted by its days,
    one per line - never mixed into the same teacher's total, which would pay a
    teacher twice for one Tuesday.

    Counted by the database for the whole page, like `period_counts`.
    """
    if not teacher_ids:
        return {}

    def _count(perioded: bool) -> dict[UUID, int]:
        condition = (
            ClassLog.timetableperiod_id.is_not(None)
            if perioded
            else ClassLog.timetableperiod_id.is_(None)
        )
        rows = session.exec(
            select(ClassLog.teacher_id, func.count())
            .where(
                ClassLog.teacher_id.in_(teacher_ids),
                ClassLog.date >= start,
                ClassLog.date <= end,
                condition,
            )
            .group_by(ClassLog.teacher_id)
        ).all()
        return {teacher_id: int(count) for teacher_id, count in rows}

    periods = _count(perioded=True)
    days = _count(perioded=False)
    # A period-logging teacher is measured in periods; a day-logging one in days.
    return {
        teacher_id: periods.get(teacher_id, days.get(teacher_id, 0))
        for teacher_id in {*periods, *days}
    }


def substitute_counts(
    session: Session, teacher_ids: list[UUID], start: date, end: date
) -> dict[UUID, int]:
    """{employee_id: periods covered for somebody else in the window}.

    Only **approved** covers count: an assigned-but-unconfirmed cover is a proposal,
    and putting it in the load figure would pay somebody for a period they may never
    stand in for.
    """
    if not teacher_ids:
        return {}
    rows = session.exec(
        select(SubstitutionAssignment.substitute_employee_id, func.count())
        .where(
            SubstitutionAssignment.substitute_employee_id.in_(teacher_ids),
            SubstitutionAssignment.on_date >= start,
            SubstitutionAssignment.on_date <= end,
            SubstitutionAssignment.status == labels.APPROVED,
        )
        .group_by(SubstitutionAssignment.substitute_employee_id)
    ).all()
    return {teacher_id: int(count) for teacher_id, count in rows}


# --- the capacity rule -----------------------------------------------------
def rule(session: Session) -> StaffWorkloadRule | None:
    """The school's policy, or None when nobody has set one yet.

    `.first()` rather than `.one()`: `UNIQUE(school_id)` does not cover a NULL
    school (see the model), so a database that somehow holds two rows must make
    the matrix read the first one instead of answering `500` on every page.
    """
    return session.exec(select(StaffWorkloadRule)).first()


def capacity(session: Session) -> tuple[int, str, int]:
    """``(capacity, source, week_slots)`` - the denominator and where it came from.

    One implementation, because three readers ask it: the matrix (the bar), the
    analytics tiles (the average) and the capacity dialog (what it is editing). A
    second copy is how the header and the table start describing two different
    weeks.

    The rule wins when the school has stated one; otherwise the timetable's own
    slot count stands in and `source` says so, so the screen can print "out of 26
    (timetable)" instead of implying a policy nobody wrote.
    """
    slots = teachers_repository.week_capacity(session)
    row = rule(session)
    if row is not None and row.weekly_periods:
        return row.weekly_periods, "rule", slots
    return slots, "timetable", slots


def save_rule(
    session: Session, payload: WorkloadRuleWrite, user_id: UUID | None
) -> StaffWorkloadRule:
    """Create the school's rule, or update the one it already has.

    One row, ever: a second rule would leave the matrix choosing between two
    numbers, and the choice would depend on row order.
    """
    row = rule(session)
    if row is None:
        row = StaffWorkloadRule()
        session.add(row)
    row.weekly_periods = payload.weekly_periods
    row.overload_percent = payload.overload_percent
    row.underload_percent = payload.underload_percent
    row.updated_by_user_id = user_id
    row.updated_at = utcnow()
    session.commit()
    session.refresh(row)
    return row


# --- duties ----------------------------------------------------------------


def _duty_order(row: StaffDuty) -> tuple:
    """Monday first, then by start time, then the dated ones, then the type.

    Chronology inside a day, not alphabet: a teacher reads Monday 08:00 before
    Monday 14:00. A duty with no day ("standing") sorts after the week, and one
    with no hours after the timed ones on its day, because a slot is what the
    reader looks for first.
    """
    rank = (
        labels.WEEK_DAYS.index(row.day_of_week)
        if row.day_of_week in labels.WEEK_DAYS
        else len(labels.WEEK_DAYS)
    )
    return (rank, row.start_time or time.max, row.on_date or date.max, row.duty_type)


def duties(session: Session, employee_id: UUID) -> list[StaffDuty]:
    """Every duty on this person's file, in the order the drawer lists them."""
    rows = session.exec(
        select(StaffDuty).where(StaffDuty.employee_id == employee_id)
    ).all()
    return sorted(rows, key=_duty_order)


def duty(session: Session, *, employee_id: UUID, duty_id: UUID) -> StaffDuty | None:
    """One duty **within the employee in the path** - the cross-profile guard."""
    return session.exec(
        select(StaffDuty).where(
            StaffDuty.id == duty_id,
            StaffDuty.employee_id == employee_id,
        )
    ).first()


def same_duty(
    session: Session,
    *,
    employee_id: UUID,
    duty_type: str,
    day_of_week: str | None,
    on_date: date | None,
    start_time: time | None,
) -> StaffDuty | None:
    """The same duty already filed - a `409`, not a second row.

    `IS NULL` for each empty column rather than `== None`: SQL's `= NULL` is never
    true, so comparing two standing duties would silently find nothing and the
    duplicate would be filed twice.
    """
    statement = select(StaffDuty).where(
        StaffDuty.employee_id == employee_id,
        StaffDuty.duty_type == duty_type,
    )
    for column, value in (
        (StaffDuty.day_of_week, day_of_week),
        (StaffDuty.on_date, on_date),
        (StaffDuty.start_time, start_time),
    ):
        statement = statement.where(
            column.is_(None) if value is None else column == value
        )
    return session.exec(statement).first()


def duty_counts(
    session: Session, employee_ids: list[UUID], today: date
) -> dict[UUID, int]:
    """{employee_id: duties still standing today} for the matrix's Duties column.

    A duty that ended (`effective_to` in the past) is history: it stays on the
    person's file and in the audit trail, but the matrix answers "what does this
    week hold", not "what has this person ever done".
    """
    if not employee_ids:
        return {}
    rows = session.exec(
        select(StaffDuty.employee_id, func.count())
        .where(
            StaffDuty.employee_id.in_(employee_ids),
            or_(
                StaffDuty.effective_to.is_(None),  # type: ignore[union-attr]
                StaffDuty.effective_to >= today,
            ),
        )
        .group_by(StaffDuty.employee_id)  # type: ignore[arg-type]
    ).all()
    return {employee_id: int(count) for employee_id, count in rows}


# --- what a week holds -----------------------------------------------------


def week_periods(session: Session, employee_id: UUID) -> list[tuple]:
    """`[(period, subject_name)]` for one teacher - their side of the timetable."""
    return list(
        session.exec(
            select(TimetablePeriod, Subject.name)
            .join(Subject, Subject.id == TimetablePeriod.subject_id)
            .where(TimetablePeriod.teacher_id == employee_id)
        ).all()
    )


def class_teacher_rooms(
    session: Session, employee_ids: list[UUID]
) -> dict[UUID, set[UUID]]:
    """{employee_id: classroom ids they run as class teacher}.

    The matrix's `classes` column used to come from `subjectteacher` alone, so a
    class teacher who was not also assigned that subject showed **no class at
    all** - the one fact that defines the job.
    """
    if not employee_ids:
        return {}
    rooms: dict[UUID, set[UUID]] = {}
    for teacher_id, room_id in session.exec(
        select(Classroom.class_teacher_id, Classroom.id).where(
            Classroom.class_teacher_id.in_(employee_ids)
        )
    ).all():
        rooms.setdefault(teacher_id, set()).add(room_id)
    return rooms


def departments(session: Session, employee_ids: list[UUID]) -> dict[UUID, str]:
    """`{employee_id: department}` in one query, for the analytics split."""
    if not employee_ids:
        return {}
    rows = session.exec(
        select(Employee.id, Employee.department).where(Employee.id.in_(employee_ids))
    ).all()
    return {employee_id: department or "" for employee_id, department in rows}
