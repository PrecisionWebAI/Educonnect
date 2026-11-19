"""The school's calendar - the one place that answers "is this day open?".

The register, the summary, the trend, the attention list, the late card and the section
header all divide by **open days**. The rule used to live inside `attendance`
(`CLOSED_WEEKDAY = 6`), which meant a school that closes on Saturdays could not be
described at all, and every second reader of the rule had to copy both the weekday
number and the holiday query - the surest way to end up with two screens disagreeing
about the same month.

So the two facts live here:

A closed day is a **kind plus a reason**, because the two screens colour differently:

* `weekly_off` - a whole weekday, from `school_setting`
  (`attendance.weekly_off_days`, `"6"` = Sunday only, `"5,6"` = Saturday and Sunday,
  or any other set). One setting for every week, never a row per Sunday.
* `weekly_off`, but only some weeks - `"5#1"` = the **1st Saturday** of every month,
  `"5#3"` the third. A school that works the first Saturday and closes the rest says
  `"5#2,5#3,5#4"` once, instead of adding a row every month.
* `week_off` - a **dated** extra off the school declared as a weekly off in the holiday
  form. It behaves like a Sunday (the register cannot be saved, the day leaves every
  percentage) but it is not a holiday: it is absent from the holiday list and the
  calendar paints it the way it paints a Sunday.
* `holiday` - the `holiday` rows, each covering `on_date` .. `end_date` (a single day
  when `end_date` is empty, so a range may cross a month boundary).
* **open on purpose** - one `school_open_day` row reopens a single date a rule (or a
  holiday) closes. It wins over every other answer, one date at a time.

Two rules keep history honest, and both are the school's own words:

* a **weekly off never takes back a day that already has a register.** The rule is read
  date by date, and a date any class has marked is left open (and keeps counting). So a
  principal who declares "2nd Saturday off" today keeps the 2nd Saturdays already taught,
  and only the ones after them close.
* a date in `school_open_day` is open even though the rule says otherwise - the "just this
  one day" override the calendar offers.

`closure` is the only place that decides *why* a day is closed, and `closed_reason` speaks
the words the screen prints ("Sunday", "1st Saturday", "Diwali break").
"""

from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings.models import Holiday, OpenDay

#: `date.weekday()` order (0 = Monday .. 6 = Sunday) - the order the screen's toggles use.
WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
WEEKDAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

#: The policy key, and what a school gets before it sets anything: Sunday.
KEY_WEEKLY_OFF = "attendance.weekly_off_days"
DEFAULT_WEEKLY_OFF = "6"

#: A closed day's kind - what the calendar colours by, never a string the UI guesses at.
KIND_WEEKLY_OFF = "weekly_off"
KIND_WEEK_OFF = "week_off"
KIND_HOLIDAY = "holiday"

#: `"5#1"` reads "the first Saturday of the month"; the `#` separates the weekday from
#: the week of the month.
NTH_SEPARATOR = "#"
#: The weeks a school may pick. There is no 5th Saturday because most months have none.
NTH_WEEKS = (1, 2, 3, 4)
NTH_ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


class Closure(NamedTuple):
    """Why a day is closed: `kind` picks the colour, `reason` is the words on screen."""

    kind: str
    reason: str


def _tokens(value: str | None) -> list[str]:
    """The stored value as pieces: `"6, 5#1"` -> `["6", "5#1"]`."""
    return [piece for piece in str(value or "").replace(" ", "").split(",") if piece]


def parse_weekly_off(value: str | None) -> set[int]:
    """`"5,6"` -> `{5, 6}`; anything unreadable is ignored, so a bad row cannot close a day.

    A `#` token (`"5#1"`) is not a whole-weekday off, so it is skipped here and read by
    `parse_nth_off` - one stored value, two shapes.
    """
    return {int(piece) for piece in _tokens(value) if piece.isdigit() and 0 <= int(piece) <= 6}


def parse_nth_off(value: str | None) -> dict[int, set[int]]:
    """`"5#1,5#3"` -> `{5: {1, 3}}` - which weeks of the month each weekday is off."""
    rules: dict[int, set[int]] = {}
    for piece in _tokens(value):
        weekday, separator, week = piece.partition(NTH_SEPARATOR)
        if not (separator and weekday.isdigit() and week.isdigit()):
            continue
        day_number, nth = int(weekday), int(week)
        if 0 <= day_number <= 6 and nth in NTH_WEEKS:
            rules.setdefault(day_number, set()).add(nth)
    return rules


def nth_off_tokens(rules: dict[int, set[int]]) -> list[str]:
    """`{5: {3, 1}}` -> `["5#1", "5#3"]` - a stable order, so the stored text never churns."""
    return [
        f"{weekday}{NTH_SEPARATOR}{nth}"
        for weekday in sorted(rules)
        for nth in sorted(rules[weekday])
    ]


