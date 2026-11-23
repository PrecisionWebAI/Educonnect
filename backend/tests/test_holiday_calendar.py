"""Phase 3.5 - the school's calendar: weekly offs, holiday ranges, and open days.

The register's numbers are only as honest as its definition of "open day". That
definition used to be a constant inside `attendance` (`CLOSED_WEEKDAY = 6`), so a school
that closes on Saturdays could not be described, and every second reader of the rule
would have had to copy it. These scenarios pin the replacement:

1. the **weekly off setting** decides which weekdays are closed, and changing it changes
   every open-day count at once;
2. a **holiday range** may cross a month boundary and is still one row;
3. a **second holiday on the same day** is refused with `409` (one day, one name);
4. a holiday over an **already saved register** keeps the rows, reports how many days it
   covers, and takes those days out of every count - until it is removed again;
5. the **register, the summary and the trend** all read the same calendar;
6. the whole calendar page is `holiday.manage` - the principal and above hold it, a teacher
   does not - while the register keeps its own `attendance.read` reads;
7. a **weekly off never takes back a day that already has a register**, and **one date can
   be reopened on purpose** without unsaving the rule.

Runs under pytest and as `python tests/test_holiday_calendar.py`.
"""

import importlib
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import service as classroom_service
from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance import holidays as holiday_service
from app.domains.academic.classroom.attendance import register as register_service
from app.domains.academic.classroom.attendance import router as attendance_router
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.attendance.schemas import (
    AttendanceBulkCreate,
    AttendanceRowWrite,
    ClosureDeleteWrite,
    HolidayWrite,
    OpenDayWrite,
    WeeklyOffWrite,
)
from app.domains.academic.classroom.students import service as student_service
from app.domains.academic.classroom.students.schemas import StudentCreate
from app.domains.admin.platform.models import School
from app.domains.admin.settings import calendar as school_calendar
from app.domains.admin.settings import values as setting_values
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission
from app.domains.auth.permissions import ROLE_PERMISSIONS_MAP

# Fixed weekdays, so nothing depends on when the suite ran.
MON = date(2026, 11, 16)
TUE = date(2026, 11, 17)
WED = date(2026, 11, 18)
THU = date(2026, 11, 19)
FRI = date(2026, 11, 20)
SAT = date(2026, 11, 21)
SUN = date(2026, 11, 22)

# A winter break that starts in one month and ends in the next.
BREAK_START = date(2026, 12, 28)
BREAK_END = date(2027, 1, 3)


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


def _school(session: Session) -> School:
    school = School(name="calendar school", code="cal", email="cal@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


def _room(session: Session):
    klass = ClassName(classname="Class 6", level=6)
    section = Section(section_name="A")
    session.add(klass)
    session.add(section)
    session.commit()
    session.refresh(klass)
    session.refresh(section)
    return ensure_room(session, klass.class_id, section.section_id)


def _student(session: Session, name: str, number: str, room):
    return student_service.create_student(
        session,
        StudentCreate(
            full_name=name,
            gender="Female",
            admission_number=number,
            classroom_id=room.id,
        ),
    )


def _office(session: Session) -> User:
    user = User(email="principal@test", full_name="the principal", hashed_password="pw")
    user._role_names = {"principal"}
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed(session: Session) -> dict:
    """One school, one class-section with two children, and a principal."""
    _school(session)
    room = _room(session)
    return {
        "room": room,
        "aarav": _student(session, "aarav sharma", "C-1", room),
        "diya": _student(session, "diya patel", "C-2", room),
        "office": _office(session),
    }


def _add(session, name, start, end=None, kind="public"):
    return holiday_service.create_holiday(
        session,
        HolidayWrite(name=name, kind=kind, start_date=start, end_date=end),
        user=None,
    )


def test_open_days_follow_the_weekly_off_setting() -> None:
    """Saturday off is one setting, not a row per Saturday."""
    with memory_session() as session:
        seed(session)

        # The default: Sunday only -> six open days in this week.
        assert school_calendar.weekly_off_days(session) == {6}
        week = school_calendar.open_days(session, MON, SUN)
        assert len(week) == 6
        assert SUN not in week and SAT in week

        # The school says Saturday is off too.
        assert holiday_service.set_weekly_off(session, [5, 6]) == [5, 6]
        week = school_calendar.open_days(session, MON, SUN)
        assert len(week) == 5
        assert SAT not in week and SUN not in week
        assert school_calendar.closed_reason(session, SAT) == "Saturday"

        # A school that runs seven days a week can say that too.
        assert holiday_service.set_weekly_off(session, []) == []
        assert len(school_calendar.open_days(session, MON, SUN)) == 7


def test_a_holiday_range_can_cross_a_month() -> None:
    """24 Dec - 2 Jan is one row, and every day in it is closed."""
    with memory_session() as session:
        seed(session)
        impact = _add(session, "winter break", BREAK_START, BREAK_END, kind="vacation")

        assert impact.holiday.days == 7
        assert impact.holiday.start_date == BREAK_START
        assert impact.holiday.end_date == BREAK_END
        assert impact.saved_register_days == 0

        closed = school_calendar.holiday_map(
            session, date(2026, 12, 20), date(2027, 1, 10)
        )
        assert len(closed) == 7
        assert closed[date(2026, 12, 28)] == "winter break"
        assert closed[date(2027, 1, 1)] == "winter break"
        assert date(2026, 12, 27) not in closed

        # The open day count skips the whole break, and the Sunday beside it.
        open_days = school_calendar.open_days(
            session, date(2027, 1, 3), date(2027, 1, 7)
        )
        # 3 Jan is the last day of the break (and a Sunday); the rest of that week
        # is open.
        assert open_days == [
            date(2027, 1, 4),
            date(2027, 1, 5),
            date(2027, 1, 6),
            date(2027, 1, 7),
        ]


def test_a_second_holiday_on_the_same_day_is_refused() -> None:
    with memory_session() as session:
        seed(session)
        _add(session, "diwali", WED)

        with pytest.raises(HTTPException) as caught:
            _add(session, "diwali again", WED)
        assert caught.value.status_code == 409
        assert "diwali" in caught.value.detail

        # A range that merely touches the day is refused as well.
        with pytest.raises(HTTPException) as caught:
            _add(session, "autumn break", TUE, THU)
        assert caught.value.status_code == 409


def test_a_holiday_over_a_saved_register_keeps_the_rows_and_leaves_the_counts() -> None:
    """The most important rule: warn about the register, never delete it."""
    with memory_session() as session:
        data = seed(session)
        room, office = data["room"], data["office"]
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=MON,
                records=[
                    AttendanceRowWrite(student_id=data["aarav"].id, status="present"),
                    AttendanceRowWrite(student_id=data["diya"].id, status="absent"),
                ],
            ),
            user=office,
        )

        before = register_service.section_summary(session, room.id, MON, SUN)
        assert before.working_days == 6

        impact = _add(session, "school closed", MON)
        assert impact.saved_register_days == 1, "the office must be warned"

        # 1. the rows are still there
        rows = list(session.exec(select(AttendanceRecord)).all())
        assert len(rows) == 2

        # 2. the day has left every count
        after = register_service.section_summary(session, room.id, MON, SUN)
        assert after.working_days == 5
        assert all(row.marked == 0 for row in after.rows)
        assert register_service.closed_reason(session, MON) == "school closed"

        # 3. saving a register on the day is refused, naming the holiday
        with pytest.raises(HTTPException) as caught:
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=MON,
                    records=[
                        AttendanceRowWrite(student_id=data["aarav"].id, status="late")
                    ],
                ),
                user=office,
            )
        assert caught.value.status_code == 409
        assert "school closed" in caught.value.detail

        # 4. removing the holiday brings the day back, rows and all
        holiday_service.delete_holiday(session, impact.holiday.id)
        back = register_service.section_summary(session, room.id, MON, SUN)
        assert back.working_days == 6
        assert len(list(session.exec(select(AttendanceRecord)).all())) == 2


