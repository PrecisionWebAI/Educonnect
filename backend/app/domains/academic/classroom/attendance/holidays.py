"""School-wide holidays: the calendar a school edits, and its weekly off days.

A holiday is **one row** for a single day or a range (`on_date` .. `end_date`), so
"winter break, 24 Dec - 2 Jan" is one entry that may cross a month boundary instead of
nine rows somebody has to edit one by one.

Three rules the routes keep:

* **a day belongs to one closure at most.** An overlapping range is a `409` that names
  the row already there, because two names for one day make every count ambiguous - and
  the table's `UNIQUE (school_id, on_date)` enforces the same rule underneath.
* **a weekly off is not a holiday.** The form's `week_off` type closes a day exactly the
  way a Sunday does, but it is kept out of the holiday list, the holiday counts and the
  holiday colour. The school's *repeating* offs are a setting ("6", "5#1"), never a row
  per month.
* **a weekly off never takes back a day that has a register.** Declaring "2nd Saturday off"
  changes nothing about the 2nd Saturdays already taught: those marks stay, and they stay
  inside every percentage (`admin/settings/calendar.closures` skips a recorded day). The
  rules apply to the days that have no register - in practice the ones still ahead.
* **a holiday (or a dated weekly off) over a saved register is confirmed, then deleted.**
  The form reads the impact first, names the class-sections in the confirm, and only the
  confirm calls `delete_closure_records`. The day then leaves every count, and removing the
  row reopens it with no rows to bring back - which is why the confirm says "cannot be
  undone".
* **one date can be reopened on purpose.** A `school_open_day` row beats every rule for
  that single date (an exam, a make-up class), without unsaving the weekly off.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.core.tenancy import tenant_of
from app.domains.admin.settings import calendar as school_calendar
from app.domains.admin.settings.models import AcademicYear, Holiday, OpenDay
from app.domains.admin.users.models import User

from .models import AttendanceRecord
from .schemas import (
    ClosedDayRead,
    HolidayCalendarRead,
    HolidayImpact,
    HolidayRead,
    HolidaySummaryRead,
    HolidayWrite,
    OpenDayRead,
    OpenDayWrite,
)

#: The kinds the form offers, and the words it prints. A row written before the form
#: existed may carry `festival` or `local`; those keep their own labels on read.
KIND_LABELS: dict[str, str] = {
    "public": "Public holiday",
    "school": "School holiday",
    "vacation": "Vacation",
    "other": "Other",
    "festival": "Festival",
    "local": "Local holiday",
    #: Not a holiday: a dated extra weekly off. It closes the day the way a Sunday does
    #: and is kept out of the holiday list, the holiday counts and the holiday colour.
    "week_off": "Weekly off",
}

#: What a school may write through the API.
WRITABLE_KINDS = {"public", "school", "vacation", "other", "week_off"}

#: The kind that closes a day without being a holiday.
WEEK_OFF_KIND = "week_off"


def _label(kind: str) -> str:
    return KIND_LABELS.get(kind, kind.replace("_", " ").title())


def _read(row: Holiday, names: dict[UUID, str]) -> HolidayRead:
    last = row.end_date or row.on_date
    return HolidayRead(
        id=row.id,
        name=row.name,
        kind=row.kind,
        kind_label=_label(row.kind),
        start_date=row.on_date,
        end_date=last,
        days=(last - row.on_date).days + 1,
        created_by_id=row.created_by_id,
        created_by=names.get(row.created_by_id) if row.created_by_id else None,
    )


def _names(session: Session, rows: list[Holiday] | list[OpenDay]) -> dict[UUID, str]:
    """{user id: name} for the rows' authors - one query for the whole list."""
    ids = {row.created_by_id for row in rows if row.created_by_id}
    if not ids:
        return {}
    users = session.exec(select(User).where(User.id.in_(ids))).all()
    return {user.id: (user.full_name or "") for user in users}


def _open_day_read(row: OpenDay, names: dict[UUID, str]) -> OpenDayRead:
    """One `school_open_day` row as the calendar reads it."""
    return OpenDayRead(
        on_date=row.on_date,
        created_by_id=row.created_by_id,
        created_by=names.get(row.created_by_id) if row.created_by_id else None,
    )


