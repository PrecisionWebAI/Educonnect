"""Attendance may only be written in the session year today falls in.

The five rules: the date is inside today's year; a past day is fine but only when the
school is open; a day after today is refused; the row is tied to the student's
enrollment of that year; and a previous or next year that is selected on screen is
read-only. Every rule is enforced here in the backend, not only in the screen.
"""

from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.attendance import register
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.attendance.schemas import (
    AttendanceBulkCreate,
    AttendanceRowWrite,
)
from app.domains.academic.classroom.students.models import Enrollment
from app.domains.admin.settings import academic_years
from tests.test_classroom_students import memory_session, seed
from tests.test_student_year_roster import _years


def _weekday(back: int = 1) -> date:
    """A recent weekday that is not today (the school is open Monday to Saturday)."""
    day = date.today() - timedelta(days=back)
    while day.weekday() == 6:  # Sunday is the default weekly off
        day -= timedelta(days=1)
    return day


def _save(session, data, day, students=("aarav", "diya")):
    return register.save_register(
        session,
        AttendanceBulkCreate(
            section_id=data["first"].id,
            date=day,
            records=[
                AttendanceRowWrite(student_id=data[name].id, status="present")
                for name in students
            ],
        ),
        user=None,
    )


def _refused(session, data, day) -> str:
    with pytest.raises(HTTPException) as refused:
        _save(session, data, day)
    assert refused.value.status_code == 409
    return refused.value.detail


def test_a_past_open_day_in_the_current_year_saves_and_links_the_enrollment():
    with memory_session() as session:
        data = seed(session)
        a, _b = _years(session)
        day = _weekday()
        rows = _save(session, data, day)
        assert len(rows) == 2
        stored = session.exec(select(AttendanceRecord)).all()
        enrollment_ids = {
            row.id
            for row in session.exec(
                select(Enrollment).where(Enrollment.academic_year_id == a.id)
            ).all()
        }
        assert all(record.enrollment_id in enrollment_ids for record in stored)
        # Saving the same day again updates, it never doubles or unlinks.
        _save(session, data, day)
        assert len(session.exec(select(AttendanceRecord)).all()) == 2


def test_a_date_after_today_is_refused():
    with memory_session() as session:
        data = seed(session)
        _years(session)
        tomorrow = date.today() + timedelta(days=1)
        while tomorrow.weekday() == 6:
            tomorrow += timedelta(days=1)
        assert "has not arrived" in _refused(session, data, tomorrow)
        assert session.exec(select(AttendanceRecord)).all() == []


def test_a_date_in_another_session_year_is_refused():
    with memory_session() as session:
        data = seed(session)
        a, _b = _years(session)
        before = a.start_date - timedelta(days=10)
        while before.weekday() == 6:
            before -= timedelta(days=1)
        assert "outside 2026-27" in _refused(session, data, before)


def test_a_previous_or_next_year_on_screen_is_read_only():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        academic_years.make_academic_year_current(
            b.id, session=session, current_user=None
        )
        message = _refused(session, data, _weekday())
        assert "2027-28 is on screen" in message and "read-only" in message
        academic_years.make_academic_year_current(
            a.id, session=session, current_user=None
        )
        assert len(_save(session, data, _weekday())) == 2


def test_a_student_with_no_enrollment_this_year_blocks_the_save_with_their_name():
    with memory_session() as session:
        data = seed(session)
        a, _b = _years(session)
        gone = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == data["diya"].id,
                Enrollment.academic_year_id == a.id,
            )
        ).one()
        session.delete(gone)
        session.commit()
        message = _refused(session, data, _weekday())
        assert "diya patel" in message and "no enrollment in 2026-27" in message
        assert session.exec(select(AttendanceRecord)).all() == []


def test_a_closed_day_still_answers_with_the_school_calendar():
    with memory_session() as session:
        data = seed(session)
        _years(session)
        sunday = date.today()
        while sunday.weekday() != 6:
            sunday -= timedelta(days=1)
        assert "Sunday" in _refused(session, data, sunday)
