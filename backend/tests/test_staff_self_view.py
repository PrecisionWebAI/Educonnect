"""Phase 9: the caller's own view, and the three staff aggregates.

Two claims are tested here, both of which a screen could otherwise make without
evidence:

* **"my" reads are mine.** `/teachers/me*` takes the employee id from the token, so a
  teacher reading their own week or month needs no office permission - and still
  cannot read a colleague's (`404`, the rule the whole domain follows);
* **the report says what it counted.** The attendance share is of the days somebody
  marked, the workload buckets name their denominator (`rule` or `timetable`), and the
  payload carries the window and the scope, so a number is never quietly about fewer
  people or a different month than the reader assumes.

Runs on in-memory SQLite, like the rest of this module's suite.
"""

import importlib
from datetime import date, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import Subject
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.insights.reports import staff_service
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import service as teachers_service
from app.domains.people.teachers.appraisal.models import Appraisal, AppraisalCycle
from app.domains.people.teachers.staff_attendance import service as attendance_service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.workload import service as workload_service
from app.domains.people.teachers.workload.models import StaffWorkloadRule

TODAY = date.today()
MONTH = TODAY.strftime("%Y-%m")


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


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("teacher", "Teacher"),
        ("school_admin", "School Administrator"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _user(session: Session, name: str, school_id, roles) -> User:
    user = User(
        email=f"{name.lower().replace(' ', '.')}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for codename in roles:
        grant_role(session, user, codename)
    return user


def _employee(session: Session, user: User, code: str, department: str) -> Employee:
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=department,
        joining_date=date(2023, 6, 1),
        email=f"{code.lower()}@test",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@pytest.fixture()
def seeded():
    """One school: a principal, two teachers, and an office account with no record."""
    session = session_for(engine())
    _roles(session)
    school = School(
        name="Test School",
        code="SELF-0001",
        email="office@self-0001.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    principal = _user(session, "Principal One", school.id, ("principal",))
    teacher_user = _user(session, "Teacher One", school.id, ("teacher",))
    teacher = _employee(session, teacher_user, "EMP-0001", "Science")
    two_user = _user(session, "Teacher Two", school.id, ("teacher",))
    two = _employee(session, two_user, "EMP-0002", "Maths")
    office = _user(session, "Office One", school.id, ("school_admin",))

    return SimpleNamespace(
        session=session,
        school=school,
        principal=principal,
        teacher_user=teacher_user,
        teacher=teacher,
        two_user=two_user,
        two=two,
        office=office,
    )


def _subject(session: Session):
    """One real subject, so a period survives the week's join (it drops orphans)."""
    found = session.exec(select(Subject).where(Subject.name == "Physics")).first()
    if found is not None:
        return found
    found = Subject(name="Physics", code="PHY")
    session.add(found)
    session.commit()
    session.refresh(found)
    return found


def _periods(session: Session, employee: Employee, count: int) -> None:
    """`count` periods a week for this teacher - only the count is read here."""
    subject = _subject(session)
    for index in range(count):
        session.add(
            TimetablePeriod(
                classroom_id=uuid4(),
                subject_id=subject.id,
                teacher_id=employee.id,
                day_of_week=DayOfWeek.monday,
                start_time=time(9 + index % 6, 0),
                end_time=time(9 + index % 6, 45),
            )
        )
    session.commit()


# --- my own view ------------------------------------------------------------


def test_a_teacher_reads_their_own_row(seeded):
    """`/teachers/me` answers with the caller, whatever their scope is."""
    row = teachers_service.get_own(seeded.session, seeded.teacher_user)
    assert row.staffCode == "EMP-0001"
    assert row.name == "Teacher One"
    assert row.department == "Science"


def test_an_account_with_no_staff_record_is_told_so(seeded):
    """An office login that is not on the roll has no profile - `404`, with a reason."""
    with pytest.raises(HTTPException) as problem:
        teachers_service.get_own(seeded.session, seeded.office)
    assert problem.value.status_code == 404
    assert "no staff record" in problem.value.detail


def test_a_teacher_reads_their_own_week(seeded):
    """The self route calls the same service; the id comes from the token."""
    _periods(seeded.session, seeded.teacher, 4)
    week = workload_service.staff_week(
        seeded.session, seeded.teacher.id, seeded.teacher_user
    )
    assert week.name == "Teacher One"
    assert week.periods == 4


def test_a_teacher_cannot_read_a_colleagues_week(seeded):
    """The office route keeps its own scope: a colleague is `404`, never `403`."""
    with pytest.raises(HTTPException) as problem:
        workload_service.staff_week(seeded.session, seeded.two.id, seeded.teacher_user)
    assert problem.value.status_code == 404


def test_a_teacher_reads_their_own_month_without_the_office_right(seeded):
    """`staff_attendance.read` is the office's because it reads everybody's register."""
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.teacher.id, date=TODAY, status=labels.PRESENT
        )
    )
    seeded.session.commit()

    month = attendance_service.month(
        seeded.session, seeded.teacher.id, MONTH, seeded.teacher_user
    )
    assert month.employee_id == seeded.teacher.id
    assert month.present == 1


def test_a_teacher_cannot_read_a_colleagues_month(seeded):
    with pytest.raises(HTTPException) as problem:
        attendance_service.month(
            seeded.session, seeded.two.id, MONTH, seeded.teacher_user
        )
    assert problem.value.status_code == 404


# --- the three aggregates ---------------------------------------------------


def test_the_attendance_share_is_of_the_days_somebody_marked(seeded):
    """One present, one absent: 50%. A day nobody marked is not in the fraction."""
    seeded.session.add_all(
        [
            StaffAttendanceRecord(
                employee_id=seeded.teacher.id, date=TODAY, status=labels.PRESENT
            ),
            StaffAttendanceRecord(
                employee_id=seeded.teacher.id,
                date=TODAY - timedelta(days=1),
                status=labels.ABSENT,
            ),
        ]
    )
    seeded.session.commit()

    report = staff_service.staff_summary(seeded.session, seeded.principal)
    assert report.attendance.marked == 2
    assert report.attendance.present == 1
    assert report.attendance.percent == 50
    assert report.attendance.window_end == TODAY
    assert report.attendance.days == 30


def test_the_workload_buckets_name_their_denominator(seeded):
    """With a school rule the buckets are shares of it - and the payload says `rule`."""
    seeded.session.add(
        StaffWorkloadRule(weekly_periods=10, overload_percent=100, underload_percent=60)
    )
    seeded.session.commit()
    _periods(seeded.session, seeded.teacher, 4)
    _periods(seeded.session, seeded.two, 8)

    report = staff_service.staff_summary(seeded.session, seeded.principal)
    assert report.workload.capacity_source == "rule"
    assert report.workload.capacity == 10
    assert report.workload.teachers == 2
    assert report.workload.periods == 12
    assert report.workload.under == 1
    assert report.workload.normal == 1
    assert report.workload.over == 0


def test_without_a_rule_the_heaviest_load_is_the_denominator(seeded):
    """A percentage needs a denominator; when the school wrote none, it says which."""
    _periods(seeded.session, seeded.teacher, 2)
    _periods(seeded.session, seeded.two, 6)

    report = staff_service.staff_summary(seeded.session, seeded.principal)
    assert report.workload.capacity_source == "timetable"
    assert report.workload.capacity == 6


def test_the_appraisal_summary_counts_the_open_season(seeded):
    """`submitted` counts everybody past draft; the average covers rated rows only."""
    cycle = AppraisalCycle(
        name="2026-27 Annual",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        status=labels.CYCLE_OPEN,
    )
    seeded.session.add(cycle)
    seeded.session.commit()
    seeded.session.refresh(cycle)
    seeded.session.add_all(
        [
            Appraisal(
                cycle_id=cycle.id,
                employee_id=seeded.teacher.id,
                status=labels.APPRAISAL_FINALIZED,
                self_rating=4,
                reviewer_rating=4,
            ),
            Appraisal(
                cycle_id=cycle.id,
                employee_id=seeded.two.id,
                status=labels.APPRAISAL_SUBMITTED,
                self_rating=5,
            ),
        ]
    )
    seeded.session.commit()

    report = staff_service.staff_summary(seeded.session, seeded.principal)
    assert report.appraisals.cycle == "2026-27 Annual"
    assert report.appraisals.total == 2
    assert report.appraisals.submitted == 2
    assert report.appraisals.reviewed == 1
    assert report.appraisals.finalized == 1
    assert report.appraisals.average_reviewer_rating == 4.0


def test_the_report_is_scoped_and_says_so(seeded):
    """A teacher's copy counts one person - and the payload admits it."""
    school_view = staff_service.staff_summary(seeded.session, seeded.principal)
    own_view = staff_service.staff_summary(seeded.session, seeded.teacher_user)

    assert school_view.scope == "school"
    assert school_view.people == 2
    assert own_view.scope == "scoped"
    assert own_view.people == 1
    assert own_view.workload.teachers == 1