def test_the_register_summary_and_trend_share_one_calendar() -> None:
    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        _add(session, "diwali", WED)

        closed = register_service.closed_days(session, MON, SUN)
        reasons = {day.date: day.reason for day in closed}
        assert reasons[WED] == "diwali"
        assert reasons[SUN] == "Sunday"
        assert SAT not in reasons, "Saturday is open on the default setting"

        summary = register_service.section_summary(session, room.id, MON, SUN)
        assert summary.working_days == len(school_calendar.open_days(session, MON, SUN))

        trend = register_service.section_trend(session, room.id, days=7, end=SUN)
        drawn = {point.date for point in trend.points}
        assert WED not in drawn, "a holiday is not drawn as 0%"
        assert SUN not in drawn
        assert MON in drawn, "an unmarked open day is still a day"


def test_only_the_office_may_edit_or_read_the_calendar() -> None:
    """The whole calendar is the office's: `holiday.manage` on every route of it."""
    for role in ("principal", "school_admin", "system_admin"):
        assert "holiday.manage" in ROLE_PERMISSIONS_MAP.get(role, []), role
    for role in ("vice_principal", "hod", "teacher", "student", "guardian"):
        assert "holiday.manage" not in ROLE_PERMISSIONS_MAP.get(role, []), role

    writes = {
        "/holidays",
        "/holidays/{holiday_id}",
        "/weekly-off",
        "/open-days",
        "/open-days/{on_date}",
    }
    found: dict[tuple[str, str], set[str]] = {}
    for route in attendance_router.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path not in writes:
            continue
        guards = {
            dependency.call.permission
            for dependency in route.dependant.dependencies
            if isinstance(dependency.call, RequirePermission)
        }
        for method in methods:
            found[(method, path)] = guards

    for key in (
        ("POST", "/holidays"),
        ("PATCH", "/holidays/{holiday_id}"),
        ("DELETE", "/holidays/{holiday_id}"),
        ("PUT", "/weekly-off"),
        ("POST", "/open-days"),
        ("DELETE", "/open-days/{on_date}"),
        ("GET", "/holidays"),
        ("GET", "/weekly-off"),
    ):
        assert found.get(key) == {"holiday.manage"}, key


