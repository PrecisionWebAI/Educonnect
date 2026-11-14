"""The People contract: what the staff screens read, and who may read it.

Each of these started as a defect the browser could not report, because an empty
column or a wrong number never throws:

* `qualification` was typed `str` while the column is nullable, so one employee
  hired without one made the **whole** directory answer `500`;
* `status` was `"On Leave" if not user.is_active`, which reported a suspended
  login as being on leave and never reported an actual approved leave;
* `workload` defaulted to 18, so anybody the timetable query missed showed a load
  of 18 periods a week;
* the list endpoint had no scope check, so a **teacher** could page through every
  colleague's phone, email and class load;
* the leave rows answered with `name`/`from` while the screen read
  `staff`/`from_date`, and the columns came out empty with no error anywhere.

Runs on an in-memory SQLite schema, like `test_tenancy.py`: no dev database, no
HTTP client, and each scenario builds its own school.
"""

import importlib
from datetime import date, time, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import repository as teacher_repository
from app.domains.people.teachers import service as teachers
from app.domains.people.teachers.models import TeacherSubject
from app.domains.services.leave import service as leave
from app.domains.services.leave.models import LeaveRequest


def engine():
    """A fresh in-memory database with every model's table."""
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("teacher", "Teacher"),
        ("hod", "Head of Department"),
        ("accountant", "Accountant"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _user(session: Session, name: str, school_id, roles: tuple[str, ...]) -> User:
    user = User(
        # A login per person: the *whole* name makes the address, or two teachers
        # whose names start with the same word collide on `user.email`.
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


def seed(created) -> dict:
    """One school with three teachers, plus a second school to test isolation.

    The three are deliberately different kinds of "not here today":

    * **Teacher One** has an approved leave covering today;
    * **Teacher Two** has a switched-off login and no leave - the account is
      suspended, they are not away;
    * **Teacher Leaver** has a `left_on` date, i.e. is off the roll.
    """
    with Session(created) as session:
        first = School(name="First school", code="aaa", email="a@test")
        second = School(name="Second school", code="bbb", email="b@test")
        session.add_all([first, second])
        session.commit()
        session.refresh(first)
        session.refresh(second)

        session.info["school_id"] = first.id
        _roles(session)

        principal = _user(session, "Principal One", first.id, ("principal",))
        one = _user(session, "Teacher One", first.id, ("teacher",))
        two = _user(session, "Teacher Two", first.id, ("teacher",))
        leaver = _user(session, "Teacher Leaver", first.id, ("teacher",))
        two.is_active = False
        session.add(two)
        session.commit()

        one_row = _employee(session, one, "EMP-0001", qualification=None)
        two_row = _employee(session, two, "EMP-0002", qualification="B.Ed")
        leaver_row = _employee(
            session, leaver, "EMP-0003", qualification="M.A", left_on=date(2026, 1, 31)
        )

        classname = ClassName(classname="Class 9", level=9)
        section = Section(section_name="A")
        session.add_all([classname, section])
        session.commit()
        session.refresh(classname)
        session.refresh(section)

        room = Classroom(
            class_id=classname.class_id,
            section_id=section.section_id,
            class_teacher_id=one_row.id,
        )
        physics = Subject(name="Physics", code="PHY")
        session.add_all([room, physics])
        session.commit()
        session.refresh(room)
        session.refresh(physics)

        session.add(TeacherSubject(teacher_id=one_row.id, subject_id=physics.id))
        session.add(
            SubjectTeacher(
                teacher_id=one_row.id, subject_id=physics.id, classroom_id=room.id
            )
        )
        # Four teaching slots in the week; Teacher One has two of them.
        for index, (day, start) in enumerate(
            (
                (DayOfWeek.monday, time(9, 0)),
                (DayOfWeek.monday, time(10, 0)),
                (DayOfWeek.tuesday, time(9, 0)),
                (DayOfWeek.tuesday, time(10, 0)),
            )
        ):
            session.add(
                TimetablePeriod(
                    classroom_id=room.id,
                    subject_id=physics.id,
                    teacher_id=one_row.id if index < 2 else two_row.id,
                    day_of_week=day,
                    start_time=start,
                    end_time=time(start.hour + 1, 0),
                )
            )
        session.commit()

        today = date.today()
        session.add(
            LeaveRequest(
                employee_id=one_row.id,
                requester_user_id=one.id,
                leave_type="Medical",
                from_date=today - timedelta(days=1),
                to_date=today + timedelta(days=1),
                days=3,
                reason="Fever",
                status="Approved",
            )
        )
        # A past leave that must not colour today's status.
        session.add(
            LeaveRequest(
                employee_id=leaver_row.id,
                requester_user_id=leaver.id,
                leave_type="Casual",
                from_date=today - timedelta(days=30),
                to_date=today - timedelta(days=29),
                days=2,
                status="Approved",
            )
        )
        session.commit()

        # The other school's teacher: never visible from the first school.
        session.info["school_id"] = second.id
        other = _user(session, "Other Teacher", second.id, ("teacher",))
        _employee(session, other, "EMP-9001")

        return {
            "first": first.id,
            "second": second.id,
            "principal": principal.id,
            "one": one.id,
            "two": two.id,
            "leaver": leaver.id,
            "other": other.id,
            "one_row": one_row.id,
            "two_row": two_row.id,
            "leaver_row": leaver_row.id,
        }


def _employee(session: Session, user: User, code: str, **extra) -> Employee:
    """An employee row for a login, with the code/joining date a real hire has."""
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=extra.pop("department", "Science"),
        qualification=extra.pop("qualification", "M.Sc"),
        joining_date=date(2021, 6, 14),
        **extra,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _rows(session: Session, **filters):
    return teachers.get_teachers(session=session, **filters)


def test_a_null_qualification_does_not_break_the_directory():
    """The regression: `qualification: str` over a nullable column answered 500."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        found = {row.staffCode: row for row in _rows(session)}

        assert found["EMP-0001"].qualification is None
        assert found["EMP-0002"].qualification == "B.Ed"
        # No invented stand-ins: the code is the employee's own.
        assert found["EMP-0001"].staffCode == "EMP-0001"


def test_status_reports_employment_and_leave_not_the_login_switch():
    """`On Leave` is an approved leave; a suspended login is not away."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        status = {row.staffCode: row.status for row in _rows(session)}

        assert status["EMP-0001"] == labels.ON_LEAVE
        assert status["EMP-0002"] == labels.ACTIVE  # login off, not on leave
        assert status["EMP-0003"] == labels.INACTIVE  # left the school


def test_workload_and_utilisation_come_from_the_timetable():
    """Two periods, a four-slot week: 2 periods and 50%, not the old fixed 18."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        found = {row.staffCode: row for row in _rows(session)}
        assert found["EMP-0001"].workload == 2
        assert found["EMP-0002"].workload == 2

        matrix = {row.staff: row for row in teachers.workload_matrix(session)}
        assert matrix["Teacher One"].periods == 2
        assert matrix["Teacher One"].capacity == 4
        assert matrix["Teacher One"].utilisation == 50
        # A teacher with no period is a row, not a gap to hide.
        assert matrix["Teacher Leaver"].periods == 0


def test_the_summary_counts_the_whole_roll():
    """Tiles are the school's numbers, whatever the table is filtered to."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        summary = teachers.staff_summary(session)

        assert summary.total == 3
        assert summary.on_leave_today == 1
        assert summary.inactive == 1
        assert summary.active == 1  # Teacher Two: login off, still on the roll
        assert summary.periods_per_week == 4
        assert summary.without_timetable == 0


def test_the_directory_filters_on_the_server():
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]

        assert [row.staffCode for row in _rows(session, q="Teacher Two")] == [
            "EMP-0002"
        ]
        # Ordered by name - "Leaver" < "One" < "Two" - which is what keeps the
        # browser's paging stable between requests.
        assert [row.staffCode for row in _rows(session, department="science")] == [
            "EMP-0003",
            "EMP-0001",
            "EMP-0002",
        ]
        assert [row.staffCode for row in _rows(session, status=labels.ON_LEAVE)] == [
            "EMP-0001"
        ]
        # Filtering by "Inactive" must still find somebody whose roles were
        # withdrawn - the very row an administrator goes looking for.
        assert [row.staffCode for row in _rows(session, status=labels.INACTIVE)] == [
            "EMP-0003"
        ]
        assert _rows(session, q="nobody by this name") == []


def test_a_teacher_only_account_sees_its_own_record():
    """`teachers.read` is not "read every colleague"."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        one = session.get(User, ids["one"])

        own = teachers.get_teachers(session=session, user=one)
        assert [row.staffCode for row in own] == ["EMP-0001"]

        with pytest.raises(HTTPException) as refused:
            teachers.get_teacher(session=session, teacher_id=ids["two_row"], user=one)
        assert refused.value.status_code == 404


def test_leadership_reads_the_school_and_may_open_one_record():
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        principal = session.get(User, ids["principal"])

        everyone = teachers.get_teachers(session=session, user=principal)
        assert sorted(row.staffCode for row in everyone) == [
            "EMP-0001",
            "EMP-0002",
            "EMP-0003",
        ]
        row = teachers.get_teacher(
            session=session, teacher_id=ids["two_row"], user=principal
        )
        assert row.staffCode == "EMP-0002"


def test_another_schools_people_never_appear():
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        assert "EMP-9001" not in {row.staffCode for row in _rows(session)}

    with Session(created) as session:
        session.info["school_id"] = ids["second"]
        assert [row.staffCode for row in _rows(session)] == ["EMP-9001"]


def test_staff_leave_rows_carry_the_fields_the_screen_reads():
    """`staff_name` / `from_date` / `to_date`, in the catalog's role word."""
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        rows = {row.staff_name: row for row in leave.list_staff_leave(session)}

        on_leave = rows["Teacher One"]
        assert on_leave.staff_code == "EMP-0001"
        assert on_leave.role == "Teacher"  # a label, not the `teacher` codename
        assert on_leave.leave_type == "Medical"
        assert on_leave.from_date.startswith(f"{date.today().year}/")
        assert on_leave.to_date
        assert on_leave.reason == "Fever"
        # Nothing invented where the domain has no data yet.
        assert on_leave.substitute is None
        assert on_leave.balance is None
        # A student's leave is the other screen's row, not this one's.
        assert all(row.staff_name for row in rows.values())


def test_the_directory_lists_teaching_posts_and_not_every_employee():
    """Membership is the *post*, not "has an employee row".

    `teacher`, `hod`, `vice_principal` and `principal` stand in front of classes,
    so they belong here; an accountant is staff but never takes a class. This is
    also the rule that keeps a hire from one screen out of the other: the Hired
    tab's `isTeacher` flag reads the same list.
    """
    created = engine()
    ids = seed(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        hod = _user(session, "Hod One", ids["first"], ("hod",))
        _employee(session, hod, "EMP-0004")
        accounts = _user(session, "Accounts One", ids["first"], ("accountant",))
        _employee(session, accounts, "EMP-0005")

        codes = [row.staffCode for row in _rows(session)]
        assert "EMP-0004" in codes  # an HOD teaches
        assert "EMP-0005" not in codes  # the accountant does not
        assert teachers.staff_summary(session).total == 4


def test_the_directory_statement_is_postgres_safe():
    """`SELECT DISTINCT … ORDER BY "user".full_name` is refused by PostgreSQL.

    SQLite runs it happily, so the SQLite tests stayed green while the live list
    answered 500 ("for SELECT DISTINCT, ORDER BY expressions must appear in select
    list"). Membership is therefore a subquery, never a joined `DISTINCT` - and the
    statement still has to be ordered, because the browser pages through it.
    """
    sql = str(
        teacher_repository.teachers_statement().compile(
            compile_kwargs={"literal_binds": True}
        )
    ).upper()

    assert "DISTINCT" not in sql
    assert "ORDER BY" in sql
