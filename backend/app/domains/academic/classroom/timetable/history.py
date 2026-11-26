"""The timetable's memory: who held each slot, and for which dates.

Two halves:

* **Writing** - model events on `TimetablePeriod`. They fire for every route a period can
  change by (the grid, the school-wide screen, a room or course being deleted, the bell
  schedule being reshaped), so no caller has to remember to leave a trail. Only a change of
  *who*, *where* or *which day* matters: a slot that merely moves to a new clock time when
  the bell schedule changes is still the same teacher in the same room on the same day.
* **Reading** - `year_load`: for a group of teachers, from the session's first day to a
  chosen day and counting **open school days only** (weekly offs and holidays are out), the
  classes they took, the substitutions they covered and the classes they were free for,
  day by day against what the timetable said *on that day*.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, event, inspect, insert, or_, update
from sqlmodel import Session, select

from .models import TimetablePeriod, TimetablePeriodHistory

#: The fields whose change starts a new stretch in the ledger.
_TRACKED = ("teacher_id", "classroom_id", "classroom_subject_id", "day_of_week")

_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _plain(value):
    """An enum member's value, or the value itself."""
    return getattr(value, "value", value)


def _open(connection, period: TimetablePeriod, today: date) -> None:
    table = TimetablePeriodHistory.__table__
    connection.execute(
        insert(table).values(
            id=uuid4(),
            school_id=period.school_id,
            period_id=period.id,
            classroom_id=period.classroom_id,
            classroom_subject_id=period.classroom_subject_id,
            teacher_id=period.teacher_id,
            day_of_week=_plain(period.day_of_week),
            start_time=period.start_time,
            end_time=period.end_time,
            valid_from=today,
            valid_to=None,
        )
    )


def _close(connection, period_id: UUID, today: date) -> None:
    """End the open stretch yesterday.

    A stretch opened today never covered a finished day, so it is removed instead of left
    behind as an empty range.
    """
    table = TimetablePeriodHistory.__table__
    connection.execute(
        delete(table).where(
            table.c.period_id == period_id,
            table.c.valid_to.is_(None),
            table.c.valid_from >= today,
        )
    )
    connection.execute(
        update(table)
        .where(table.c.period_id == period_id, table.c.valid_to.is_(None))
        .values(valid_to=today - timedelta(days=1))
    )


@event.listens_for(TimetablePeriod, "after_insert")
def _slot_placed(mapper, connection, target) -> None:
    _open(connection, target, date.today())


@event.listens_for(TimetablePeriod, "after_update")
def _slot_changed(mapper, connection, target) -> None:
    state = inspect(target)
    if not any(state.attrs[name].history.has_changes() for name in _TRACKED):
        return
    today = date.today()
    _close(connection, target.id, today)
    _open(connection, target, today)


@event.listens_for(TimetablePeriod, "after_delete")
def _slot_cleared(mapper, connection, target) -> None:
    _close(connection, target.id, date.today())


# --- reading ----------------------------------------------------------------


@dataclass
class YearLoad:
    """One teacher's scheduled classes from the first day of the session to a day."""

    #: Classes they actually took: the ones the timetable put them in on open days, less
    #: the ones an approved substitute took over while they were away.
    classes: int = 0
    #: Approved covers they did for an absent colleague, on open days.
    substitutions: int = 0
    #: Lesson slots on open days with neither a class of their own nor a cover - the days
    #: they were simply free.
    free: int = 0
    #: Every lesson slot of those days (open days x the day's lesson slots): the whole
    #: of what a teacher could have been in, the denominator of the utilisation bar.
    capacity: int = 0


def year_load(
    session: Session,
    teacher_ids: list[UUID],
    start: date,
    end: date,
    *,
    slots_per_day: int,
    covers: Iterable[tuple[date, UUID, UUID]] = (),
) -> dict[UUID, YearLoad]:
    """{teacher id: classes, covers and free classes} from `start` to `end`, per open day.

    Only days the school was open count (`calendar.open_days`: weekly offs and holidays are
    out), and a cover can only fall on such a day. For each one:

    * the teacher's **scheduled** classes are the ledger rows whose stretch covers that date
      on that weekday - so a teacher who took over a slot four days ago is credited from
      those four days only, and the one who left keeps the days before;
    * a class they were scheduled for but an approved substitute took over (they were away)
      is **not** a class they took - it counts for the substitute instead;
    * a slot is **free** when it held neither a scheduled class of theirs nor a cover they
      did, and never below zero.

    `covers` is `(date, substitute id, absent teacher id)` per approved cover.
    """
    from app.domains.admin.settings import calendar as school_calendar

    if not teacher_ids or end < start:
        return {}

    open_days = school_calendar.open_days(session, start, end)
    open_set = set(open_days)
    by_weekday: dict[str, list[date]] = defaultdict(list)
    for day in open_days:
        by_weekday[_WEEKDAYS[day.weekday()]].append(day)

    table = TimetablePeriodHistory
    rows = session.exec(
        select(
            table.teacher_id, table.day_of_week, table.valid_from, table.valid_to
        ).where(
            table.teacher_id.in_(teacher_ids),
            table.valid_from <= end,
            or_(table.valid_to.is_(None), table.valid_to >= start),
        )
    ).all()

    scheduled: dict[UUID, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for teacher_id, weekday, valid_from, valid_to in rows:
        for day in by_weekday.get(weekday, ()):
            if valid_from <= day and (valid_to is None or day <= valid_to):
                scheduled[teacher_id][day] += 1

    covered: dict[UUID, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    taken_over: dict[UUID, int] = defaultdict(int)
    for on_date, substitute_id, absent_id in covers:
        if on_date not in open_set:
            continue
        covered[substitute_id][on_date] += 1
        taken_over[absent_id] += 1

    result: dict[UUID, YearLoad] = {}
    for teacher_id in teacher_ids:
        own = scheduled.get(teacher_id, {})
        cover = covered.get(teacher_id, {})
        busy = sum(
            min(own.get(day, 0) + cover.get(day, 0), slots_per_day)
            for day in set(own) | set(cover)
        )
        result[teacher_id] = YearLoad(
            classes=max(sum(own.values()) - taken_over.get(teacher_id, 0), 0),
            substitutions=sum(cover.values()),
            free=max(len(open_days) * slots_per_day - busy, 0),
            capacity=len(open_days) * slots_per_day,
        )
    return result