def _saved_register_days(session: Session, start: date, end: date) -> int:
    """How many days in the range already have a register saved (school-wide)."""
    day = AttendanceRecord.date
    total = session.exec(
        select(func.count(func.distinct(day))).where(day >= start, day <= end)
    ).one()
    return int(total or 0)


def _range(payload: HolidayWrite) -> tuple[date, date]:
    """The payload's window, with the ways it can be wrong turned into a 422."""
    start = payload.start_date
    end = payload.end_date or start
    if end < start:
        raise HTTPException(
            status_code=422, detail="A holiday cannot end before it starts."
        )
    if payload.kind not in WRITABLE_KINDS:
        raise HTTPException(
            status_code=422,
            detail=(
                "A holiday is a public holiday, a school holiday, a vacation, other, "
                "or a weekly off."
            ),
        )
    # A weekly off is described by its type, not by a name the school has to invent.
    if payload.kind != WEEK_OFF_KIND and not payload.name.strip():
        raise HTTPException(status_code=422, detail="The holiday needs a name.")
    return start, end


def _name(payload: HolidayWrite) -> str:
    """The row's name - a weekly off falls back to the type's own words."""
    name = payload.name.strip()
    if payload.kind == WEEK_OFF_KIND:
        return name or KIND_LABELS[WEEK_OFF_KIND]
    return name


def _refuse_overlap(
    session: Session, start: date, end: date, exclude_id: UUID | None = None
) -> None:
    """`409` when another closure row already covers part of the range.

    A day belongs to one row, and the database says so too (`UNIQUE (school_id,
    on_date)`), so a weekly off and a holiday cannot share a date: the second one is this
    `409`. That is the useful answer - two names for one day make every count ambiguous,
    and the day is already closed by the first row.
    """
    for row in school_calendar.closure_rows_between(session, start, end):
        if exclude_id is not None and row.id == exclude_id:
            continue
        last = (row.end_date or row.on_date).isoformat()
        raise HTTPException(
            status_code=409,
            detail=(
                f"{row.name} already covers {row.on_date.isoformat()} - {last}. "
                "Edit that one instead of adding a second."
            ),
        )


def _clear_open_days(session: Session, start: date, end: date) -> None:
    """Drop the "just this day open" overrides inside a window that a row now closes.

    A day holds one answer: once a holiday (or a moved holiday) covers the date, an override
    that said "school open anyway" would be a second, contradictory answer - and the row
    would never be reachable again from the screen.
    """
    for row in school_calendar.open_day_rows(session, start, end):
        session.delete(row)


def list_calendar(session: Session, start: date, end: date) -> HolidayCalendarRead:
    """Everything the calendar draws for a window: holidays, weekly offs, marked days.

    The two lists are kept apart on purpose. A holiday is a named event the school
    announces; a weekly off is an ordinary closed day. The calendar paints them
    differently, the list under it shows the holidays only, and the dated weekly offs
    travel in their own list because clicking one of those days reopens (or edits) exactly
    that date.
    """
    rows = school_calendar.holiday_rows_between(session, start, end)
    week_off_rows = school_calendar.week_off_rows_between(session, start, end)
    open_rows = school_calendar.open_day_rows(session, start, end)
    names = _names(session, rows + week_off_rows + open_rows)
    # The shading is the server's own answer, not a copy of the rule: every day `closure()`
    # calls a weekly off (a weekday, a "1st Saturday" rule or a dated extra off).
    closed = school_calendar.closures(session, start, end)
    weekly_off_dates = sorted(
        day
        for day, found in closed.items()
        if found.kind != school_calendar.KIND_HOLIDAY
    )
    day = AttendanceRecord.date
    marked = session.exec(
        select(day).where(day >= start, day <= end).distinct().order_by(day)
    ).all()
    return HolidayCalendarRead(
        from_date=start,
        to_date=end,
        holidays=[_read(row, names) for row in rows],
        weekly_off_days=sorted(school_calendar.weekly_off_days(session)),
        nth_off_days=school_calendar.nth_off_list(session),
        weekly_off_dates=weekly_off_dates,
        week_offs=[_read(row, names) for row in week_off_rows],
        week_off_dates=sorted(school_calendar.week_off_map(session, start, end)),
        open_days=[_open_day_read(row, names) for row in open_rows],
        closed_days=[
            ClosedDayRead(date=day, reason=found.reason, kind=found.kind)
            for day, found in sorted(closed.items())
        ],
        marked_dates=[value for value in marked if value is not None],
        summary=calendar_summary(session),
    )