def weekly_off_days(session: Session) -> set[int]:
    """The weekdays this school is regularly closed."""
    raw = setting_values.get_value(session, KEY_WEEKLY_OFF, DEFAULT_WEEKLY_OFF)
    return parse_weekly_off(raw)


def nth_off_days(session: Session) -> dict[int, set[int]]:
    """The "1st/2nd/3rd/4th Saturday" rules: `{weekday: {weeks of the month}}`."""
    raw = setting_values.get_value(session, KEY_WEEKLY_OFF, DEFAULT_WEEKLY_OFF)
    return parse_nth_off(raw)


def nth_off_list(session: Session) -> list[str]:
    """The same rules as the API writes them (`["5#1", "5#3"]`)."""
    return nth_off_tokens(nth_off_days(session))


def set_weekly_off_days(
    session: Session, days: list[int], nth: list[str] | None = None
) -> set[int]:
    """Store the school's weekly offs (sorted CSV) and hand back the weekdays stored.

    An empty list is a real answer - a school that runs seven days a week - and is
    stored as an empty value, not as "the default".

    `nth` carries the `"5#1"` Saturday rules. Leaving it `None` **keeps** whatever the
    school already had, so an older caller that only speaks whole weekdays cannot
    quietly wipe the Saturday rules.
    """
    clean = sorted({int(day) for day in days if 0 <= int(day) <= 6})
    if nth is None:
        rules = nth_off_days(session)
    else:
        rules = parse_nth_off(",".join(nth))
    tokens = [str(day) for day in clean] + nth_off_tokens(rules)
    setting_values.set_value(session, KEY_WEEKLY_OFF, ",".join(tokens))
    return set(clean)


def week_of_month(day: date) -> int:
    """Which occurrence of that weekday this day is: 1 for the 1st .. 5 for the 5th."""
    return (day.day - 1) // 7 + 1


def weekly_off_label(weekday: int) -> str:
    """The words the picker prints for a weekly off: "Sunday", "Saturday"."""
    return WEEKDAY_NAMES[weekday] if 0 <= weekday <= 6 else "Weekly off"


def nth_label(weekday: int, nth: int) -> str:
    """`(5, 1)` -> `"1st Saturday"` - the words for a `"5#1"` rule."""
    if not 0 <= weekday <= 6:
        return "Weekly off"
    return f"{NTH_ORDINALS.get(nth, f'{nth}th')} {WEEKDAY_NAMES[weekday]}"


def closure_rows_between(session: Session, start: date, end: date) -> list[Holiday]:
    """Every dated closure row touching `[start, end]`, oldest first.

    That is the holiday rows **and** the extra weekly offs (`kind = "week_off"`), because
    both close a day. Use `holiday_rows_between` when only the holidays are wanted.
    """
    statement = (
        select(Holiday)
        .where(
            Holiday.on_date <= end,
            func.coalesce(Holiday.end_date, Holiday.on_date) >= start,
        )
        .order_by(Holiday.on_date)
    )
    return list(session.exec(statement).all())


def holiday_rows_between(session: Session, start: date, end: date) -> list[Holiday]:
    """The holiday rows only - an extra weekly off closes a day but is not a holiday."""
    return [
        row
        for row in closure_rows_between(session, start, end)
        if row.kind != KIND_WEEK_OFF
    ]


def week_off_rows_between(session: Session, start: date, end: date) -> list[Holiday]:
    """The dated extra weekly offs (the form's `week_off` type) touching the range."""
    return [
        row
        for row in closure_rows_between(session, start, end)
        if row.kind == KIND_WEEK_OFF
    ]


def holiday_on(session: Session, day: date) -> Holiday | None:
    """The closure row covering that day, when there is one (holiday or weekly off)."""
    statement = (
        select(Holiday)
        .where(
            Holiday.on_date <= day,
            func.coalesce(Holiday.end_date, Holiday.on_date) >= day,
        )
        .order_by(Holiday.on_date)
    )
    return session.exec(statement).first()


def _expand(rows: list[Holiday], start: date, end: date) -> dict[date, str]:
    """`{day: row name}` for the rows' range, clipped to `[start, end]`.

    A range row is expanded here and nowhere else, so "24 Dec - 2 Jan" is nine closed
    days for every caller without any of them knowing about `end_date`.
    """
    days: dict[date, str] = {}
    for row in rows:
        first = max(row.on_date, start)
        last = min(row.end_date or row.on_date, end)
        current = first
        while current <= last:
            days.setdefault(current, row.name)
            current += timedelta(days=1)
    return days