def test_the_weekly_off_route_keeps_the_saturday_rule() -> None:
    """The HTTP write the screen uses: `{days, nth}` in, the same rules out.

    The service test proves the arithmetic; this one proves the **route** does not drop the
    field on the way through - which is exactly what a stale API build does, and what makes a
    "2nd/4th Saturday" rule look saved but leave the calendar unshaded.
    """
    with memory_session() as session:
        data = seed(session)
        office = data["office"]

        written = attendance_router.write_weekly_off(
            payload=WeeklyOffWrite(days=[6], nth=["5#2", "5#4"]),
            session=session,
            current_user=office,
        )
        assert written.days == [6]
        assert written.nth == ["5#2", "5#4"]

        read_back = attendance_router.read_weekly_off(
            session=session, current_user=office
        )
        assert read_back.days == [6]
        assert read_back.nth == ["5#2", "5#4"]

        # And the calendar the screen draws is told which Saturdays those are.
        calendar = holiday_service.list_calendar(
            session, date(2026, 11, 1), date(2026, 11, 30)
        )
        assert date(2026, 11, 14) in calendar.weekly_off_dates, "the 2nd Saturday"
        assert date(2026, 11, 28) in calendar.weekly_off_dates, "the 4th Saturday"
        assert date(2026, 11, 7) not in calendar.weekly_off_dates, (
            "the 1st Saturday is open"
        )
        assert date(2026, 11, 21) not in calendar.weekly_off_dates, (
            "the 3rd Saturday is open"
        )


def test_the_calendar_summary_counts_holidays_and_vacation_days() -> None:
    """The three cards: holiday rows, public holidays, and vacation **days**.

    A weekly off is not a holiday and a 5-day vacation is 5 days, not 1 - the two mistakes
    that would make the card disagree with the list under it.
    """
    with memory_session() as session:
        _school(session)
        _add(session, "diwali", date(2026, 11, 8))  # public, one day
        _add(session, "sports day", date(2026, 11, 20), kind="school")
        _add(
            session,
            "winter break",
            date(2026, 12, 28),
            date(2027, 1, 1),
            kind="vacation",
        )
        _add(
            session, "", date(2026, 11, 21), kind="week_off"
        )  # a closure, not a holiday

        summary = holiday_service.calendar_summary(
            session, date(2026, 11, 1), date(2026, 12, 31)
        )
        assert summary.total == 3, "the weekly off is not a holiday"
        assert summary.public == 1
        assert summary.school == 1
        assert summary.vacation == 1
        assert summary.vacation_days == 4, (
            "28-31 Dec: the break is clipped to the window"
        )
        assert summary.session_label == "", "an explicit window is not a session"

        # The whole break inside a window that holds all of it: five days.
        whole = holiday_service.calendar_summary(
            session, date(2026, 12, 1), date(2027, 1, 31)
        )
        assert whole.vacation_days == 5, "28 Dec - 1 Jan is five days"

        # A window that starts inside the break counts only the days it holds.
        clipped = holiday_service.calendar_summary(
            session, date(2026, 12, 30), date(2027, 1, 31)
        )
        assert clipped.vacation == 1
        assert clipped.vacation_days == 3, "30, 31 Dec and 1 Jan"


def test_a_closure_lists_the_sections_that_would_lose_their_register() -> None:
    """The warning names the class-sections, and the delete only happens when asked.

    `closure_impact` reads; `delete_closure_records` writes. Saving a holiday must never be
    the thing that removes a register - the office has to confirm it.
    """
    with memory_session() as session:
        data = seed(session)
        room, aarav, diya, office = (
            data["room"],
            data["aarav"],
            data["diya"],
            data["office"],
        )
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=MON,
                records=[
                    AttendanceRowWrite(student_id=aarav.id, status="present"),
                    AttendanceRowWrite(student_id=diya.id, status="absent"),
                ],
            ),
            user=office,
        )

        impact = register_service.closure_impact(session, MON, SUN)
        assert impact.total_records == 2
        day = impact.days[0]
        assert day.date == MON
        assert day.total_records == 2
        assert len(day.sections) == 1
        section = day.sections[0]
        assert (section.class_name, section.section_name) == ("Class 6", "A")
        assert section.students == 2, "two children hold a mark"
        assert section.records == 2
        assert impact.days == [day], "only the day with a register is reported"

        # A proposed weekly off deletes nothing: the rule skips a day that already has a
        # register, so the preview stays empty even for a Monday that is marked.
        preview = register_service.weekly_off_impact(session, MON, SUN, [0], [])
        assert preview.total_records == 0
        assert preview.days == []

        # Reading twice changes nothing; only the explicit delete removes rows.
        assert register_service.closure_impact(session, MON, SUN).total_records == 2
        removed = register_service.delete_closure_records(
            session, ClosureDeleteWrite(from_date=MON, to_date=MON)
        )
        assert removed.deleted_records == 2
        assert removed.days == [MON]
        assert register_service.register(session, room.id, MON).counts.unmarked == 2
        assert register_service.closure_impact(session, MON, SUN).total_records == 0

        # `dates` clears exactly those days: a weekly-off preview must never widen to a range.
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=WED,
                records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
            ),
            user=office,
        )
        untouched = register_service.delete_closure_records(
            session, ClosureDeleteWrite(dates=[TUE])
        )
        assert untouched.deleted_records == 0, "Tuesday has no register"
        assert register_service.register(session, room.id, WED).counts.present == 1
        exact = register_service.delete_closure_records(
            session, ClosureDeleteWrite(dates=[WED])
        )
        assert exact.deleted_records == 1