def create_holiday(
    session: Session, payload: HolidayWrite, user: User | None
) -> HolidayImpact:
    """Add a holiday (single day or range); `409` when it overlaps another one."""
    start, end = _range(payload)
    _refuse_overlap(session, start, end)
    _clear_open_days(session, start, end)

    current_year = session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()
    row = Holiday(
        on_date=start,
        end_date=end if end != start else None,
        name=_name(payload),
        kind=payload.kind,
        created_by_id=user.id if user is not None else None,
        academic_year_id=current_year.id if current_year is not None else None,
        school_id=tenant_of(session),
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    names = {user.id: (user.full_name or "")} if user is not None else {}
    return HolidayImpact(
        holiday=_read(row, names),
        saved_register_days=_saved_register_days(session, start, end),
    )


def get_holiday(session: Session, holiday_id: UUID) -> Holiday:
    """This school's holiday row, or a `404`."""
    row = session.get(Holiday, holiday_id)
    school = tenant_of(session)
    if row is None or (school is not None and row.school_id != school):
        raise HTTPException(status_code=404, detail="Holiday not found")
    return row


def update_holiday(
    session: Session, holiday_id: UUID, payload: HolidayWrite
) -> HolidayImpact:
    """Edit a holiday in place; the same overlap rule applies to the new window."""
    row = get_holiday(session, holiday_id)
    start, end = _range(payload)
    _refuse_overlap(session, start, end, exclude_id=row.id)
    _clear_open_days(session, start, end)

    row.on_date = start
    row.end_date = end if end != start else None
    row.name = _name(payload)
    row.kind = payload.kind
    session.add(row)
    session.commit()
    session.refresh(row)

    return HolidayImpact(
        holiday=_read(row, _names(session, [row])),
        saved_register_days=_saved_register_days(session, start, end),
    )


def delete_holiday(session: Session, holiday_id: UUID) -> None:
    """Remove the holiday. Attendance rows are not touched - the day simply reopens.

    Rows already deleted by the form's own confirm are gone for good: reopening a day shows
    an empty register, not the marks that were cleared when it closed. The override rows
    inside the range go too, because they only ever meant "open although this row closes it".
    """
    row = get_holiday(session, holiday_id)
    _clear_open_days(session, row.on_date, row.end_date or row.on_date)
    session.delete(row)
    session.commit()


def _take_day_out_of_holiday(session: Session, row: Holiday, day: date) -> None:
    """Remove one date from a holiday row: shorten it, delete it, or split it in two."""
    start = row.on_date
    end = row.end_date or row.on_date

    def window(first: date, last: date) -> tuple[date, date | None]:
        return first, (last if last != first else None)

    if start == end:
        session.delete(row)
    elif day == start:
        row.on_date, row.end_date = window(day + timedelta(days=1), end)
        session.add(row)
    elif day == end:
        row.on_date, row.end_date = window(start, day - timedelta(days=1))
        session.add(row)
    else:
        row.on_date, row.end_date = window(start, day - timedelta(days=1))
        session.add(row)
        first, last = window(day + timedelta(days=1), end)
        session.add(
            Holiday(
                on_date=first,
                end_date=last,
                name=row.name,
                kind=row.kind,
                created_by_id=row.created_by_id,
                academic_year_id=row.academic_year_id,
                school_id=row.school_id,
            )
        )


def mark_open_day(
    session: Session, payload: OpenDayWrite, user: User | None
) -> OpenDayRead:
    """Reopen **one** date a weekly off or a holiday closes - the calendar's own override.

    The weekly-off setting is left exactly as it is: the school opens on this date, and
    every other Sunday (or 2nd Saturday) stays closed. A register may then be saved on the
    day, because `closure()` answers `None` for it.

    A **holiday** is different: opening a day takes that day out of the holiday itself.
    A one-day holiday disappears; a range loses its first or last day, or is split in two
    when the day is in the middle (Diwali 6-10, open the 8th -> 6-7 and 9-10). Nothing is
    left behind as an "open on purpose" marker, because no rule closes the day any more.
    If a weekly off still closes it, the usual override row is added.

    Two refusals, both `409`:

    * the day is already open - the row would say nothing at all;
    * the row already exists - one date, one answer.
    """
    day = payload.on_date
    if school_calendar.closure(session, day) is None:
        raise HTTPException(
            status_code=409,
            detail=f"{day.isoformat()} is already an open day - there is nothing to reopen.",
        )
    existing = session.exec(select(OpenDay).where(OpenDay.on_date == day)).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{day.isoformat()} is already open on purpose.",
        )

    holidays = school_calendar.holiday_rows_between(session, day, day)
    if holidays:
        _take_day_out_of_holiday(session, holidays[0], day)
        session.flush()
        if school_calendar.closure(session, day) is None:
            session.commit()
            return OpenDayRead(
                on_date=day,
                created_by_id=user.id if user is not None else None,
                created_by=(user.full_name or "") if user is not None else None,
            )

    row = OpenDay(
        on_date=day,
        created_by_id=user.id if user is not None else None,
        school_id=tenant_of(session),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _open_day_read(row, _names(session, [row]))


def clear_open_day(session: Session, day: date) -> None:
    """Close the date again - the rule takes over exactly as it did before the override."""
    row = session.exec(select(OpenDay).where(OpenDay.on_date == day)).first()
    if row is None:
        raise HTTPException(
            status_code=404, detail="That day was not opened on purpose."
        )
    session.delete(row)
    session.commit()


def calendar_summary(
    session: Session, start: date | None = None, end: date | None = None
) -> HolidaySummaryRead:
    """How many holidays the school declared in a window - the Calendar page's three cards.

    The window is the **current session** when the caller sends none: "how many holidays this
    year" has to mean the school's year (1 Apr - 31 Mar), not January's. Without a session row
    it falls back to the calendar year, and `session_label` says which window answered.

    A weekly off is **not** counted: it closes a day, but it is not a holiday, and a card that
    counted both would make the holiday list disagree with the figure above it.
    """
    label = ""
    if start is None or end is None:
        year = session.exec(
            select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
        ).first()
        if year is not None:
            start, end, label = year.start_date, year.end_date, year.name
        else:
            today = date.today()
            start, end = date(today.year, 1, 1), date(today.year, 12, 31)

    rows = school_calendar.holiday_rows_between(session, start, end)
    counts = {"public": 0, "school": 0, "vacation": 0, "other": 0}
    vacation_days = 0
    for row in rows:
        kind = row.kind if row.kind in counts else "other"
        counts[kind] += 1
        if kind != "vacation":
            continue
        # The days of the break that fall inside the window, counted once.
        first = max(row.on_date, start)
        last = min(row.end_date or row.on_date, end)
        if last >= first:
            vacation_days += (last - first).days + 1

    return HolidaySummaryRead(
        from_date=start,
        to_date=end,
        session_label=label,
        total=len(rows),
        public=counts["public"],
        school=counts["school"],
        vacation=counts["vacation"],
        other=counts["other"],
        vacation_days=vacation_days,
    )


def weekly_off(session: Session) -> list[int]:
    """The school's weekly off days, `date.weekday()` order (0 = Monday)."""
    return sorted(school_calendar.weekly_off_days(session))


def nth_off(session: Session) -> list[str]:
    """The Saturday rules as `"5#1"` tokens (the 1st Saturday of every month)."""
    return school_calendar.nth_off_list(session)


def set_weekly_off(
    session: Session, days: list[int], nth: list[str] | None = None
) -> list[int]:
    """Store the weekly off days; an empty list is a real answer (open seven days).

    `nth` carries the Saturday rules. `None` keeps whatever is stored, so a caller that
    only speaks whole weekdays cannot wipe a school's "2nd and 4th Saturday" setting.
    """
    return sorted(school_calendar.set_weekly_off_days(session, days, nth))