def holiday_map(session: Session, start: date, end: date) -> dict[date, str]:
    """`{day: holiday name}` for every **holiday** day inside the range."""
    return _expand(holiday_rows_between(session, start, end), start, end)


def week_off_map(session: Session, start: date, end: date) -> dict[date, str]:
    """`{day: name}` for the extra weekly offs declared through the holiday form."""
    return _expand(week_off_rows_between(session, start, end), start, end)


def open_day_rows(session: Session, start: date, end: date) -> list[OpenDay]:
    """The `school_open_day` rows touching the range, oldest first."""
    statement = (
        select(OpenDay)
        .where(OpenDay.on_date >= start, OpenDay.on_date <= end)
        .order_by(OpenDay.on_date)
    )
    return list(session.exec(statement).all())


def open_day_dates(session: Session, start: date, end: date) -> set[date]:
    """The single dates the school reopened although a rule closes them."""
    return {row.on_date for row in open_day_rows(session, start, end)}


def recorded_dates(session: Session, start: date, end: date) -> set[date]:
    """The days **any** class already has a register on (school-wide).

    The weekly-off rules read this and leave those days open: the school asked that the rule
    never take back a day it has already taught - the marks stay, and they stay inside every
    percentage. It is also why a rule saved today keeps today's 2nd Saturday open and only
    closes the ones after it.

    The import sits inside the function because `attendance` imports this module for every
    count it makes; a module-level import of its models would be a cycle.
    """
    from app.domains.academic.classroom.attendance.models import AttendanceRecord

    day = AttendanceRecord.date
    rows = session.exec(
        select(day).where(day >= start, day <= end).distinct()
    ).all()
    return {value for value in rows if value is not None}


def closures(session: Session, start: date, end: date) -> dict[date, Closure]:
    """`{day: why it is closed}` for the range - one read per source, never a loop of queries.

    The order is the answer's own priority: **open on purpose** (the one-date override) beats
    everything; a whole-weekday off explains the day best, then a "1st Saturday" rule, then
    the holiday (it is the only one with a name the school chose), and a dated weekly off
    last - it says the least about the day, and a weekly off landing on a holiday must not
    hide the holiday's name.

    Both weekly-off shapes skip a day that already has a register: those marks are real, so
    the day is a working day (see `recorded_dates`). A holiday row is *not* protected that
    way - a holiday is a decision taken now, and the calendar makes the office confirm the
    delete before it saves one.
    """
    offs = weekly_off_days(session)
    rules = nth_off_days(session)
    week_offs = week_off_map(session, start, end)
    holidays = holiday_map(session, start, end)
    reopened = open_day_dates(session, start, end)
    recorded = recorded_dates(session, start, end) if (offs or rules) else set()

    days: dict[date, Closure] = {}
    current = start
    while current <= end:
        if current in reopened:
            current += timedelta(days=1)
            continue
        weekday = current.weekday()
        week = week_of_month(current)
        if weekday in offs and current not in recorded:
            days[current] = Closure(KIND_WEEKLY_OFF, weekly_off_label(weekday))
        elif week in rules.get(weekday, set()) and current not in recorded:
            days[current] = Closure(KIND_WEEKLY_OFF, nth_label(weekday, week))
        elif current in holidays:
            days[current] = Closure(KIND_HOLIDAY, holidays[current])
        elif current in week_offs:
            days[current] = Closure(KIND_WEEK_OFF, week_offs[current])
        current += timedelta(days=1)
    return days


def closure(session: Session, day: date) -> Closure | None:
    """Why the school is closed that day, kind and words - `None` on an open day."""
    return closures(session, day, day).get(day)


def closed_reason(session: Session, day: date) -> str | None:
    """Why the school is closed that day ("Sunday", "1st Saturday", "Diwali break")."""
    found = closure(session, day)
    return found.reason if found else None


def closed_kind(session: Session, day: date) -> str | None:
    """`weekly_off` / `week_off` / `holiday` for a closed day - what the calendar colours by."""
    found = closure(session, day)
    return found.kind if found else None


def is_open(session: Session, day: date) -> bool:
    """An open day: no weekly off, no extra weekly off, no holiday."""
    return closure(session, day) is None


def open_days(session: Session, start: date, end: date) -> list[date]:
    """Every open day in the range, oldest first - the denominator every % divides by."""
    closed = closures(session, start, end)
    days: list[date] = []
    current = start
    while current <= end:
        if current not in closed:
            days.append(current)
        current += timedelta(days=1)
    return days


def count_open_days(session: Session, start: date, end: date) -> int:
    """`len(open_days(...))`, for the callers that only need the number."""
    return len(open_days(session, start, end))

