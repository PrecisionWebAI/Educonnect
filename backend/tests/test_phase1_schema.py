"""Phase 1: the schema safety net - reserved names, uniques, money, and the renamed table.

Every test here fails for a rule the phase was asked to enforce:

* **`user` is not a table any more** - `app_user` is (reserved word, Rule 6);
* **one employee code per school** - and two schools may each own EMP-0001;
* **no teacher in two rooms at 09:00** (the double-booking key);
* **money is a decimal, not a float** - 1234.56 round-trips as 1234.56;
* **`securitylog`/`chatfile` no longer have columns called `user`/`when`**.

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import SecurityLog
from app.domains.admin.users.models import User
from app.domains.finance.fees.models import FeeTransaction, PaymentMode
from app.domains.main.chat.models import ChatFile
from app.domains.operations.salary.models import SalaryPayment
from app.domains.people.staff.models import Employee


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


def _person(session: Session, school: School, code: str) -> Employee:
    user = User(
        # Unique per call: the test is about the *employee code* rule, and a shared
        # email would fail first (the login is unique per school).
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
    return employee


def test_the_login_table_is_named_app_user():
    """Rule 6: `user` is a keyword; the table is `app_user` and nothing else."""
    assert User.__tablename__ == "app_user"
    assert "app_user" in SQLModel.metadata.tables
    assert "user" not in SQLModel.metadata.tables


def test_one_employee_code_is_unique_inside_a_school():
    created = engine()
    session = _session(created)
    school = _school(session, "AAA-0001")
    _person(session, school, "EMP-0001")

    with pytest.raises(IntegrityError):
        _person(session, school, "EMP-0001")


def test_two_schools_may_each_start_at_emp_0001():
    """The composite key is the point: EMP-0001 is a school's number, not a global one."""
    created = engine()
    one, two = _session(created), _session(created)
    school_one = _school(one, "BBB-0001")
    school_two = _school(two, "CCC-0001")
    # Bind each session to its school, so the assertions below also prove isolation.
    one.info["school_id"] = school_one.id
    two.info["school_id"] = school_two.id

    _person(one, school_one, "EMP-0001")
    _person(two, school_two, "EMP-0001")

    assert [row.employee_code for row in one.exec(select(Employee)).all()] == [
        "EMP-0001"
    ]
    assert [row.employee_code for row in two.exec(select(Employee)).all()] == [
        "EMP-0001"
    ]


def test_a_teacher_cannot_be_in_two_rooms_at_nine():
    created = engine()
    session = _session(created)
    school = _school(session, "DDD-0001")
    teacher = _person(session, school, "EMP-0001")

    def period(start: time) -> TimetablePeriod:
        return TimetablePeriod(
            classroom_id=uuid4(),
            subject_id=uuid4(),
            teacher_id=teacher.id,
            day_of_week=DayOfWeek.monday,
            start_time=start,
            end_time=time(start.hour + 1, 0),
            school_id=school.id,
        )

    session.add(period(time(9, 0)))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(period(time(9, 0)))
        session.commit()


def test_the_next_period_is_fine():
    """The key is the slot, not the teacher: 10:00 is a different room."""
    created = engine()
    session = _session(created)
    school = _school(session, "EEE-0001")
    teacher = _person(session, school, "EMP-0001")
    for hour in (9, 10):
        session.add(
            TimetablePeriod(
                classroom_id=uuid4(),
                subject_id=uuid4(),
                teacher_id=teacher.id,
                day_of_week=DayOfWeek.monday,
                start_time=time(hour, 0),
                end_time=time(hour + 1, 0),
                school_id=school.id,
            )
        )
    session.commit()
    assert len(session.exec(select(TimetablePeriod)).all()) == 2


def test_money_is_a_decimal_and_survives_the_round_trip():
    """Rule 4: `numeric(12,2)` in the schema; 1234.56 stays 1234.56."""
    created = engine()
    session = _session(created)
    school = _school(session, "FFF-0001")
    payment = FeeTransaction(
        student_id=uuid4(),
        fee_structure_id=uuid4(),
        amount_paid=Decimal("1234.56"),
        date=date(2026, 11, 14),
        payment_mode=PaymentMode.cash,
        receipt_number="RCPT-1",
        school_id=school.id,
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)

    stored = session.get(FeeTransaction, payment.id)
    assert stored.amount_paid == Decimal("1234.56")
    assert str(stored.amount_paid.as_tuple().exponent) == "-2"


def test_the_salary_register_holds_decimals_not_floats():
    """`gross`, `deductions`, `net` are money columns, `numeric(12,2)` each."""
    created = engine()
    session = _session(created)
    school = _school(session, "GGG-0001")
    employee = _person(session, school, "EMP-0001")
    session.add(
        SalaryPayment(
            employee_id=employee.id,
            month="Nov 2026",
            gross=Decimal("50000.00"),
            deductions=Decimal("2500.50"),
            net=Decimal("47499.50"),
            school_id=school.id,
        )
    )
    session.commit()

    stored = session.exec(select(SalaryPayment)).one()
    assert stored.net == Decimal("47499.50")
    assert stored.net == stored.gross - stored.deductions


def test_no_model_column_is_called_user_or_when():
    """Rule 6: the reserved words are gone from the columns too, not just the table."""
    assert {"actor_email", "occurred_at"} <= set(SecurityLog.__table__.columns.keys())
    assert "user" not in SecurityLog.__table__.columns
    assert "when" not in SecurityLog.__table__.columns
    assert "shared_at" in ChatFile.__table__.columns
    assert "when" not in ChatFile.__table__.columns


def test_school_keys_are_unique():
    """`school.code`, `.name` and `.email` are the three keys the model declares."""
    created = engine()
    session = _session(created)
    _school(session, "HHH-0001")

    with pytest.raises(IntegrityError):
        session.add(
            School(
                name="Another name",
                code="HHH-0001",
                email="other@hhh.test",
                phone="9999999998",
            )
        )
        session.commit()