def test_percentage_divides_by_open_days_not_by_marked_days() -> None:
    """One present mark in a four-day week is 25%, and a holiday shrinks the base."""
    with memory_session() as session:
        data = seed(session)
        room, aarav, office = data["room"], data["aarav"], data["office"]
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=MON,
                records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
            ),
            user=office,
        )

        summary = register_service.section_summary(session, room.id, MON, THU)
        row = {item.student_id: item for item in summary.rows}[aarav.id]
        assert summary.working_days == 4
        assert (row.present, row.marked) == (1, 1)
        assert row.percent == 25.0, "the denominator is the four open days"

        # A holiday takes a day out of the base - the mark itself is untouched.
        _add(session, "diwali", THU)
        after = register_service.section_summary(session, room.id, MON, THU)
        assert after.working_days == 3
        assert {item.student_id: item for item in after.rows}[aarav.id].percent == 33.3
        assert len(list(session.exec(select(AttendanceRecord)).all())) == 1


def test_the_trend_can_end_on_the_day_being_looked_at() -> None:
    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        trend = register_service.section_trend(session, room.id, days=7, end=WED)
        # One point per **open** day: 12-18 Nov has six of them (the 15th is a Sunday).
        assert trend.points[-1].date == WED
        assert trend.points[0].date == date(2026, 11, 12), "six days back, WED included"
        assert len(trend.points) == 6


def test_the_summary_window_is_the_register_itself() -> None:
    """No dates given: the window starts where the class's register starts."""
    with memory_session() as session:
        data = seed(session)
        room, aarav, office = data["room"], data["aarav"], data["office"]

        empty = register_service.section_summary(session, room.id)
        assert empty.rows == [], "nothing saved yet is an empty table, not an error"
        assert empty.working_days == 0

        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=WED,
                records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
            ),
            user=office,
        )

        summary = register_service.section_summary(session, room.id, None, WED)
        assert summary.from_date == WED, "the first saved day, not the 1st of the month"
        assert summary.to_date == WED, "one saved day means a one-day window"
        assert summary.working_days == 1
        row = {item.student_id: item for item in summary.rows}[aarav.id]
        assert row.present_total == 1
        assert row.percent == 100.0


def test_the_summary_stops_at_the_cutoff_not_at_the_clock() -> None:
    """Today counts once it has a register; a day that has passed counts either way.

    Monday and Tuesday are marked. On Wednesday morning the cutoff is Tuesday, so the
    child is at 100% and the day nobody has reached is not judged. Marking Wednesday moves
    the cutoff with it; letting Thursday pass without a register makes *that* day an
    absence, because the school was open and nobody marked it.
    """
    with memory_session() as session:
        data = seed(session)
        room, aarav, office = data["room"], data["aarav"], data["office"]
        for day in (MON, TUE):
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=day,
                    records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
                ),
                user=office,
            )

        # Wednesday is "today" and holds no register yet: the cutoff is Tuesday.
        summary = register_service.section_summary(session, room.id, today=WED)
        assert summary.from_date == MON
        assert summary.to_date == TUE, "a day still waiting to be marked is not judged"
        assert summary.working_days == 2
        row = {item.student_id: item for item in summary.rows}[aarav.id]
        assert row.percent == 100.0, "an unreached day cannot pull this down"

        # Marking Wednesday moves the cutoff with it - and only then.
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=WED,
                records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
            ),
            user=office,
        )
        marked = register_service.section_summary(session, room.id, today=WED)
        assert marked.to_date == WED
        assert marked.working_days == 3
        assert {item.student_id: item for item in marked.rows}[
            aarav.id
        ].percent == 100.0

        # Thursday passes with no register at all: the school was open, so it counts.
        passed = register_service.section_summary(session, room.id, today=FRI)
        assert passed.to_date == THU, "yesterday, because today has no register yet"
        assert passed.working_days == 4
        assert {item.student_id: item for item in passed.rows}[aarav.id].percent == 75.0


def test_the_header_figure_is_the_rows_figure() -> None:
    """The card on top and the rows inside the tab read one month, one calendar, one formula."""
    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        aarav, diya, office = data["aarav"], data["diya"], data["office"]
        for day, statuses in (
            (MON, ("present", "present")),
            (TUE, ("present", "present")),
            (WED, ("absent", "present")),
        ):
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=day,
                    records=[
                        AttendanceRowWrite(student_id=aarav.id, status=statuses[0]),
                        AttendanceRowWrite(student_id=diya.id, status=statuses[1]),
                    ],
                ),
                user=office,
            )

        percent, open_days = register_service.section_month(session, room.id)
        assert open_days == 3
        # Five present-or-late marks over three open days for two children.
        assert percent == 83.3

        # The rows below count the very same five marks, so the header cannot disagree.
        summary = register_service.section_summary(session, room.id)
        month_present = sum(row.month_present_total for row in summary.rows)
        assert month_present == 5
        assert (
            round(month_present * 100 / (open_days * len(summary.rows)), 1) == percent
        )

        # The drill-down the page actually reads carries both numbers.
        detail = classroom_service.section_detail(session, room.id)
        assert detail.attendanceOpenDays == 3
        assert detail.attendancePercent == 83.3

        # A holiday over one of those days takes the marks with it, on both screens:
        # Monday and Wednesday stay open, so three attended marks over 2 x 2.
        _add(session, "diwali", TUE)
        percent, open_days = register_service.section_month(session, room.id)
        assert open_days == 2
        assert percent == 75.0


