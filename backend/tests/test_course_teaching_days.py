"""Phase 2 - the calendar helper the weekly plans are built on.

The Course plan must never count a day the school is closed, and must count a day it
reopened. The rules are the school's own (Phase 2's calendar), so these tests pin the
wrapper rather than copying the rule:

* the month is cut 1-7 / 8-14 / 15-21 / 22-28 / 29-end, with **no fifth week** unless a
  29th exists (February 2026: four; February 2028: five);
* a Sunday (the default weekly off) and a holiday row are not teaching days;
* a dated `week_off` closes a weekday too;
* a `school_open_day` reopens a Sunday;
* changing `attendance.weekly_off_days` changes the answer without a code change;
* a swapped month/year or a backwards range is refused, not silently answered.
"""

import importlib
from calendar import monthrange
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.course import teaching_days
from app.domains.admin.platform.models import School
from app.domains.admin.settings import calendar, values
from app.domains.admin.settings.models import Holiday, OpenDay


def memory_session() -> Session:
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def seed(session: Session) -> School:
    school = School(name="Calendar School", code="CAL-0001", email="office@cal.test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


def _weekday_in(year: int, month: int, weekday: int) -> date:
    """The first date of that month that falls on `weekday` (0 = Monday)."""
    for day in range(1, monthrange(year, month)[1] + 1):
        candidate = date(year, month, day)
        if candidate.weekday() == weekday:
            return candidate
    raise AssertionError("no such weekday in this month")


def test_the_month_is_cut_into_four_weeks_plus_a_fifth_when_it_has_a_29th():
    with memory_session() as session:
        seed(session)

        november = teaching_days.week_ranges(session, 2026, 11)
        assert [week.week_no for week in november] == [1, 2, 3, 4, 5]
        assert (november[0].start_date, november[0].end_date) == (
            date(2026, 11, 1),
            date(2026, 11, 7),
        )
        assert (november[-1].start_date, november[-1].end_date) == (
            date(2026, 11, 29),
            date(2026, 11, 30),
        )

        february_2026 = teaching_days.week_ranges(session, 2026, 2)
        assert [week.week_no for week in february_2026] == [1, 2, 3, 4]

        february_2028 = teaching_days.week_ranges(session, 2028, 2)
        assert [week.week_no for week in february_2028] == [1, 2, 3, 4, 5]
        assert (february_2028[-1].start_date, february_2028[-1].end_date) == (
            date(2028, 2, 29),
            date(2028, 2, 29),
        )


def test_a_sunday_and_a_holiday_are_not_teaching_days():
    with memory_session() as session:
        seed(session)
        sunday = _weekday_in(2026, 11, 6)
        holiday = _weekday_in(2026, 11, 1)

        before = teaching_days.week_ranges(session, 2026, 11)
        for week in before:
            assert sunday not in week.teaching_days
            assert all(day.weekday() != 6 for day in week.teaching_days)

        session.add(Holiday(on_date=holiday, name="Diwali", kind="public"))
        session.commit()

        after = teaching_days.week_ranges(session, 2026, 11)
        for week in after:
            assert holiday not in week.teaching_days
            assert week.teaching_day_count == len(week.teaching_days)

        assert (
            sum(week.teaching_day_count for week in after)
            == sum(week.teaching_day_count for week in before) - 1
        )


def test_a_dated_week_off_closes_a_weekday():
    with memory_session() as session:
        seed(session)
        weekday = _weekday_in(2026, 11, 2)  # a Tuesday

        session.add(Holiday(on_date=weekday, name="Local holiday", kind="week_off"))
        session.commit()

        weeks = teaching_days.week_ranges(session, 2026, 11)
        assert all(weekday not in week.teaching_days for week in weeks)


def test_a_school_open_day_reopens_a_sunday():
    with memory_session() as session:
        seed(session)
        sunday = _weekday_in(2026, 11, 6)

        session.add(OpenDay(on_date=sunday))
        session.commit()

        weeks = teaching_days.week_ranges(session, 2026, 11)
        assert any(sunday in week.teaching_days for week in weeks)


def test_the_weekly_off_setting_decides_which_days_are_closed():
    with memory_session() as session:
        seed(session)
        saturday = _weekday_in(2026, 11, 5)

        before = teaching_days.get_teaching_days(
            session, date(2026, 11, 1), date(2026, 11, 30)
        )
        assert saturday in before, "the default closes Sunday only"

        values.set_value(session, calendar.KEY_WEEKLY_OFF, "5,6")

        after = teaching_days.get_teaching_days(
            session, date(2026, 11, 1), date(2026, 11, 30)
        )
        assert saturday not in after


def test_bad_input_is_refused():
    with memory_session() as session:
        seed(session)

        for year, month in ((2026, 13), (2026, 0), (1800, 1), (2300, 1)):
            try:
                teaching_days.week_ranges(session, year, month)
            except ValueError:
                pass
            else:  # pragma: no cover - the assertion is the point
                raise AssertionError(f"accepted month {year}-{month}")

        try:
            teaching_days.get_teaching_days(
                session, date(2026, 11, 7), date(2026, 11, 1)
            )
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError("accepted a backwards range")
