"""Workload, substitution, staff attendance, salary and leave follow the selected year.

People (teachers, staff) are never hidden; the work tied to a year - the timetable week,
the days they were marked, the months they were paid, the leave they asked for - shows
only for the selected session year. Switching back brings everything back.
"""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.settings import academic_years, year_scope
from app.domains.operations.salary import repository as salary_repo
from app.domains.operations.salary.models import SalaryPayment
from app.domains.people.teachers.staff_attendance import repository as staff_repo
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.substitution import repository as substitution_repo
from app.domains.people.teachers.workload import repository as workload_repo
from app.domains.services.leave import repository as leave_repo
from app.domains.services.leave.models import LeaveRequest
from tests.test_classroom_students import memory_session, seed
from tests.test_student_year_roster import _years


def _switch(session, year):
    academic_years.make_academic_year_current(
        year.id, session=session, current_user=None
    )


def test_the_month_labels_are_the_selected_years_twelve_months():
    with memory_session() as session:
        seed(session)
        a, b = _years(session)
        assert year_scope.month_labels(session)[0] == "Apr 2026"
        assert year_scope.month_labels(session)[-1] == "Mar 2027"
        assert len(year_scope.month_labels(session)) == 12
        _switch(session, b)
        assert year_scope.month_labels(session)[0] == "Apr 2027"


def test_workload_timetable_staff_attendance_salary_and_leave_follow_the_year():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        school = data["school"].id
        teacher = uuid4()
        monday = date(2026, 11, 16)

        session.add(
            TimetablePeriod(
                academic_year_id=a.id,
                classroom_id=data["first"].id,
                classroom_subject_id=uuid4(),
                teacher_id=teacher,
                day_of_week=DayOfWeek.monday,
                start_time=time(9, 0),
                end_time=time(9, 40),
                school_id=school,
            )
        )
        session.add(
            StaffAttendanceRecord(
                employee_id=teacher, date=monday, status="present", school_id=school
            )
        )
        session.add(
            SalaryPayment(
                employee_id=teacher,
                month="Nov 2026",
                net=Decimal("100"),
                school_id=school,
            )
        )
        session.add(
            LeaveRequest(
                requester_user_id=uuid4(),
                employee_id=teacher,
                leave_type="Casual",
                from_date=monday,
                to_date=monday,
                days=1,
                school_id=school,
            )
        )
        session.commit()

        # `week_periods` joins the subject, so only the plain timetable read is checked here.
        def periods():
            return substitution_repo.periods_on_weekday(session, DayOfWeek.monday)

        assert len(periods()) == 1
        assert (
            len(
                staff_repo.records_between(
                    session, employee_id=teacher, start=monday, end=monday
                )
            )
            == 1
        )
        assert (
            len(staff_repo.records_on(session, on_date=monday, employee_ids=[teacher]))
            == 1
        )
        assert len(salary_repo.get_register(session)) == 1
        assert len(leave_repo.staff_requests(session)) == 1

        _switch(session, b)

        assert periods() == []
        assert (
            staff_repo.records_between(
                session, employee_id=teacher, start=monday, end=monday
            )
            == []
        )
        assert (
            staff_repo.records_on(session, on_date=monday, employee_ids=[teacher]) == {}
        )
        assert salary_repo.get_register(session) == []
        assert leave_repo.staff_requests(session) == []
        assert workload_repo.completed_counts(session, [teacher], monday, monday) == {}
        assert workload_repo.substitute_counts(session, [teacher], monday, monday) == {}

        _switch(session, a)

        assert len(periods()) == 1
        assert len(salary_repo.get_register(session)) == 1
        assert len(leave_repo.staff_requests(session)) == 1
