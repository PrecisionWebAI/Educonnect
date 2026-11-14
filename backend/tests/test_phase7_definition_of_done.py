"""Phase 7: the definition of done - the facts the eight phases promised.

Every test here is a promise from the plan, not a new feature:

* **one leave, one subject** and the two tabs' scope (0.10) - `kind` never widens
  what a caller may read;
* **the register covers staff** (0.9 bug) and a second mark is `409`;
* **a teacher cannot read a colleague's month or leave** - `404`, not `403`;
* **another school's rows are invisible** (`404` by construction);
* **approval puts somebody `On Leave Today`** and cancelling takes them off;
* **the workload numbers are the timetable's** - periods, capacity and the band;
* **money columns are decimal, not float** (`numeric(12,2)` from Phase 1).

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import Numeric
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers import service as teachers_service
from app.domains.people.teachers.staff_attendance import service as attendance_service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.services.leave import service as leave_service
from app.domains.services.leave import workflow as leave_workflow
from app.domains.services.leave.models import LeaveRequest


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


def _session(created) -> Session:
    return Session(created, expire_on_commit=False)


def _school(session: Session, code: str = "P7") -> School:
    for name in ("teacher", "hod", "school_admin", "accountant", "principal"):
        if not session.exec(select(Role).where(Role.codename == name)).first():
            session.add(Role(codename=name, label=name.title()))
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


def _employee(session: Session, school: School, code: str, role: str = "teacher"):
    user = User(
        email=f"{code.lower()}@{school.code.lower()}.test",
        full_name=f"Person {code}",
        hashed_password="x",
        school_id=school.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    grant_role(session, user, role)
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


# --- the split and the register (0.9) ---------------------------------------


def test_one_employee_never_appears_in_both_lists():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, teacher = _employee(session, school, "EMP-0001", "teacher")
        _, accountant = _employee(session, school, "EMP-0002", "accountant")

        teaching = {
            row.id for row in teachers_repository.roll_employees(session, "teacher")
        }
        staff = {row.id for row in teachers_repository.roll_employees(session, "staff")}

        assert teaching & staff == set()
        assert teacher.id in teaching and accountant.id in staff


def test_the_register_covers_staff_not_only_teachers():
    """The 0.9 bug: `staffattendancerecord` used to be built from the teaching roll."""
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, accountant = _employee(session, school, "EMP-0002", "accountant")

        attendance_service.mark_self(
            session,
            attendance_service.AttendanceSelfIn(
                date=date(2026, 11, 10), status="present"
            ),
            session.get(User, accountant.user_id),
        )
        row = session.exec(select(StaffAttendanceRecord)).one()
        assert row.employee_id == accountant.id


def test_a_second_mark_on_the_same_day_is_a_409():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        user, _ = _employee(session, school, "EMP-0001", "teacher")
        payload = attendance_service.AttendanceSelfIn(
            date=date(2026, 11, 10), status="present"
        )
        attendance_service.mark_self(session, payload, user)
        with pytest.raises(Exception) as problem:
            attendance_service.mark_self(session, payload, user)
        assert getattr(problem.value, "status_code", None) == 409


# --- privacy: a teacher reads themselves, nobody else -----------------------


def test_a_teacher_cannot_read_a_colleagues_month():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        me, _ = _employee(session, school, "EMP-0001", "teacher")
        _, other = _employee(session, school, "EMP-0002", "teacher")

        with pytest.raises(Exception) as problem:
            attendance_service.month(session, other.id, "2026-11", me)
        assert getattr(problem.value, "status_code", None) == 404


def test_another_schools_leave_is_a_404():
    created = engine()
    with _session(created) as session:
        mine = _school(session, "P7A")
        theirs = _school(session, "P7B")
        user, _ = _employee(session, mine, "EMP-0001")
        outsider_user, outsider = _employee(session, theirs, "EMP-9001")

        row = LeaveRequest(
            employee_id=outsider.id,
            requester_user_id=outsider_user.id,
            leave_type="Casual",
            from_date=date(2026, 11, 10),
            to_date=date(2026, 11, 10),
            days=1,
            status="Pending",
            school_id=theirs.id,
        )
        session.add(row)
        session.commit()

        session.info["school_id"] = mine.id
        with pytest.raises(Exception) as problem:
            leave_workflow.read_request(session, row.id, user)
        assert getattr(problem.value, "status_code", None) == 404


# --- leave: tabs, approval, reversal ----------------------------------------


def test_approval_puts_somebody_on_leave_today_and_cancelling_takes_them_off():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        owner, employee = _employee(session, school, "EMP-0001", "teacher")
        office, _ = _employee(session, school, "EMP-0002", "school_admin")

        today = date.today()
        request = LeaveRequest(
            employee_id=employee.id,
            requester_user_id=owner.id,
            leave_type="Casual",
            from_date=today,
            to_date=today,
            days=1,
            status="Pending",
            school_id=school.id,
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        assert teachers_service.staff_summary(session, "teacher").on_leave_today == 0
        leave_workflow.decide(
            session, request.id, action="approve", note="ok", user=office
        )
        assert teachers_service.staff_summary(session, "teacher").on_leave_today == 1

        leave_workflow.decide(
            session, request.id, action="cancel", note=None, user=owner
        )
        assert teachers_service.staff_summary(session, "teacher").on_leave_today == 0


def test_the_tab_kind_never_widens_what_a_teacher_may_read():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        teacher_user, teacher = _employee(session, school, "EMP-0001", "teacher")
        other_user, other = _employee(session, school, "EMP-0002", "teacher")

        for user, employee in ((teacher_user, teacher), (other_user, other)):
            session.add(
                LeaveRequest(
                    employee_id=employee.id,
                    requester_user_id=user.id,
                    leave_type="Casual",
                    from_date=date(2026, 11, 10),
                    to_date=date(2026, 11, 10),
                    days=1,
                    status="Pending",
                    school_id=school.id,
                )
            )
        session.commit()

        rows = leave_service.tab_requests(session, kind="staff", user=teacher_user)
        assert [row.person for row in rows] == ["Person EMP-0001"]


# --- workload numbers are the timetable's -----------------------------------


def test_the_matrix_counts_the_timetables_own_periods():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, teacher = _employee(session, school, "EMP-0001", "teacher")
        for day, hour in (
            (DayOfWeek.monday, 9),
            (DayOfWeek.tuesday, 9),
            (DayOfWeek.wednesday, 10),
        ):
            session.add(
                TimetablePeriod(
                    classroom_id=uuid4(),
                    subject_id=uuid4(),
                    teacher_id=teacher.id,
                    day_of_week=day,
                    start_time=time(hour, 0),
                    end_time=time(hour + 1, 0),
                    school_id=school.id,
                )
            )
        session.commit()

        rows = teachers_service.workload_matrix(session)
        row = next(item for item in rows if item.id == teacher.id)
        assert row.periods == 3
        # No rule written: the denominator is the timetable's own slot count.
        assert row.capacity_source == "timetable"
        assert row.capacity == row.week_slots
        assert row.band in {"Light", "Steady", "Overloaded", "Unassigned"}


# --- money is decimal --------------------------------------------------------


def test_money_columns_are_numeric_12_2():
    from app.domains.finance.fees.models import FeeTransaction
    from app.domains.operations.fees_structure.models import FeeStructure
    from app.domains.operations.salary.models import EmployeeSalary, SalaryPayment

    checked = [
        (FeeStructure, "amount"),
        (FeeTransaction, "amount_paid"),
        (EmployeeSalary, "salary_monthly"),
        (SalaryPayment, "gross"),
        (SalaryPayment, "deductions"),
        (SalaryPayment, "net"),
    ]
    for model, name in checked:
        column = model.__table__.columns[name]
        assert isinstance(column.type, Numeric), (
            f"{model.__name__}.{name} is not numeric"
        )
        assert (column.type.precision, column.type.scale) == (12, 2), (
            f"{model.__name__}.{name} is not numeric(12,2)"
        )