def test_a_section_without_a_register_has_no_header_figure() -> None:
    """No register is not 0% - the card prints a dash and says so."""
    with memory_session() as session:
        data = seed(session)
        assert register_service.section_month(session, data["room"].id) == (None, 0)

    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        aarav, diya, office = data["aarav"], data["diya"], data["office"]
        for day, student in ((MON, aarav), (WED, diya)):
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=day,
                    records=[
                        AttendanceRowWrite(student_id=student.id, status="present")
                    ],
                ),
                user=office,
            )

        summary = register_service.section_summary(session, room.id, None, WED)
        rows = {item.student_id: item for item in summary.rows}
        # Aarav has been on the roll since Monday (three open days); diya was first marked
        # on Wednesday, so her own denominator is the one open day since.
        assert summary.working_days == 3
        assert rows[aarav.id].open_days == 3
        assert rows[aarav.id].percent == 33.3
        assert rows[diya.id].open_days == 1, "a later start is not a penalty"
        assert rows[diya.id].percent == 100.0


def test_late_students_last_month() -> None:
    """Two late days in a 25-day month is 8% - over the 5% bar; one day is not."""
    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        aarav, diya, office = data["aarav"], data["diya"], data["office"]
        late_days = [date(2026, 11, 3), date(2026, 11, 4), date(2026, 11, 5)]
        # Aarav is late on the first two days, diya only on the first; both present after.
        for index, day in enumerate(late_days):
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=day,
                    records=[
                        AttendanceRowWrite(
                            student_id=aarav.id,
                            status="late" if index < 2 else "present",
                        ),
                        AttendanceRowWrite(
                            student_id=diya.id,
                            status="late" if index == 0 else "present",
                        ),
                    ],
                ),
                user=office,
            )

        # The default bar is 10%: aarav was late 2 of 25 open days (8%), so nobody is listed.
        default_bar = register_service.late_students_last_month(
            session, room.id, today=date(2026, 12, 10)
        )
        assert default_bar.threshold == 10 and default_bar.rows == []

        # A school that wants a stricter bar sets it.
        setting_values.set_value(session, "attendance.late_share_percent", 5)
        late_list = register_service.late_students_last_month(
            session, room.id, today=date(2026, 12, 10)
        )
        assert late_list.month_label == "November 2026"
        assert late_list.open_days == 25, "30 days minus the five Sundays"
        assert late_list.marked_days == 3
        assert late_list.threshold == 5
        assert [row.student_id for row in late_list.rows] == [aarav.id]
        assert late_list.rows[0].late == 2
        assert late_list.rows[0].percent == 8.0

        # The bar is one setting, so the school can raise it.
        setting_values.set_value(session, "attendance.late_share_percent", 30)
        strict = register_service.late_students_last_month(
            session, room.id, today=date(2026, 12, 10)
        )
        assert strict.rows == []


def test_late_list_without_data_is_empty_not_an_error() -> None:
    with memory_session() as session:
        data = seed(session)
        late_list = register_service.late_students_last_month(
            session, data["room"].id, today=date(2026, 12, 10)
        )
        assert late_list.rows == []
        assert late_list.marked_days == 0
        assert late_list.open_days == 25


# ---------------------------------------------------------------------------
# Phase 7: the form's "week off" type, the Saturday rule, and the two figures
# ---------------------------------------------------------------------------


def test_a_week_off_type_closes_the_day_without_becoming_a_holiday() -> None:
    """`kind="week_off"` behaves like a Sunday and stays out of the holiday list."""
    with memory_session() as session:
        data = seed(session)
        room, aarav, office = data["room"], data["aarav"], data["office"]

        # No name is needed for this kind - the type already says what it is.
        impact = _add(session, "", SAT, kind="week_off")
        assert impact.holiday.name == "Weekly off"

        calendar = holiday_service.list_calendar(session, MON, SUN)
        assert calendar.holidays == [], "a weekly off is not a holiday"
        assert [row.kind for row in calendar.week_offs] == ["week_off"]
        assert calendar.week_off_dates == [SAT]
        assert SAT in calendar.weekly_off_dates, "the calendar shades it like a Sunday"
        assert SUN in calendar.weekly_off_dates

        assert school_calendar.closed_reason(session, SAT) == "Weekly off"
        assert school_calendar.closed_kind(session, SAT) == "week_off"
        assert school_calendar.is_open(session, SAT) is False

        # Saturday leaves the open days exactly the way Sunday does.
        assert SAT not in school_calendar.open_days(session, MON, SUN)
        assert len(school_calendar.open_days(session, MON, SUN)) == 5

        closed = register_service.closed_days(session, MON, SUN)
        assert [(day.date, day.kind) for day in closed] == [
            (SAT, "week_off"),
            (SUN, "weekly_off"),
        ]

        # And the register refuses it with the same words the calendar prints.
        with pytest.raises(HTTPException) as refused:
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=SAT,
                    records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
                ),
                user=office,
            )
        assert refused.value.status_code == 409
        assert "Weekly off" in refused.value.detail

        # Deleting it reopens the day; nothing else is touched.
        holiday_service.delete_holiday(session, impact.holiday.id)
        assert school_calendar.is_open(session, SAT) is True


def test_a_weekly_off_cannot_share_a_day_with_a_holiday() -> None:
    """One day, one closure row - the same rule the table's unique key enforces."""
    with memory_session() as session:
        seed(session)
        _add(session, "diwali", SAT)

        with pytest.raises(HTTPException) as refused:
            _add(session, "", SAT, kind="week_off")
        assert refused.value.status_code == 409
        assert "diwali" in refused.value.detail

        # The holiday keeps the day, its name and its colour.
        assert school_calendar.closed_reason(session, SAT) == "diwali"
        assert school_calendar.closed_kind(session, SAT) == "holiday"


def test_the_nth_saturday_rule_closes_only_that_week() -> None:
    """`"5#1"` is one setting for every month - never a row per Saturday."""
    with memory_session() as session:
        seed(session)
        first_saturday = date(2026, 11, 7)
        second_saturday = date(2026, 11, 14)
        assert SAT == date(2026, 11, 21), "the third Saturday of November 2026"

        assert holiday_service.set_weekly_off(session, [6], ["5#1"]) == [6]
        assert school_calendar.nth_off_list(session) == ["5#1"]

        assert school_calendar.closed_reason(session, first_saturday) == "1st Saturday"
        assert school_calendar.closed_kind(session, first_saturday) == "weekly_off"
        assert school_calendar.is_open(session, second_saturday) is True
        assert school_calendar.is_open(session, SAT) is True

        # One week: Mon-Fri open, the 1st Saturday and the Sunday closed.
        week = [date(2026, 11, day) for day in (2, 3, 4, 5, 6, 7, 8)]
        assert [day for day in week if school_calendar.is_open(session, day)] == week[
            :5
        ]

        # And the calendar is told which days to shade, so the screen never redoes the maths.
        calendar = holiday_service.list_calendar(session, week[0], week[-1])
        assert first_saturday in calendar.weekly_off_dates
        assert week[-1] in calendar.weekly_off_dates, "the Sunday is still a weekly off"
        assert second_saturday not in calendar.weekly_off_dates

        # A payload without `nth` keeps the rule the school already had.
        holiday_service.set_weekly_off(session, [6])
        assert school_calendar.nth_off_list(session) == ["5#1"]

        # The rule is a setting, so turning it off reopens the Saturdays.
        holiday_service.set_weekly_off(session, [6], [])
        assert school_calendar.is_open(session, first_saturday) is True


def test_the_register_calendar_marks_closed_and_saved_days() -> None:
    """One read gives the month calendar its colours and its saved-register dots."""
    with memory_session() as session:
        data = seed(session)
        room, aarav, office = data["room"], data["aarav"], data["office"]
        _add(session, "", SAT, kind="week_off")
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=MON,
                records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
            ),
            user=office,
        )

        calendar = register_service.section_calendar(session, room.id, MON, SUN)
        assert (calendar.from_date, calendar.to_date) == (MON, SUN)
        assert len(calendar.days) == 7, "one row per calendar day"
        days = {day.date: day for day in calendar.days}

        assert days[MON].saved is True
        assert days[MON].closed_kind is None, "a saved day is an open day"
        assert days[TUE].saved is False
        assert days[SAT].closed_kind == "week_off"
        assert days[SAT].closed_reason == "Weekly off"
        assert days[SUN].closed_kind == "weekly_off"
        assert days[SUN].closed_reason == "Sunday"


def test_the_month_fraction_divides_by_the_months_open_days() -> None:
    """`Monthly attendance 5/12`: present-and-late over the month's open days.

    The denominator is the calendar's open days up to the month's cutoff - never the count
    of registers somebody remembered to take - because "10 of the 22 days we were open" is
    what the office needs, and "10 of the 10 days I marked" flatters every gap. A month
    nobody took a register in keeps its open days but reports `month_saved == 0`, which is
    what makes the row print a dash instead of `0/27`.
    """
    with memory_session() as session:
        data = seed(session)
        room = data["room"]
        aarav, diya, office = data["aarav"], data["diya"], data["office"]

        marks = {
            MON: ("present", "present"),
            TUE: ("present", "present"),
            WED: ("absent", "present"),
        }
        for day, (aarav_status, diya_status) in marks.items():
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=day,
                    records=[
                        AttendanceRowWrite(student_id=aarav.id, status=aarav_status),
                        AttendanceRowWrite(student_id=diya.id, status=diya_status),
                    ],
                ),
                user=office,
            )

        # Wednesday is today and it is saved: the month runs over its three open days.
        summary = register_service.section_summary(
            session, room.id, until=WED, month=WED, today=WED
        )
        rows = {row.student_id: row for row in summary.rows}
        assert {row.month_open_days for row in summary.rows} == {3}
        assert rows[aarav.id].month_present_total == 2
        assert rows[diya.id].month_present_total == 3
        assert {row.month_saved for row in summary.rows} == {3}

        # The day on screen stops the month on Tuesday - and the annual figure does not
        # rewind with it: the year always ends on the cutoff, which is what "as of today"
        # means. Only the month follows the date the reader picked.
        earlier = register_service.section_summary(
            session, room.id, until=TUE, month=WED, today=WED
        )
        earlier_rows = {row.student_id: row for row in earlier.rows}
        assert {row.month_open_days for row in earlier.rows} == {2}
        assert earlier_rows[aarav.id].month_saved == 2
        assert earlier_rows[diya.id].month_present_total == 2
        assert earlier_rows[aarav.id].percent == 66.7, (
            "the year still ends on the cutoff"
        )

        # A month nobody took a register in: no registers, nothing present. The month has
        # open days, but this child's own record starts in November - their October is the
        # empty window before their first mark, so the row prints a dash.
        empty = register_service.section_summary(
            session, room.id, until=WED, month=date(2026, 10, 15), today=WED
        )
        assert {row.month_saved for row in empty.rows} == {0}
        assert {row.month_present_total for row in empty.rows} == {0}
        assert {row.month_open_days for row in empty.rows} == {0}, (
            "October 2026 has 27 open days, but none of them are in this child's record"
        )


