"""`GET /teachers/performance` - the score from attendance, workload and course.

Three rules the tests here pin down, because each of them was a choice:

* **the window is the session** (1 April -> 31 March), read from the school's
  `academic_year` row when one is current - not a rolling 90 days;
* **a component with nothing behind it is `None`, not 0%** - an unmarked register,
  no timetable period, no chapter plan;
* **the course component is coverage and timeliness**, and falls back to coverage
  alone when no chapter was ever given a planned date.

The URL is asserted too: the screen has called `/teachers/performance` since Phase 1.
"""

import importlib
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as people_labels
from app.domains.people.teachers.performance import router as router_module
from app.domains.people.teachers.performance import service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord


def engine():
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


def session_for(created, school_id=None):
    session = Session(created, expire_on_commit=False)
    if school_id is not None:
        session.info["school_id"] = school_id
    return session


def _teacher(session: Session, school_id, code: str, name: str):
    role = session.exec(select(Role).where(Role.codename == "teacher")).first()
    user = User(
        email=f"{code.lower()}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    if role is not None:
        grant_role(session, user, "teacher")
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2023, 6, 1),
        email=f"{code.lower()}@test",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


@pytest.fixture()
def seeded():
    session = session_for(engine())
    session.add(Role(codename="teacher", label="Teacher"))
    session.commit()
    school = School(
        name="Test School",
        code="PERF-0001",
        email="office@perf-0001.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    _, one = _teacher(session, school.id, "EMP-0001", "Teacher One")
    _, two = _teacher(session, school.id, "EMP-0002", "Teacher Two")
    return SimpleNamespace(session=session, school=school, one=one, two=two)


def test_the_url_did_not_move():
    """The screen has called `/teachers/performance` since Phase 1."""
    paths = [route.path for route in router_module.router.routes]
    assert "/teachers/performance" in paths


def test_the_window_is_the_school_year_not_ninety_days(seeded):
    """No `academic_year` row: the calendar's April -> March, not a rolling quarter."""
    window = service.session_window(seeded.session)

    assert window.start.month == 4 and window.start.day == 1
    assert window.end.month == 3 and window.end.day == 31
    assert window.start.year + 1 == window.end.year
    assert window.name == f"{window.start.year}-{str(window.start.year + 1)[-2:]}"


def test_the_schools_own_session_wins_over_the_calendar(seeded):
    """A school that shifted its year is not overruled by the calendar."""
    seeded.session.add(
        AcademicYear(
            name="2024-25",
            start_date=date(2024, 5, 1),
            end_date=date(2025, 4, 30),
            is_current=True,
            school_id=seeded.school.id,
        )
    )
    seeded.session.commit()

    window = service.session_window(seeded.session)
    assert window.name == "2024-25"
    assert window.start == date(2024, 5, 1)
    assert window.end == date(2025, 4, 30)


def test_attendance_counts_half_days_as_half(seeded):
    """Present 2 + one half day out of 4 marked = 62% (5 earned half-days of 8)."""
    today = date.today()
    statuses = [
        people_labels.PRESENT,
        people_labels.PRESENT,
        people_labels.HALF_DAY,
        people_labels.ABSENT,
    ]
    for offset, status in enumerate(statuses):
        seeded.session.add(
            StaffAttendanceRecord(
                employee_id=seeded.one.id,
                date=today - timedelta(days=offset),
                status=status,
                school_id=seeded.school.id,
            )
        )
    seeded.session.commit()

    window = service.session_window(seeded.session)
    register = service._attendance(
        seeded.session, [seeded.one.id], window.start, window.end
    )[seeded.one.id]

    assert (register.present, register.half_day, register.marked) == (2, 1, 4)
    assert register.percent == 62


def test_a_day_outside_the_session_is_not_counted(seeded):
    """A register row from last year must not leak into this year's percentage."""
    window = service.session_window(seeded.session)
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.one.id,
            date=window.start - timedelta(days=1),
            status=people_labels.ABSENT,
            school_id=seeded.school.id,
        )
    )
    seeded.session.commit()

    register = service._attendance(
        seeded.session, [seeded.one.id], window.start, window.end
    )
    assert seeded.one.id not in register


def test_course_is_coverage_and_timeliness():
    """6 of 10 chapters, 3 of the 6 planned ones on time, 12 days late overall."""
    course = service._Course(done=6, total=10, on_time=3, planned=6, slippage=12)

    assert course.coverage == 60
    assert course.timeliness == 50
    assert course.average_days == 2
    assert course.value == round(60 * 0.6 + 50 * 0.4)
    assert "6 of 10 chapter(s) (60%)" in course.display
    assert "2 day(s) late on average" in course.display


def test_a_plan_with_no_planned_dates_is_coverage_only():
    """Timeliness needs a date to be late for - without one it is not 0%."""
    course = service._Course(done=4, total=8, on_time=0, planned=0, slippage=0)

    assert course.timeliness is None
    assert course.average_days is None
    assert course.value == course.coverage == 50
    assert "on time" not in course.display


def test_finishing_early_reads_early():
    course = service._Course(done=6, total=6, on_time=6, planned=6, slippage=-12)

    assert course.value == 100
    assert course.average_days == -2
    assert "2 day(s) early on average" in course.display


def test_the_score_renormalises_over_what_is_known():
    """Two of three components: the weights are renormalised, not the missing one."""
    components = service._components(
        attendance=service._Register(present=9, half_day=0, marked=10),
        workload=(9, 12, "rule"),
        course=None,
    )
    by_key = {item.key: item for item in components}

    assert by_key["attendance"].value == 90
    assert by_key["workload"].value == 75  # 9 of 12 periods
    assert by_key["workload"].display.endswith("(the school's rule)")
    # No plan -> "no data", and the score is the two that exist.
    assert by_key["course"].value is None
    assert service._score(components) == round((90 * 0.4 + 75 * 0.3) / 0.7)


def test_nothing_recorded_is_none_not_zero():
    components = service._components(attendance=None, workload=(0, 0, "timetable"), course=None)

    assert all(item.value is None for item in components)
    assert service._score(components) is None


def test_a_staff_row_has_no_timetable_or_plan_components():
    """A staff member's job has neither, so the components are absent, not 0%."""
    components = service._components(attendance=None, workload=None, course=None)

    assert [item.key for item in components] == ["attendance"]
    assert service._score(components) is None

