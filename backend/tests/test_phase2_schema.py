"""Phase 2: the leave/attendance/school-master schema the phase was asked for.

Every test here fails for a rule the phase added:

* **one leave, one subject** - a request is either a staff leave (`employee_id`) or
  a student leave (`student_id`), never both and never neither (0.10's two tabs);
* **a leave type belongs to one school once** (`uq_leavetype_school_name`);
* **one holiday per day per school** (`uq_holiday_school_date`);
* **one department name per school**, and `employee.department_id` points at it;
* **one session name per school**, and `end_date >= start_date`;
* **enrollment is one placement per student per session**;
* **the register's status is the agreed vocabulary** - `on_leave` is derived from
  `leaverequest`, so the column refuses to store it;
* **`classlog.timetableperiod_id`** and the three `syllabusprogress` columns exist,
  because the workload tab reads them.

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import SyllabusProgress
from app.domains.academic.classroom.homework.models import ClassLog
from app.domains.academic.classroom.students.models import Enrollment
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear, Department, Holiday
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.services.leave.models import LeaveRequest, LeaveType


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


def _session(created, school_id=None) -> Session:
    session = Session(created, expire_on_commit=False)
    if school_id is not None:
        session.info["school_id"] = school_id
    return session


def _school(session: Session, code: str) -> School:
    school = School(
        name=f"School {code}",
        code=code,
        email=f"office@{code.lower()}.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


def _person(session: Session, school: School, code: str) -> tuple[User, Employee]:
    user = User(
        email=f"{uuid4().hex[:10]}@test",
        full_name=f"User {code}",
        hashed_password="x",
        school_id=school.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2023, 6, 1),
        school_id=school.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


def _leave(session: Session, school: School, user: User, **extra) -> LeaveRequest:
    payload = {
        "requester_user_id": user.id,
        "leave_type": "Casual",
        "from_date": date(2026, 11, 10),
        "to_date": date(2026, 11, 11),
        "days": 2,
        "school_id": school.id,
    }
    payload.update(extra)
    return LeaveRequest(**payload)


# --- the two tabs (0.10) -----------------------------------------------------


def test_a_staff_leave_names_the_employee():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS01")
        user, employee = _person(session, school, "EMP-0001")
        session.add(_leave(session, school, user, employee_id=employee.id))
        session.commit()
        row = session.exec(select(LeaveRequest)).one()
        assert row.employee_id == employee.id
        assert row.student_id is None
        assert row.half_day is False


def test_a_leave_that_names_nobody_is_refused():
    """Both NULL is the old staff shape - the check makes it impossible now."""
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS02")
        user, _ = _person(session, school, "EMP-0001")
        session.add(_leave(session, school, user))
        with pytest.raises(IntegrityError):
            session.commit()


def test_a_leave_that_names_two_people_is_refused():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS03")
        user, employee = _person(session, school, "EMP-0001")
        session.add(
            _leave(
                session,
                school,
                user,
                employee_id=employee.id,
                student_id=uuid4(),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


# --- masters -----------------------------------------------------------------


def test_a_leave_type_is_unique_inside_a_school_only():
    created = engine()
    with _session(created) as session:
        first = _school(session, "PS04")
        second = _school(session, "PS05")
        session.add(LeaveType(name="Casual", applies_to="staff", school_id=first.id))
        session.commit()
        session.add(LeaveType(name="Casual", applies_to="staff", school_id=second.id))
        session.commit()  # another school may have its own "Casual"
        session.add(LeaveType(name="Casual", applies_to="staff", school_id=first.id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_one_holiday_per_day_per_school():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS06")
        session.add(
            Holiday(on_date=date(2026, 11, 14), name="Diwali", school_id=school.id)
        )
        session.commit()
        session.add(
            Holiday(
                on_date=date(2026, 11, 14), name="Diwali again", school_id=school.id
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_a_session_cannot_end_before_it_starts():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS07")
        session.add(
            AcademicYear(
                name="2026-27",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 4, 30),
                school_id=school.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_a_department_name_is_unique_inside_a_school():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS08")
        session.add(Department(name="Science", school_id=school.id))
        session.commit()
        session.add(Department(name="Science", school_id=school.id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_the_employee_points_at_its_department_row():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS09")
        _, employee = _person(session, school, "EMP-0001")
        department = Department(name="Science", school_id=school.id)
        session.add(department)
        session.commit()
        session.refresh(department)
        employee.department_id = department.id
        session.add(employee)
        session.commit()
        session.refresh(employee)
        assert employee.department_id == department.id
        # The text column is untouched - it is what the profile prints.
        assert employee.department == "Science"


# --- the classroom links -----------------------------------------------------


def test_classlog_can_name_the_period_it_was_written_against():
    assert "timetableperiod_id" in ClassLog.__table__.columns


def test_syllabus_progress_has_an_owner_a_session_and_a_plan():
    columns = SyllabusProgress.__table__.columns
    names = set(columns.keys())
    assert {"teacher_id", "academic_year_id", "planned_completion"} <= names
    # All three are optional: a row written before this phase stays valid.
    assert columns["teacher_id"].nullable
    assert columns["planned_completion"].nullable


def test_enrollment_is_one_placement_per_student_per_session():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS10")
        year = AcademicYear(
            name="2026-27",
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            school_id=school.id,
        )
        session.add(year)
        session.commit()
        session.refresh(year)
        payload = {
            "student_id": uuid4(),
            "classroom_id": uuid4(),
            "academic_year_id": year.id,
            "school_id": school.id,
        }
        session.add(Enrollment(**payload))
        session.commit()
        session.add(Enrollment(**payload))
        with pytest.raises(IntegrityError):
            session.commit()


# --- the register ------------------------------------------------------------


def test_the_register_records_times_and_refuses_on_leave():
    created = engine()
    with _session(created) as session:
        school = _school(session, "PS11")
        _, employee = _person(session, school, "EMP-0001")
        row = StaffAttendanceRecord(
            employee_id=employee.id,
            date=date(2026, 11, 10),
            status="present",
            check_in_time=time(9, 5),
            check_out_time=time(16, 40),
            school_id=school.id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.check_in_time == time(9, 5)

    # `on_leave` is derived, so the column itself refuses it.
    with _session(created) as session:
        school = session.exec(select(School)).first()
        employee = session.exec(select(Employee)).first()
        session.add(
            StaffAttendanceRecord(
                employee_id=employee.id,
                date=date(2026, 11, 11),
                status="on_leave",
                school_id=school.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
