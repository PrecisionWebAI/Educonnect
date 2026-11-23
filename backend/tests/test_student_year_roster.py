"""Switching the academic year changes who is on the roll.

The old year's class must not leak into a year where nobody is enrolled yet: a student
with no enrollment in the new year is "not placed", a promoted child sits in the new
class, a retained one in the same class, and switching back restores the earlier roll.
"""

from datetime import date

from sqlmodel import select

from app.domains.academic.classroom.students import service
from app.domains.academic.classroom.students.models import Enrollment, Student
from app.domains.academic.classroom.students.placement import (
    place_student,
)
from app.domains.admin.settings import academic_years
from app.domains.admin.settings.academic_year_context import (
    ensure_current_academic_year,
)
from app.domains.admin.settings.models import AcademicYear
from tests.test_classroom_students import _student, memory_session, seed


def _years(session):
    """The running year (a) and the next one (b), both with real windows."""
    a = ensure_current_academic_year(session)
    b = AcademicYear(
        name="2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
        school_id=a.school_id,
    )
    session.add(b)
    session.commit()
    session.refresh(b)
    return a, b


def _switch(session, year):
    """The real switch the principal's dropdown calls (clear old flag, set new, sync)."""
    academic_years.make_academic_year_current(
        year.id, session=session, current_user=None
    )


def _roster(session, room=None):
    rows = service.get_students(
        session, classroom_id=room.id if room is not None else None
    )
    return {row.name for row in rows}


def test_a_year_with_nobody_enrolled_shows_an_empty_class_not_last_years():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}

        _switch(session, b)

        assert _roster(session, data["first"]) == set()
        assert _roster(session, data["second"]) == set()
        # Children enrolled only in the old year are not on the new year's roll.
        assert _roster(session) == set()
        assert service.count_students(session) == 0

        # Nothing was deleted: the old year still has its enrollments.
        assert (
            len(
                session.exec(
                    select(Enrollment).where(Enrollment.academic_year_id == a.id)
                ).all()
            )
            == 3
        )

        _switch(session, a)
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}
        assert _roster(session, data["second"]) == {"kabir singh"}


def test_promoted_and_retained_children_sit_where_the_new_year_puts_them():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)

        aarav = session.get(Student, data["aarav"].id)
        diya = session.get(Student, data["diya"].id)
        # aarav is promoted to 6-B, diya is retained in 6-A - in the new year only.
        place_student(session, aarav, data["second"].id, year=b, update_current=False)
        place_student(session, diya, data["first"].id, year=b, update_current=False)

        # Still the old year: nothing moves until the year is switched.
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}

        _switch(session, b)

        assert _roster(session, data["first"]) == {"diya patel"}
        assert _roster(session, data["second"]) == {"aarav sharma"}
        assert _roster(session) == {"aarav sharma", "diya patel"}
        assert service.count_students(session) == 2

        _switch(session, a)
        assert _roster(session, data["second"]) == {"kabir singh"}
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}


def test_a_new_admission_with_no_class_stays_visible_in_every_year():
    with memory_session() as session:
        seed(session)
        a, b = _years(session)
        waiting = _student(session, "new child", "P1-9")  # never placed anywhere

        assert "new child" in _roster(session)
        _switch(session, b)
        assert "new child" in _roster(session)
        assert session.get(Student, waiting.id).classroom_id is None


def test_the_list_is_a_to_z_and_carries_the_tab_columns():
    from datetime import date as _date

    from app.domains.academic.classroom.attendance.models import AttendanceRecord

    with memory_session() as session:
        data = seed(session)
        a, _b = _years(session)
        names = [row.name for row in service.get_students(session)]
        assert names == sorted(names)

        kabir = service.get_students(session, classroom_id=data["second"].id)[0]
        assert kabir.admissionYear == a.name
        assert kabir.admissionClass == "Class 6"
        assert kabir.promotionStatus == "NEW_ADMISSION"
        assert kabir.nextYearOutcome is None
        assert kabir.guardian == "meera singh"
        assert kabir.phone == "9000000111"
        assert kabir.attendancePercent is None  # nothing marked: no data, not 0%

        # Two school days in the year: present, then absent -> 50%.
        for day, status in (
            (_date(2026, 11, 16), "present"),
            (_date(2026, 11, 17), "absent"),
        ):
            session.add(
                AttendanceRecord(
                    student_id=kabir.id,
                    classroom_id=data["second"].id,
                    date=day,
                    status=status,
                    school_id=data["school"].id,
                )
            )
        session.commit()
        kabir = service.get_students(session, classroom_id=data["second"].id)[0]
        assert kabir.attendancePercent == 50.0


