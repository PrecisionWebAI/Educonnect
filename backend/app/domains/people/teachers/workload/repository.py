"""Reads for what a teacher taught, the capacity rule and one person's week.

The Workload and Performance tabs that used these have been removed; what stays is what
the teacher's own "My week", the Course tab and the staff reports still read.

The week is read in **two** statements (the timetable's periods, the duties) and
assembled in Python: a grid is asked for one person at a time, and a `UNION` of
two tables with different columns would need every column cast to text to sort.
"""

from datetime import date, time
from uuid import UUID

from sqlmodel import Session, func, select

from app.domains.academic.classroom.homework.models import ClassLog
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.settings import year_scope
from app.domains.people.teachers.substitution.models import SubstitutionAssignment

from .. import labels
from .. import repository as teachers_repository
from .models import StaffDuty, StaffWorkloadRule

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
        statement = select(ClassLog.teacher_id, func.count()).where(
            ClassLog.teacher_id.in_(teacher_ids),
            ClassLog.date >= start,
            ClassLog.date <= end,
            condition,
        )
        statement = year_scope.by_date_window(session, statement, ClassLog.date)
        rows = session.exec(statement.group_by(ClassLog.teacher_id)).all()
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
    statement = select(
        SubstitutionAssignment.substitute_employee_id, func.count()
    ).where(
        SubstitutionAssignment.substitute_employee_id.in_(teacher_ids),
        SubstitutionAssignment.on_date >= start,
        SubstitutionAssignment.on_date <= end,
        SubstitutionAssignment.status == labels.APPROVED,
    )
    statement = year_scope.by_date_window(
        session, statement, SubstitutionAssignment.on_date
    )
    rows = session.exec(
        statement.group_by(SubstitutionAssignment.substitute_employee_id)
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


# --- what a week holds -----------------------------------------------------


def week_periods(session: Session, employee_id: UUID) -> list[tuple]:
    """`[(period, subject_name)]` for one teacher - their side of the timetable."""
    from app.domains.academic.classroom.course.models import ClassroomSubject

    statement = (
        select(TimetablePeriod, ClassroomSubject.name)
        .join(
            ClassroomSubject,
            ClassroomSubject.id == TimetablePeriod.classroom_subject_id,
        )
        .where(TimetablePeriod.teacher_id == employee_id)
    )
    # The week belongs to the selected session year: next year starts with an empty one.
    statement = year_scope.by_year_column(
        session, statement, TimetablePeriod.academic_year_id, include_null=True
    )
    return list(session.exec(statement).all())


def class_teacher_rooms(
    session: Session, employee_ids: list[UUID]
) -> dict[UUID, set[UUID]]:
    """{employee_id: classroom ids they run as class teacher} this academic year.

    Read from the year's class-teacher assignments (the record), not from the legacy
    `classroom.class_teacher_id` pointer - which names almost nobody - so a class teacher is
    never missed and one whose assignment has ended is not shown.
    """
    if not employee_ids:
        return {}
    from app.domains.academic.classroom.students.promotion.class_teacher import (
        class_teacher_rooms_for,
    )

    return {
        teacher_id: set(rooms)
        for teacher_id, rooms in class_teacher_rooms_for(session, employee_ids).items()
    }
