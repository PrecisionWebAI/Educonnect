"""The real teaching days of a week - the one calendar the Course plans are built on.

A plan cannot say "this week" and then count a Sunday, a Diwali break or a dated extra
weekly off as a school day. The school's calendar already answers "is this day open?"
in one place (`app/domains/admin/settings/calendar.py`), so this module does not copy the
rule - it wraps it for the Course feature and adds the one thing the plans need: the
month cut into Week 1-5.

* Week 1 = 1-7, Week 2 = 8-14, Week 3 = 15-21, Week 4 = 22-28, and Week 5 = 29-end
  **only when the month actually has a 29th**. February therefore never has a fifth week;
  a leap February does (one day, the 29th).
* `start_date`/`end_date` are the calendar days; `teaching_days` removes the weekly off,
  the holidays and adds back a `school_open_day` override. The plan stores the two dates;
  the days are shown from this calculation, so a corrected holiday is visible at once.

The session is already bound to one school (the tenant listeners), which is why there is
no `school` parameter: `session.info["school_id"]` is the school.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from sqlmodel import Session

from app.domains.admin.settings import calendar

#: The calendar-day span of each week. The last tuple is trimmed to the month's own end.
WEEK_SPANS: tuple[tuple[int, int], ...] = (
    (1, 7),
    (8, 14),
    (15, 21),
    (22, 28),
    (29, 31),
)

#: A sane range for a plan's year. Not a political statement - it catches a swapped
#: month/year (`month=2026`) before it reaches the calendar.
MIN_YEAR = 1900
MAX_YEAR = 2200


@dataclass(frozen=True)
class WeekRange:
    """One week of a month, as the Lesson Plan popup draws it."""

    week_no: int
    start_date: date
    end_date: date
    #: The open days inside the range, oldest first (weekly offs and holidays removed).
    teaching_days: tuple[date, ...]

    @property
    def teaching_day_count(self) -> int:
        """`len(teaching_days)` - what the tab prints next to the range."""
        return len(self.teaching_days)

    @property
    def label(self) -> str:
        """`1 Nov - 7 Nov` - the words above the form."""
        return (
            f"{self.start_date.day} {self.start_date.strftime('%b')} - "
            f"{self.end_date.day} {self.end_date.strftime('%b')}"
        )


def _check_month(year: int, month: int) -> None:
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"year must be between {MIN_YEAR} and {MAX_YEAR}.")
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12.")


def get_teaching_days(session: Session, start: date, end: date) -> list[date]:
    """Every open day in `start..end`, oldest first.

    The school's own calendar decides: the weekly off (`attendance.weekly_off_days`), a
    holiday row or a dated `week_off` closes the day, and a `school_open_day` reopens it.
    """
    if end < start:
        raise ValueError("end must be on or after start.")
    return calendar.open_days(session, start, end)


def teaching_day_count(session: Session, start: date, end: date) -> int:
    """`len(get_teaching_days(...))` for the callers that only need the number."""
    return len(get_teaching_days(session, start, end))


def week_ranges(session: Session, year: int, month: int) -> list[WeekRange]:
    """The month's weeks (1-4, plus 5 when it has a 29th), with their teaching days."""
    _check_month(year, month)
    last_day = monthrange(year, month)[1]

    weeks: list[WeekRange] = []
    for week_no, (first, span_end) in enumerate(WEEK_SPANS, start=1):
        if first > last_day:
            break
        start = date(year, month, first)
        end = date(year, month, min(span_end, last_day))
        weeks.append(
            WeekRange(
                week_no=week_no,
                start_date=start,
                end_date=end,
                teaching_days=tuple(get_teaching_days(session, start, end)),
            )
        )
    return weeks


#: The phase plan's own name for the helper; kept as an alias so a caller can use either.
teaching_days = get_teaching_days