def test_looking_at_the_next_year_never_enrols_anybody_in_it():
    from app.domains.academic.classroom.students.placement import (
        backfill_current_enrollments,
    )

    with memory_session() as session:
        seed(session)
        a, b = _years(session)
        _switch(session, b)
        # What `GET /academic-years/current` does on every read.
        assert backfill_current_enrollments(session, b) == 0
        assert (
            session.exec(
                select(Enrollment).where(Enrollment.academic_year_id == b.id)
            ).all()
            == []
        )
        assert _roster(session) == set()

        # Today's own year is still repaired when a placed student has no row in it.
        _switch(session, a)
        assert backfill_current_enrollments(session, a) == 0  # already complete


def test_signing_in_puts_the_school_back_on_the_year_that_is_running():
    from app.domains.admin.settings.academic_years import reset_to_todays_year

    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)  # a = 2026-27 (today's year), b = 2027-28
        _switch(session, b)
        assert _roster(session, data["first"]) == set()  # looking at next year

        assert reset_to_todays_year(session).id == a.id

        assert session.get(AcademicYear, a.id).is_current is True
        assert session.get(AcademicYear, b.id).is_current is False
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}
        # Already running: nothing to do.
        assert reset_to_todays_year(session).id == a.id


def test_looking_at_another_year_reads_that_years_enrollments_without_moving_anyone():
    from app.domains.academic.classroom.students.placement import place_student

    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)  # a runs today; b is next year
        aarav = session.get(Student, data["aarav"].id)
        # aarav is promoted to 6-B in the next year only.
        place_student(session, aarav, data["second"].id, year=b, update_current=False)

        # Today's view: nothing changed.
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}

        # This request looks at the next year (what the X-Academic-Year header does).
        session.info["academic_year_id"] = b.id
        assert _roster(session, data["first"]) == set()
        assert _roster(session, data["second"]) == {"aarav sharma"}
        assert service.count_students(session, classroom_id=data["second"].id) == 1
        only = service.get_students(session, classroom_id=data["second"].id)
        assert only[0].section == "B"

        # Nobody was moved: the pointer still says today's class.
        session.info.pop("academic_year_id")
        assert session.get(Student, aarav.id).classroom_id == data["first"].id
        assert _roster(session, data["first"]) == {"aarav sharma", "diya patel"}


def test_class_counts_and_rolls_follow_the_year_on_screen():
    from app.domains.academic.classroom import repository as classroom_repo
    from app.domains.academic.classroom import service as classroom_service
    from app.domains.academic.classroom.homework import repository as homework_repo
    from app.domains.academic.classroom.students.placement import place_student

    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        aarav = session.get(Student, data["aarav"].id)
        place_student(session, aarav, data["second"].id, year=b, update_current=False)
        first, second = data["first"].id, data["second"].id

        # The running year: 2 in 6-A, 1 in 6-B.
        strength = classroom_service._strength_by_section(session)
        assert (strength[first], strength[second]) == (2, 1)
        per_room = classroom_repo.get_students_per_section(session)
        assert per_room[first][0] == 2 and per_room[second][0] == 1
        assert homework_repo.roll_counts(session, [first, second]) == {
            first: 2,
            second: 1,
        }

        # The same request looking at next year: only the one enrolled there, in 6-B.
        session.info["academic_year_id"] = b.id
        strength = classroom_service._strength_by_section(session)
        assert strength.get(first, 0) == 0 and strength[second] == 1
        per_room = classroom_repo.get_students_per_section(session)
        assert first not in per_room and per_room[second][0] == 1
        assert homework_repo.roll_counts(session, [first, second]) == {second: 1}
        assert [
            s.full_name
            for s, _ in classroom_repo.get_students_in_section(session, second)
        ] == ["aarav sharma"]