# ---------------------------------------------------------------------------
# The school's two answers of 19 Nov 2026: a weekly off never takes back a day
# that already has a register, and one date can be reopened on purpose
# ---------------------------------------------------------------------------


def test_a_new_weekly_off_never_takes_back_a_saved_day() -> None:
    """The days already marked stay, and they stay inside the percentage.

    The school runs seven days a week and takes a Sunday register; only then does it
    declare Sunday off. That Sunday keeps its marks *and* stays a working day, so no
    percentage moves. The next Sunday is the first one the rule closes - which is exactly
    "the weekly off applies after that Sunday", the day type's own last recorded date.
    """
    with memory_session() as session:
        data = seed(session)
        room, office = data["room"], data["office"]

        # Seven days a week, so the Sunday register can be taken at all.
        assert holiday_service.set_weekly_off(session, []) == []
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=SUN,
                records=[
                    AttendanceRowWrite(student_id=data["aarav"].id, status="present"),
                    AttendanceRowWrite(student_id=data["diya"].id, status="present"),
                ],
            ),
            user=office,
        )

        # Sunday is declared off **after** that register was saved.
        assert holiday_service.set_weekly_off(session, [5, 6]) == [5, 6]

        # 1. nothing was deleted by the save
        assert len(list(session.exec(select(AttendanceRecord)).all())) == 2

        # 2. the taught Sunday is a working day; the next Sunday is the first one closed
        next_sunday = date(2026, 11, 29)
        assert school_calendar.is_open(session, SUN) is True
        assert school_calendar.closed_reason(session, SUN) is None
        assert school_calendar.closed_reason(session, next_sunday) == "Sunday"

        # 3. it still counts - Mon-Sat plus the taught Sunday is six open days
        assert len(school_calendar.open_days(session, MON, SUN)) == 6
        summary = register_service.section_summary(session, room.id, MON, SUN)
        assert summary.working_days == 6
        assert [row.marked for row in summary.rows] == [1, 1]

        # 4. the calendar paints it open, and still shades the Saturdays that are off
        calendar = holiday_service.list_calendar(session, MON, SUN)
        assert SUN not in calendar.weekly_off_dates
        assert SAT in calendar.weekly_off_dates


def test_one_date_can_be_reopened_on_purpose() -> None:
    """Just this Sunday: the rule stays, the one date opens, and the register is allowed."""
    with memory_session() as session:
        data = seed(session)
        room, office = data["room"], data["office"]
        next_sunday = date(2026, 11, 29)

        assert school_calendar.closed_reason(session, SUN) == "Sunday"

        opened = holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=SUN), user=office
        )
        assert opened.on_date == SUN
        assert opened.created_by == "the principal"

        # The one date is open; the Sunday after it is not, and the rule is unchanged.
        assert school_calendar.closed_reason(session, SUN) is None
        assert school_calendar.closed_reason(session, next_sunday) == "Sunday"
        assert holiday_service.weekly_off(session) == [6]

        # A register may be taken on the reopened date...
        register_service.save_register(
            session,
            AttendanceBulkCreate(
                section_id=room.id,
                date=SUN,
                records=[
                    AttendanceRowWrite(student_id=data["aarav"].id, status="present")
                ],
            ),
            user=office,
        )

        # ...and is still refused, by name, on the next Sunday.
        with pytest.raises(HTTPException) as refused:
            register_service.save_register(
                session,
                AttendanceBulkCreate(
                    section_id=room.id,
                    date=next_sunday,
                    records=[
                        AttendanceRowWrite(
                            student_id=data["aarav"].id, status="present"
                        )
                    ],
                ),
                user=office,
            )
        assert refused.value.status_code == 409
        assert "Sunday" in refused.value.detail

        # The calendar tells the screen which dates were opened.
        calendar = holiday_service.list_calendar(session, MON, SUN)
        assert [row.on_date for row in calendar.open_days] == [SUN]

        # Reopening the same date twice is a 409 - one date, one answer.
        with pytest.raises(HTTPException) as again:
            holiday_service.mark_open_day(
                session, OpenDayWrite(on_date=SUN), user=office
            )
        assert again.value.status_code == 409

        # An override removed from a date with no register hands it back to the rule.
        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=next_sunday), user=office
        )
        assert school_calendar.closed_reason(session, next_sunday) is None
        holiday_service.clear_open_day(session, next_sunday)
        assert school_calendar.closed_reason(session, next_sunday) == "Sunday"

        # The date that was taught stays open even after its override goes: the register
        # wins over the rule (the promise in `test_a_new_weekly_off_never_takes_back...`).
        holiday_service.clear_open_day(session, SUN)
        assert school_calendar.closed_reason(session, SUN) is None


