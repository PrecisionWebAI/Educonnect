"""Reads and writes for the week and for the school's day shape.

The only place that knows the API's `section_id` is the column's `classroom_id`.
"""

from datetime import time
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from .models import BellSchedule, TimetablePeriod
from .schemas import TimetablePeriodCreate


def _scope_year(query, academic_year_id: UUID | None):
    """Current year plus legacy NULL rows; no argument keeps the old all-years read."""
    if academic_year_id is None:
        return query
    return query.where(
        or_(
            TimetablePeriod.academic_year_id == academic_year_id,
            TimetablePeriod.academic_year_id.is_(None),
        )
    )


def create_period(
    session: Session,
    period_in: TimetablePeriodCreate,
    academic_year_id: UUID | None = None,
) -> TimetablePeriod:
    row = TimetablePeriod(
        academic_year_id=academic_year_id,
        classroom_id=period_in.section_id,
        classroom_subject_id=period_in.classroom_subject_id,
        teacher_id=period_in.teacher_id,
        day_of_week=period_in.day_of_week,
        start_time=period_in.start_time,
        end_time=period_in.end_time,
        room=period_in.room,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_timetable_by_class(
    session: Session,
    class_id: UUID,
    section_id: UUID | None = None,
    academic_year_id: UUID | None = None,
) -> list[TimetablePeriod]:
    """A class's week, or one section's when `section_id` is named.

    A period names only its section; the class is matched through
    `section.class_id`, so "the whole class" means every section in it.
    """
    from app.domains.academic.classroom.academics.models import Classroom

    query = (
        select(TimetablePeriod)
        .join(Classroom, Classroom.id == TimetablePeriod.classroom_id)
        .where(Classroom.class_id == class_id)
    )
    query = _scope_year(query, academic_year_id)
    if section_id:
        query = query.where(TimetablePeriod.classroom_id == section_id)
    return list(
        session.exec(
            query.order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
        ).all()
    )


def get_timetable_by_teacher(
    session: Session, teacher_id: UUID, academic_year_id: UUID | None = None
) -> list[TimetablePeriod]:
    statement = _scope_year(
        select(TimetablePeriod).where(TimetablePeriod.teacher_id == teacher_id),
        academic_year_id,
    )
    statement = statement.order_by(
        TimetablePeriod.day_of_week, TimetablePeriod.start_time
    )
    return list(session.exec(statement).all())


def get_all_periods(
    session: Session, academic_year_id: UUID | None = None
) -> list[TimetablePeriod]:
    statement = _scope_year(select(TimetablePeriod), academic_year_id)
    statement = statement.order_by(
        TimetablePeriod.day_of_week, TimetablePeriod.start_time
    )
    return list(session.exec(statement).all())


def get_period(session: Session, period_id: UUID) -> TimetablePeriod | None:
    """One period, for the edit/clear actions."""
    return session.get(TimetablePeriod, period_id)


def clash(
    session: Session,
    *,
    teacher_id: UUID,
    classroom_id: UUID,
    day_of_week,
    start_time: time,
    academic_year_id: UUID | None = None,
    ignore_id: UUID | None = None,
) -> TimetablePeriod | None:
    """A row that already holds this teacher **or** this room at this hour.

    One query, because the two refusals come from the same pair of keys and the caller
    wants to say which of them was hit. `ignore_id` is the period being moved, so
    saving it unchanged is not a clash with itself.
    """
    statement = _scope_year(
        select(TimetablePeriod).where(
            TimetablePeriod.day_of_week == day_of_week,
            TimetablePeriod.start_time == start_time,
        ),
        academic_year_id,
    )
    if ignore_id is not None:
        statement = statement.where(TimetablePeriod.id != ignore_id)
    for row in session.exec(statement).all():
        if row.teacher_id == teacher_id or row.classroom_id == classroom_id:
            return row
    return None


def update_period(
    session: Session,
    period: TimetablePeriod,
    period_in: TimetablePeriodCreate,
    academic_year_id: UUID | None = None,
) -> TimetablePeriod:
    """Replace a period's fields.

    The grid always sends the whole slot (subject, teacher, day, times, room), so a
    plain field-by-field copy is the honest update - no partial-merge guessing.
    """
    period.academic_year_id = academic_year_id or period.academic_year_id
    period.classroom_id = period_in.section_id
    period.classroom_subject_id = period_in.classroom_subject_id
    period.teacher_id = period_in.teacher_id
    period.day_of_week = period_in.day_of_week
    period.start_time = period_in.start_time
    period.end_time = period_in.end_time
    period.room = period_in.room
    session.add(period)
    session.commit()
    session.refresh(period)
    return period


def delete_period(session: Session, period: TimetablePeriod) -> None:
    """Clear a slot: the period is gone from the week."""
    session.delete(period)
    session.commit()


# --- the school's day shape ------------------------------------------------


def bell_slots(session: Session) -> list[BellSchedule]:
    return list(
        session.exec(select(BellSchedule).order_by(BellSchedule.period_no)).all()
    )


class PeriodsWouldBeLost(Exception):
    """The new day has fewer lessons than classes already use."""

    def __init__(self, count: int):
        self.count = count


def replace_bell_slots(
    session: Session, slots: list[dict], force: bool = False
) -> list[BellSchedule]:
    """Swap the day's shape for a new one in a single transaction.

    The day is global, so every placed period moves with it: the lesson that was the
    Nth one of the day becomes the Nth lesson of the new day, in every class. Only a
    period whose lesson no longer exists (the day got shorter) is dropped, and only
    with `force`.
    """
    old = bell_slots(session)
    old_index = {
        row.start_time: n
        for n, row in enumerate((r for r in old if not r.is_break), start=1)
    }
    new_lessons = [s for s in slots if not s["is_break"]]

    placed = [
        (p, old_index[p.start_time])
        for p in session.exec(select(TimetablePeriod)).all()
        if p.start_time in old_index
    ]
    lost = [p for p, n in placed if n > len(new_lessons)]
    if lost and not force:
        raise PeriodsWouldBeLost(len(lost))
    for p in lost:
        session.delete(p)
    keep = [(p, n) for p, n in placed if n <= len(new_lessons)]
    # Two passes through a parking time, so one row never lands on another's key
    # (`uq_timetableperiod_*`) halfway through the move.
    for p, n in keep:
        p.start_time = time(23, 59, n)
    session.flush()
    for p, n in keep:
        p.start_time = new_lessons[n - 1]["start_time"]
        p.end_time = new_lessons[n - 1]["end_time"]
    session.flush()

    for row in old:
        session.delete(row)
    session.flush()
    rows = [BellSchedule(**slot) for slot in slots]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def add_bell_slots(session: Session, slots: list[dict]) -> list[BellSchedule]:
    """Write the day's shape in one go - used only by the one-time seed."""
    rows = [BellSchedule(**slot) for slot in slots]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows
