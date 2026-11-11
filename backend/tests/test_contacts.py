"""One contact, one person - the rules in `app/core/contacts.py`.

The scenarios here are what the admission form, the hire form and the interview form
all run into, so they are worth knowing exactly:

    1. a second family may not reuse a guardian's number;
    2. the **same person** (a teacher whose child studies here) keeps their own number
       and address - one person, one contact;
    3. a student's own email is not a login for somebody else;
    4. the form's popup names the person and the children already linked;
    5. an edit moves every record of that person together (`sync_contact`);
    6. a contact another person holds is never taken over.

The scenarios are plain functions (`check_*`) that build their own throw-away SQLite
schema, so this file runs under pytest **and** on its own, without dev dependencies.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core import contacts
from app.core.schema import MODEL_MODULES as _MODEL_MODULES
from app.domains.auth.models import Role
from app.domains.auth.roles import set_user_roles
from app.domains.admin.platform.models import School
from app.domains.people.staff.models import Employee
from app.domains.academic.classroom.students.models import Guardian, Student, StudentGuardianRelationship
from app.domains.admin.users.models import User

#: The role catalog rows these scenarios need (a real database seeds them).
_ROLES = ("teacher", "guardian", "student")


def load_every_model() -> None:
    import importlib

    for domain in _MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")


def memory_session() -> Session:
    """A throw-away in-memory database with the whole schema on it."""
    load_every_model()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session) -> School:
    for codename in _ROLES:
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="contacts test school", code="ct", email="ct@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    # Bind the session to the school, the way a request does: every row written from
    # here belongs to it.
    session.info["school_id"] = school.id
    return school


def _user(session: Session, email: str, name: str, roles: list[str]) -> User:
    user = User(email=email, full_name=name, hashed_password="x", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    if roles:
        set_user_roles(session, user, roles)
    return user


def _student(session: Session, **overrides) -> Student:
    """A student the way the product makes one now: a row with an admission number.

    The guardian block the form collects is **not** part of the row any more - a parent
    is a `Guardian` row linked through `StudentGuardianRelationship` - so the scenarios
    here build that link themselves.
    """
    values = {
        "student_first_name": "child",
        "full_name": "child one",
        "admission_number": "CT-1",
        "date_of_birth": date(2015, 1, 1),
    }
    values.update(overrides)
    student = Student(**values)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def seed(session: Session) -> dict:
    """One family, one stranger, and one teacher who is also that parent.

    * `parent`   - a login holding `teacher` **and** `guardian`, a staff record and a
      guardian record: the same person in three shapes.
    * `child`    - their child, linked to `parent`, with an address of their own.
    * `stranger` - a second guardian with a number and an address of their own.
    """
    _school(session)
    parent_user = _user(session, "parent@test", "parent person", ["teacher", "guardian"])
    parent = Guardian(
        name="parent person",
        phone="9000000101",
        email="parent@test",
        user_id=parent_user.id,
        occupation="teacher",
    )
    stranger = Guardian(
        name="stranger person", phone="9000000202", email="stranger@test"
    )
    session.add(parent)
    session.add(stranger)
    session.commit()
    session.refresh(parent)
    session.refresh(stranger)

    employee = Employee(
        user_id=parent_user.id,
        employee_code="EMP-CT-1",
        department="science",
        joining_date=date(2020, 6, 1),
        email="parent@test",
        phone="9000000101",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)

    child = _student(session, student_email="child.own@test", user_id=None)
    session.add(
        StudentGuardianRelationship(
            student_id=child.id,
            guardian_id=parent.id,
            relationship_type="father",
            is_primary=True,
        )
    )
    session.commit()
    return {
        "parent_user": parent_user,
        "parent": parent,
        "stranger": stranger,
        "employee": employee,
        "child": child,
    }


def _refusal(session: Session, **kwargs) -> HTTPException:
    """Run `require_contact_free` and hand back the refusal it raised."""
    try:
        contacts.require_contact_free(session, **kwargs)
    except HTTPException as error:
        return error
    raise AssertionError("the contact was accepted, but another person holds it")


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_phone_of_another_person_is_refused(session: Session) -> None:
    """A second family cannot file itself under a number somebody already has."""
    seed(session)
    refused = _refusal(session, who="The guardian", phone="9000000202")
    assert refused.status_code == 409
    assert "stranger person" in refused.detail
    assert "phone number '9000000202'" in refused.detail


def check_phone_normalisation_finds_the_same_person(session: Session) -> None:
    """`+91 90000 00101` and `9000000101` are one number, not two."""
    seed(session)
    holder = contacts.find_contact(session, phone="+91 90000 00101")
    assert holder is not None
    assert holder.kind in (contacts.KIND_LOGIN, contacts.KIND_GUARDIAN)
    assert holder.name == "parent person"


def check_same_person_keeps_their_own_contact(session: Session) -> None:
    """A teacher whose child studies here is one person: their own number is theirs."""
    data = seed(session)
    contacts.require_contact_free(
        session,
        who="The guardian",
        phone="9000000101",
        email="parent@test",
        allow_user_id=data["parent_user"].id,
    )  # must not raise


def check_a_students_own_email_is_not_a_login(session: Session) -> None:
    """A child is not a login: their address cannot be handed to somebody else."""
    data = seed(session)
    assert data["child"].student_email == "child.own@test"
    refused = _refusal(session, who="The new guardian", email="child.own@test")
    assert refused.status_code == 409


def check_the_popup_names_the_person_and_their_children(session: Session) -> None:
    """What the form shows when a contact is already on file."""
    seed(session)
    read = contacts.contact_read(session, phone="9000000202")
    assert read["found"] is True
    assert read["name"] == "stranger person"
    assert read["guardianId"] is not None
    assert "stranger person" in read["message"]

    mine = contacts.contact_read(session, phone="9000000101")
    assert mine["found"] is True
    assert set(mine["roles"]) == {"guardian", "teacher"}
    assert [child["name"] for child in mine["children"]] == ["child one"]

    empty = contacts.contact_read(session, phone="9777777777")
    assert empty["found"] is False
    assert "Nobody on file" in empty["message"]


def check_sync_moves_every_row_of_one_person(session: Session) -> None:
    """An edit reaches the login, the guardian row **and** the staff row."""
    data = seed(session)
    notes = contacts.sync_contact(
        session,
        guardian_id=data["parent"].id,
        email="moved@test",
        phone="9000000303",
    )
    session.refresh(data["parent_user"])
    session.refresh(data["parent"])
    session.refresh(data["employee"])
    assert data["parent_user"].email == "moved@test"
    assert data["parent"].email == "moved@test"
    assert data["employee"].email == "moved@test"
    assert data["parent"].phone == "9000000303"
    assert data["employee"].phone == "9000000303"
    assert any("login changed" in note for note in notes)


def check_sync_never_takes_another_persons_contact(session: Session) -> None:
    """The stranger's number stays theirs; the note says what was left alone."""
    data = seed(session)
    notes = contacts.sync_contact(
        session, guardian_id=data["parent"].id, phone="9000000202"
    )
    session.refresh(data["parent"])
    assert data["parent"].phone == "9000000101"
    assert any("already belongs to another person" in note for note in notes)


# ---------------------------------------------------------------------------
# What pytest collects (each test builds its own in-memory database)
# ---------------------------------------------------------------------------


def test_phone_of_another_person_is_refused():
    with memory_session() as session:
        check_phone_of_another_person_is_refused(session)


def test_phone_normalisation_finds_the_same_person():
    with memory_session() as session:
        check_phone_normalisation_finds_the_same_person(session)


def test_same_person_keeps_their_own_contact():
    with memory_session() as session:
        check_same_person_keeps_their_own_contact(session)


def test_a_students_own_email_is_not_a_login():
    with memory_session() as session:
        check_a_students_own_email_is_not_a_login(session)


def test_the_popup_names_the_person_and_their_children():
    with memory_session() as session:
        check_the_popup_names_the_person_and_their_children(session)


def test_sync_moves_every_row_of_one_person():
    with memory_session() as session:
        check_sync_moves_every_row_of_one_person(session)


def test_sync_never_takes_another_persons_contact():
    with memory_session() as session:
        check_sync_never_takes_another_persons_contact(session)


#: (label, scenario) - the same rules pytest checks, runnable without pytest.
SCENARIOS = (
    (
        "a second family cannot reuse a guardian's number",
        check_phone_of_another_person_is_refused,
    ),
    (
        "a number finds the same person however it is typed",
        check_phone_normalisation_finds_the_same_person,
    ),
    (
        "the same person keeps their own contact",
        check_same_person_keeps_their_own_contact,
    ),
    ("a student's own email is not a login", check_a_students_own_email_is_not_a_login),
    (
        "the popup names the person and their children",
        check_the_popup_names_the_person_and_their_children,
    ),
    ("an edit moves every row of one person", check_sync_moves_every_row_of_one_person),
    ("a contact is never taken over", check_sync_never_takes_another_persons_contact),
)