def test_a_weekly_off_covers_the_whole_year_not_a_window() -> None:
    """Sunday off closes **every** Sunday of the year, and the register is refused on each.

    The rule is one setting read date by date - not rows, and not a date window. So a Sunday
    in January and a Sunday eleven months later stand under the same answer, and no register
    can be saved on either. A screen reads a window of its own to draw the grid; that window
    is a view, never the length of the rule.
    """
    with memory_session() as session:
        data = seed(session)
        room, office = data["room"], data["office"]

        assert holiday_service.weekly_off(session) == [6]
        closed = register_service.closed_days(
            session, date(2026, 1, 1), date(2026, 12, 31)
        )

        # 2026 holds 52 Sundays, and the whole year - not one month of it - is closed.
        assert len(closed) == 52
        assert {row.date.weekday() for row in closed} == {6}
        assert {row.reason for row in closed} == {"Sunday"}
        assert closed[0].date == date(2026, 1, 4)
        assert closed[-1].date == date(2026, 12, 27)

        # The register is refused in February, in July and in December alike: the day is
        # named, and nothing is written.
        for far in (date(2026, 2, 1), date(2026, 7, 5), date(2026, 12, 27)):
            with pytest.raises(HTTPException) as refused:
                register_service.save_register(
                    session,
                    AttendanceBulkCreate(
                        section_id=room.id,
                        date=far,
                        records=[
                            AttendanceRowWrite(
                                student_id=data["aarav"].id, status="present"
                            )
                        ],
                    ),
                    user=office,
                )
            assert refused.value.status_code == 409
            assert "Sunday" in refused.value.detail
        assert list(session.exec(select(AttendanceRecord)).all()) == []

        # The calendar page's own read is the same whole year: the grid shades all 52, not
        # the month it happens to be showing.
        page = holiday_service.list_calendar(
            session, date(2026, 1, 1), date(2026, 12, 31)
        )
        assert len(page.closed_days) == 52
        assert len(page.weekly_off_dates) == 52

        # One reopened date leaves the other fifty-one exactly as they were.
        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=date(2026, 12, 27)), user=office
        )
        remaining = register_service.closed_days(
            session, date(2026, 1, 1), date(2026, 12, 31)
        )
        assert len(remaining) == 51
        assert school_calendar.closed_reason(session, date(2026, 12, 27)) is None


def _holiday_windows(session):
    rows = holiday_service.list_calendar(session, MON, date(2026, 11, 30)).holidays
    return [(row.name, row.start_date, row.end_date) for row in rows]


def test_opening_a_one_day_holiday_removes_the_holiday() -> None:
    with memory_session() as session:
        data = seed(session)
        _add(session, "diwali", THU)

        opened = holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=THU), user=data["office"]
        )
        assert opened.on_date == THU
        assert school_calendar.is_open(session, THU) is True
        assert _holiday_windows(session) == []
        # No leftover "open on purpose" marker: nothing closes the day any more.
        assert holiday_service.list_calendar(session, MON, SUN).open_days == []


def test_opening_the_last_or_first_day_shortens_the_holiday() -> None:
    with memory_session() as session:
        data = seed(session)
        office = data["office"]
        _add(session, "diwali", MON, FRI)

        holiday_service.mark_open_day(session, OpenDayWrite(on_date=FRI), user=office)
        assert _holiday_windows(session) == [("diwali", MON, THU)]

        holiday_service.mark_open_day(session, OpenDayWrite(on_date=MON), user=office)
        assert _holiday_windows(session) == [("diwali", TUE, THU)]
        assert school_calendar.is_open(session, FRI) is True
        assert school_calendar.is_open(session, MON) is True
        assert school_calendar.closed_reason(session, WED) == "diwali"


def test_opening_a_day_in_the_middle_splits_the_holiday_in_two() -> None:
    with memory_session() as session:
        data = seed(session)
        _add(session, "diwali", MON, FRI)

        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=WED), user=data["office"]
        )
        assert _holiday_windows(session) == [
            ("diwali", MON, TUE),
            ("diwali", THU, FRI),
        ]
        assert school_calendar.is_open(session, WED) is True
        assert school_calendar.closed_reason(session, TUE) == "diwali"
        assert school_calendar.closed_reason(session, THU) == "diwali"


def test_a_two_day_leftover_becomes_a_single_day_holiday() -> None:
    with memory_session() as session:
        data = seed(session)
        _add(session, "diwali", MON, WED)
        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=MON), user=data["office"]
        )
        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=WED), user=data["office"]
        )
        assert _holiday_windows(session) == [("diwali", TUE, TUE)]


def test_a_sunday_inside_a_holiday_leaves_the_holiday_and_stays_a_weekly_off_override() -> (
    None
):
    with memory_session() as session:
        data = seed(session)
        _add(session, "break", SAT, date(2026, 11, 23))

        holiday_service.mark_open_day(
            session, OpenDayWrite(on_date=SUN), user=data["office"]
        )
        assert _holiday_windows(session) == [
            ("break", SAT, SAT),
            ("break", date(2026, 11, 23), date(2026, 11, 23)),
        ]
        # Sunday is still a weekly off, so the usual override row opens it.
        assert school_calendar.is_open(session, SUN) is True
        assert [
            row.on_date
            for row in holiday_service.list_calendar(
                session, MON, date(2026, 11, 30)
            ).open_days
        ] == [SUN]
