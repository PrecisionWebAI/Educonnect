"""The staff profile: what it answers, who may change it, and what it refuses.

Each test here is a rule a profile drawer has to get right, and each one is
invisible in the browser when it is wrong:

* the profile must describe **the same person the directory row did** - a drawer
  that shows a different status or workload from the row behind it is worse than
  no drawer at all;
* a teacher must not read a colleague's profile (`404`, not `403`: an API must not
  confirm that somebody else's id exists);
* an HOD may edit **inside their own department only**, and `teachers.update` is
  not that rule - it says they edit profiles at all;
* a leaver's profile stays readable but is **read-only** (`409`);
* a duplicate degree is `409` naming the pair, not a silent second row;
* a designation change is **history**: appended, never an overwrite;
* a row id is looked up **within the employee**, so a caller who may edit one
  profile cannot delete another's row by guessing its id.

Runs on an in-memory SQLite schema like `test_people_contracts.py`: no dev
database, no HTTP client, and every test builds its own school.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import Subject
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import service as teachers
from app.domains.people.teachers.profile import service as profile
from app.domains.people.teachers.profile.models import (
    StaffCertification,
    StaffEmploymentHistory,
    StaffExperience,
    StaffQualification,
)
from app.domains.people.teachers.profile.schemas import (
    EmploymentUpdate,
    ExperienceCreate,
    QualificationCreate,
)


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


def session_for(created, school_id):
    """A session bound to one school whose objects stay readable after a commit.

    `expire_on_commit=False` matters here: these tests hand the seed's `User` and
    `Employee` straight to the code under test, and the default setting expires
    every attribute at the first commit - so reading `.id` after the seed's session
    closed would raise `DetachedInstanceError` instead of exercising the rule.
    """
    session = Session(created, expire_on_commit=False)
    session.info["school_id"] = school_id
    return session


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("teacher", "Teacher"),
        ("hod", "Head of Department"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _user(session: Session, name: str, school_id, roles: tuple[str, ...]) -> User:
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


def _employee(session: Session, user: User, code: str, **extra) -> Employee:
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=extra.pop("department", "Science"),
        qualification=extra.pop("qualification", None),
        joining_date=extra.pop("joining_date", date(2023, 6, 1)),
        email=f"{code.lower()}@test",
        **extra,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def seed(created) -> dict:
    """One school: a principal, a Science HOD, two teachers, a leaver, two subjects.

    The leaver holds a teaching role **and** a `left_on` date, which is exactly the
    row `status="Inactive"` finds - the profile must keep showing them and must
    refuse to edit them.
    """
    with Session(created, expire_on_commit=False) as session:
        first = School(name="First school", code="aaa", email="a@test")
        second = School(name="Second school", code="bbb", email="b@test")
        session.add_all([first, second])
        session.commit()
        session.refresh(first)
        session.refresh(second)

        session.info["school_id"] = first.id
        _roles(session)

        principal = _user(session, "Principal One", first.id, ("principal",))
        hod = _user(session, "Hod Science", first.id, ("hod", "teacher"))
        one = _user(session, "Teacher One", first.id, ("teacher",))
        two = _user(session, "Teacher Two", first.id, ("teacher",))
        leaver = _user(session, "Teacher Leaver", first.id, ("teacher",))

        principal_row = _employee(session, principal, "EMP-0000")
        hod_row = _employee(session, hod, "EMP-0001", department="Science")
        one_row = _employee(session, one, "EMP-0002", department="Science")
        two_row = _employee(session, two, "EMP-0003", department="Maths")
        leaver_row = _employee(
            session, leaver, "EMP-0004", department="Science", left_on=date(2026, 1, 31)
        )

        physics = Subject(name="Physics", code="PHY")
        chemistry = Subject(name="Chemistry", code="CHM")
        session.add_all([physics, chemistry])
        session.commit()
        session.refresh(physics)
        session.refresh(chemistry)

        session.info["school_id"] = second.id
        other = _user(session, "Other Teacher", second.id, ("teacher",))
        other_row = _employee(session, other, "EMP-0005", department="Science")

        return {
            "school": first.id,
            "principal": principal,
            "principal_row": principal_row,
            "hod": hod,
            "hod_row": hod_row,
            "one": one,
            "one_row": one_row,
            "two": two,
            "two_row": two_row,
            "leaver": leaver,
            "leaver_row": leaver_row,
            "other_row": other_row,
            "physics": physics.id,
            "chemistry": chemistry.id,
        }


# --- structure ------------------------------------------------------------


def test_the_profile_tables_are_tenant_owned_and_registered():
    """Every profile table carries `school_id`, or a profile leaks across schools."""
    assert "people.teachers.profile" in MODEL_MODULES
    for table in (
        StaffQualification,
        StaffExperience,
        StaffCertification,
        StaffEmploymentHistory,
    ):
        assert "school_id" in table.__table__.columns, table.__tablename__


# --- reads ----------------------------------------------------------------


def test_the_profile_describes_the_row_it_was_opened_from():
    """The drawer and the table must not disagree about the same person."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        row = teachers.get_teacher(session, ids["one_row"].id, ids["principal"])
        full = teachers.teacher_profile(session, ids["one_row"].id, ids["principal"])

        assert full.name == row.name
        assert full.staff_code == row.staffCode
        assert full.status == row.status == "Active"
        assert full.department == row.department
        assert full.workload == row.workload
        # Nothing is invented for a person with no timetable: no week, no percentage.
        assert full.capacity == 0
        assert full.utilisation == 0
        assert full.qualifications == []


def test_a_teacher_cannot_read_a_colleagues_profile():
    """`404`, not `403`: the answer must not confirm that the id exists."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        with pytest.raises(HTTPException) as caught:
            teachers.teacher_profile(session, ids["two_row"].id, ids["one"])
        assert caught.value.status_code == 404

        own = teachers.teacher_profile(session, ids["one_row"].id, ids["one"])
        assert own.id == ids["one_row"].id


def test_a_cross_school_profile_is_not_found():
    """The tenant listener narrows the read; somebody else's school is just absent."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        with pytest.raises(HTTPException) as caught:
            teachers.teacher_profile(session, ids["other_row"].id, ids["principal"])
        assert caught.value.status_code == 404


# --- writes: who ----------------------------------------------------------


def test_an_hod_edits_inside_their_department_only():
    """`teachers.update` is not the rule; the department is."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]

        colleague = profile.require_employee(session, ids["one_row"].id, ids["hod"])
        profile.require_edit(session, colleague, ids["hod"])  # Science -> Science

        elsewhere = profile.require_employee(session, ids["two_row"].id, ids["hod"])
        with pytest.raises(HTTPException) as caught:
            profile.require_edit(session, elsewhere, ids["hod"])
        assert caught.value.status_code == 403

        # A principal may edit both - the school-level role is not narrowed.
        profile.require_edit(session, elsewhere, ids["principal"])


def test_a_leavers_profile_is_readable_but_frozen():
    """Off the roll is `409`, with a message that names the way back in."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]

        full = teachers.teacher_profile(session, ids["leaver_row"].id, ids["principal"])
        assert full.status == "Inactive"

        leaver = profile.require_employee(
            session, ids["leaver_row"].id, ids["principal"]
        )
        with pytest.raises(HTTPException) as caught:
            profile.require_edit(session, leaver, ids["principal"])
        assert caught.value.status_code == 409
        assert "Reactivate" in caught.value.detail


# --- writes: the lists ----------------------------------------------------


def test_a_duplicate_degree_is_a_conflict():
    """The 409 names the pair it found, in the form the database stores."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        employee = profile.require_employee(
            session, ids["one_row"].id, ids["principal"]
        )

        row = profile.add_qualification(
            session, employee, QualificationCreate(degree="B.Ed", year_completed=2019)
        )
        assert row.degree == "b.ed"  # canonical text, lower-cased on the way in

        with pytest.raises(HTTPException) as caught:
            profile.add_qualification(
                session,
                employee,
                QualificationCreate(degree="B.Ed", year_completed=2019),
            )
        assert caught.value.status_code == 409
        assert "b.ed (2019)" in caught.value.detail

        # A different year is a different qualification, not a duplicate.
        profile.add_qualification(
            session, employee, QualificationCreate(degree="B.Ed", year_completed=2022)
        )
        assert len(profile.reads(session, employee.id).qualifications) == 2


def test_a_row_of_another_employee_is_not_found():
    """The row id is looked up **within** the employee in the path."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        one = profile.require_employee(session, ids["one_row"].id, ids["principal"])
        two = profile.require_employee(session, ids["two_row"].id, ids["principal"])

        row = profile.add_qualification(session, one, QualificationCreate(degree="M.Sc"))
        with pytest.raises(HTTPException) as caught:
            profile.delete_qualification(session, two, row.id)
        assert caught.value.status_code == 404


def test_an_experience_that_ends_before_it_starts_is_refused():
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        employee = profile.require_employee(
            session, ids["one_row"].id, ids["principal"]
        )

        with pytest.raises(HTTPException) as caught:
            profile.add_experience(
                session,
                employee,
                ExperienceCreate(
                    employer="Delhi Public School",
                    from_date=date(2020, 6, 1),
                    to_date=date(2019, 6, 1),
                ),
            )
        assert caught.value.status_code == 400


def test_subjects_are_replaced_and_an_unknown_id_is_refused():
    """A replace, and a bad id refuses **before** anything is deleted."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        employee = profile.require_employee(
            session, ids["one_row"].id, ids["principal"]
        )

        names = profile.set_subjects(
            session, employee, [ids["physics"], ids["chemistry"], ids["physics"]]
        )
        assert names == ["Chemistry", "Physics"]

        with pytest.raises(HTTPException) as caught:
            profile.set_subjects(session, employee, [ids["chemistry"], uuid4()])
        assert caught.value.status_code == 400

        # The refusal changed nothing: the list is still exactly what it was.
        assert profile.subject_names(session, employee.id) == ["Chemistry", "Physics"]


# --- writes: the post -----------------------------------------------------


def test_a_designation_change_is_appended_to_the_history():
    """A promotion is an event, not an overwrite - and saving again adds nothing."""
    created = engine()
    ids = seed(created)
    with Session(created, expire_on_commit=False) as session:
        session.info["school_id"] = ids["school"]
        employee = profile.require_employee(
            session, ids["one_row"].id, ids["principal"]
        )

        profile.update_employment(
            session,
            employee,
            EmploymentUpdate(designation="Senior Teacher", employment_type="Full-time"),
            ids["principal"],
        )
        assert employee.designation == "senior teacher"
        assert employee.employment_type == "Full-time"

        history = profile.reads(session, employee.id).history
        assert [row.event for row in history] == ["Designation changed"]
        assert history[0].to_value == "senior teacher"
        assert history[0].recorded_by == "Principal One"

        # The same designation in different capitals is not a second promotion.
        profile.update_employment(
            session,
            employee,
            EmploymentUpdate(designation="senior teacher"),
            ids["principal"],
        )
        assert len(profile.reads(session, employee.id).history) == 1





