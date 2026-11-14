"""Phase 3: the Teachers / Staff split (0.9), pagination, and the register's roll.

Every test here fails for a rule the phase added:

* **one employee, one list** - a teaching role puts you in Teachers, any other
  role in Staff, and nobody in both (the rule is the role list read two ways);
* **pagination is the server's** - `skip`/`limit` page the same filtered query, and
  `count_teachers` reports the total the page did not load;
* **filters compose** - a search with a department still returns only matching
  rows, on any page;
* **an empty school answers empty** - `[]`, not an error, not an invented row;
* **the register covers staff too** - the 0.9 bug: it was built from the teaching
  roll, so an accountant had no row in the "staff" register;
* **the periods tile is hidden for staff** (`shows_periods`), and a teacher's
  periods are the timetable's own count.

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date, time
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import repository, service


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


def _school(session: Session, code: str = "PS3") -> School:
    for codename in ("teacher", "hod", "school_admin", "accountant", "librarian"):
        if not session.exec(select(Role).where(Role.codename == codename)).first():
            session.add(Role(codename=codename, label=codename.replace("_", " ")))
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


def _person(
    session: Session,
    school: School,
    code: str,
    *,
    name: str | None = None,
    department: str = "Science",
    role: str = "teacher",
) -> Employee:
    user = User(
        email=f"{uuid4().hex[:10]}@test",
        full_name=name or f"User {code}",
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
        department=department,
        joining_date=date(2023, 6, 1),
        school_id=school.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


# --- the split (0.9) ---------------------------------------------------------


def test_a_teacher_and_a_staff_member_land_on_opposite_sides():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        teacher = _person(session, school, "EMP-0001", name="Anita Rao")
        accountant = _person(
            session, school, "EMP-0002", name="Ravi Kumar", role="accountant"
        )

        teaching = {row.id for row in repository.roll_employees(session, "teacher")}
        staff = {row.id for row in repository.roll_employees(session, "staff")}

        assert teacher.id in teaching and teacher.id not in staff
        assert accountant.id in staff and accountant.id not in teaching
        # and nobody is invented into a third place
        assert teaching | staff == {teacher.id, accountant.id}


def test_two_teaching_roles_still_put_one_row_in_the_list():
    """A teacher who is also an HOD: one row, not two (the join trap)."""
    created = engine()
    with _session(created) as session:
        school = _school(session)
        employee = _person(session, school, "EMP-0001", name="Anita Rao")
        user = session.get(User, employee.user_id)
        grant_role(session, user, "hod")

        rows = repository.roll_employees(session, "teacher")
        assert [row.id for row in rows] == [employee.id]


# --- pagination --------------------------------------------------------------


def test_skip_and_limit_page_the_same_filtered_query():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        for index, name in enumerate(("Anita", "Bhavna", "Chetan")):
            _person(session, school, f"EMP-000{index + 1}", name=name)

        first = repository.get_teachers(session, kind="teacher", limit=1)
        second = repository.get_teachers(session, kind="teacher", skip=1, limit=1)
        rest = repository.get_teachers(session, kind="teacher", skip=2, limit=1)

        assert [row.id for row in first] != [row.id for row in second]
        assert len({first[0].id, second[0].id, rest[0].id}) == 3
        # `limit=None` is "everything", which is what the browser pages through.
        assert len(repository.get_teachers(session, kind="teacher")) == 3


def test_the_total_counts_the_filters_not_the_page():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _person(session, school, "EMP-0001", name="Anita Rao", department="Science")
        _person(session, school, "EMP-0002", name="Bhavna Shah", department="Science")
        _person(session, school, "EMP-0003", name="Chetan Verma", department="Arts")

        assert repository.count_teachers(session, kind="teacher") == 3
        assert (
            repository.count_teachers(session, kind="teacher", department="Science")
            == 2
        )
        page = repository.get_teachers(session, kind="teacher", limit=1)
        assert len(page) == 1


def test_a_search_and_a_department_still_compose():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _person(session, school, "EMP-0001", name="Anita Rao", department="Science")
        _person(session, school, "EMP-0002", name="Anita Shah", department="Arts")

        rows = repository.get_teachers(
            session, kind="teacher", q="anita", department="Science"
        )
        assert [row.employee_code for row in rows] == ["EMP-0001"]
        assert (
            repository.count_teachers(
                session, kind="teacher", q="anita", department="Science"
            )
            == 1
        )


# --- empty school ------------------------------------------------------------


def test_an_empty_school_answers_empty_not_an_error():
    created = engine()
    with _session(created) as session:
        _school(session, "PS3E")
        assert repository.get_teachers(session, kind="teacher") == []
        assert repository.get_teachers(session, kind="staff") == []
        assert repository.count_teachers(session, kind="teacher") == 0
        # A caller scoped to ids that resolved to nothing sees nothing.
        assert repository.get_teachers(session, kind="teacher", visible_ids=set()) == []
        assert (
            repository.count_teachers(session, kind="teacher", visible_ids=set()) == 0
        )


# --- the register's roll and the tiles --------------------------------------


def test_the_register_roll_includes_staff_not_only_teachers():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        teacher = _person(session, school, "EMP-0001", role="teacher")
        accountant = _person(session, school, "EMP-0002", role="accountant")

        everyone = {row.id for row in repository.all_employees(session)}
        assert {teacher.id, accountant.id} <= everyone


def test_periods_per_week_are_the_timetables_own_rows():
    """The card's number is `timetableperiod` rows, one week - never an estimate."""
    created = engine()
    with _session(created) as session:
        school = _school(session)
        employee = _person(session, school, "EMP-0001")
        for day, hour in ((DayOfWeek.monday, 9), (DayOfWeek.tuesday, 10)):
            session.add(
                TimetablePeriod(
                    classroom_id=uuid4(),
                    subject_id=uuid4(),
                    teacher_id=employee.id,
                    day_of_week=day,
                    start_time=time(hour, 0),
                    end_time=time(hour + 1, 0),
                    school_id=school.id,
                )
            )
        session.commit()

        counts = repository.period_counts(session, [employee.id])
        assert counts[employee.id] == 2


def test_the_periods_tile_is_hidden_for_staff():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _person(session, school, "EMP-0001", role="teacher")
        _person(session, school, "EMP-0002", role="accountant")

        teaching = service.staff_summary(session, kind="teacher")
        staff = service.staff_summary(session, kind="staff")

        assert teaching.kind == "teacher" and teaching.shows_periods is True
        assert (teaching.total, teaching.active) == (1, 1)
        assert staff.kind == "staff" and staff.shows_periods is False
        assert (staff.total, staff.periods_per_week) == (1, 0)
