"""The guardian card's API - adding, editing and removing a family from a student.

Scenarios (the same ones the card's buttons produce):

    1. adding a guardian with a **new** contact creates the person and their login, and
       the first-time password comes back once;
    2. adding a contact the school already has links **that** person - a sibling's
       parent keeps one row, one login and one number, and no second password appears;
    3. a contact that belongs to another family is refused (`409`), naming them;
    4. editing a guardian moves the person's login and row together;
    5. removing a guardian unlinks this child only: the person, their login and their
       other children stay, and the primary contact passes to whoever is left.

Runs under pytest and under `scripts/_phase5_verify.py` (the API image has no pytest).
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.domains.auth.models import Role
from app.domains.schools.models import School
from app.domains.students import guardians
from app.domains.students.models import Guardian, Student, StudentGuardianRelationship
from app.domains.students.schemas import GuardianWrite
from app.domains.users.models import User

_ROLES = ("student", "guardian", "teacher")
_MODEL_MODULES = (
    "academics",
    "admissions",
    "attendance",
    "auth",
    "chat",
    "exams",
    "finance",
    "hiring",
    "homework",
    "operations",
    "salary",
    "staff",
    "students",
    "teachers",
    "timetable",
    "users",
)


def load_every_model() -> None:
    import importlib

    for domain in _MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")


def memory_session() -> Session:
    load_every_model()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _student(session: Session, name: str, number: str) -> Student:
    """A student row with an admission number - the guardian is a row of its own."""
    student = Student(
        student_first_name=name,
        full_name=name,
        admission_number=number,
        date_of_birth=date(2014, 3, 3),
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def seed(session: Session) -> dict:
    """Two students, each with one guardian of their own (and their logins)."""
    for codename in _ROLES:
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="guardian api school", code="gas", email="gas@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    first = _student(session, "first child", "GAS-1")
    second = _student(session, "second child", "GAS-2")
    first_guardian = guardians.add_guardian(
        session,
        first.id,
        GuardianWrite(
            name="first parent",
            phone="9000000101",
            email="first.parent@test",
            relation="father",
        ),
    )
    second_guardian = guardians.add_guardian(
        session,
        second.id,
        GuardianWrite(name="other family", phone="9000000202", email="other@test"),
    )
    return {
        "first": first,
        "second": second,
        "first_guardian": first_guardian,
        "second_guardian": second_guardian,
    }


def _write(**overrides) -> GuardianWrite:
    values = {
        "name": "second parent",
        "phone": "9000000303",
        "email": "second.parent@test",
        "relation": "mother",
    }
    values.update(overrides)
    return GuardianWrite(**values)


def _refusal(session: Session, student_id, **overrides) -> HTTPException:
    try:
        guardians.add_guardian(session, student_id, _write(**overrides))
    except HTTPException as error:
        return error
    raise AssertionError("the guardian was added, but the contact is not free")


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_a_new_guardian_gets_a_person_and_a_login(session: Session) -> None:
    """A contact nobody uses creates the person, their login and the link."""
    data = seed(session)
    read = guardians.add_guardian(session, data["first"].id, _write())

    assert read.name == "second parent"
    assert read.relation == "mother"
    assert read.isPrimary is False, "the student already had a primary contact"
    assert read.loginEmail == "second.parent@test"
    assert read.password, "the first-time password is shown once, here"
    assert len(guardians.list_guardians(session, data["first"].id)) == 2


def check_a_siblings_parent_is_linked_not_duplicated(session: Session) -> None:
    """The same contact is the same person: one row, one login, both children."""
    data = seed(session)
    first = data["first_guardian"]

    # The second child's form carries the first child's parent contact.
    linked = guardians.add_guardian(
        session,
        data["second"].id,
        GuardianWrite(name="first parent", phone="9000000101", email="first.parent@test"),
    )

    assert linked.guardianId == first.guardianId
    assert linked.password is None, "the login already existed and is reused"
    assert linked.loginEmail == "first.parent@test"
    # Adding it again to the same child updates the link instead of duplicating it.
    again = guardians.add_guardian(
        session,
        data["second"].id,
        GuardianWrite(
            name="first parent",
            phone="9000000101",
            email="first.parent@test",
            relation="father",
        ),
    )
    assert again.guardianId == first.guardianId
    assert len(guardians.list_guardians(session, data["second"].id)) == 2


def check_another_familys_contact_is_refused(session: Session) -> None:
    """The card cannot file a new person under a number another family holds."""
    data = seed(session)
    refused = _refusal(session, data["first"].id, phone="9000000202")
    assert refused.status_code == 409
    assert "other family" in refused.detail


def check_editing_moves_the_person_everywhere(session: Session) -> None:
    """An edit follows the person: their row and their login together."""
    data = seed(session)
    first = data["first_guardian"]
    read = guardians.update_guardian(
        session,
        data["first"].id,
        first.guardianId,
        _write(
            name="first parent renamed",
            phone="9000000909",
            email="renamed@test",
        ),
    )
    assert read.name == "first parent renamed"
    assert read.phone == "9000000909"

    guardian = session.get(Guardian, first.guardianId)
    account = session.get(User, guardian.user_id)
    assert guardian.email == "renamed@test"
    assert account.email == "renamed@test", "the login moved with the guardian"


def check_removing_keeps_the_person_and_moves_primary(session: Session) -> None:
    """Removing a guardian unlinks this child only - and hands over `is_primary`."""
    data = seed(session)
    first = data["first_guardian"]
    added = guardians.add_guardian(session, data["first"].id, _write())

    # The primary contact leaves: the guardian left on file takes over.
    result = guardians.remove_guardian(
        session, data["first"].id, first.guardianId
    )
    assert result.removed is True
    assert result.primaryMovedTo == "second parent"

    remaining = guardians.list_guardians(session, data["first"].id)
    assert [item.guardianId for item in remaining] == [added.guardianId]
    assert remaining[0].isPrimary is True

    # The person survives: their row and their login are still there.
    assert session.get(Guardian, first.guardianId) is not None
    assert session.exec(
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.guardian_id == first.guardianId
        )
    ).first() is None
    assert session.get(User, session.get(Guardian, first.guardianId).user_id) is not None


# ---------------------------------------------------------------------------
# What pytest collects
# ---------------------------------------------------------------------------


def test_a_new_guardian_gets_a_person_and_a_login():
    with memory_session() as session:
        check_a_new_guardian_gets_a_person_and_a_login(session)


def test_a_siblings_parent_is_linked_not_duplicated():
    with memory_session() as session:
        check_a_siblings_parent_is_linked_not_duplicated(session)


def test_another_familys_contact_is_refused():
    with memory_session() as session:
        check_another_familys_contact_is_refused(session)


def test_editing_moves_the_person_everywhere():
    with memory_session() as session:
        check_editing_moves_the_person_everywhere(session)


def test_removing_keeps_the_person_and_moves_primary():
    with memory_session() as session:
        check_removing_keeps_the_person_and_moves_primary(session)


#: (label, scenario) - the list `scripts/_phase5_verify.py` walks.
SCENARIOS = (
    (
        "a new guardian gets a person and a login",
        check_a_new_guardian_gets_a_person_and_a_login,
    ),
    (
        "a sibling's parent is linked, not duplicated",
        check_a_siblings_parent_is_linked_not_duplicated,
    ),
    (
        "another family's contact is refused",
        check_another_familys_contact_is_refused,
    ),
    ("editing moves the person everywhere", check_editing_moves_the_person_everywhere),
    (
        "removing keeps the person and moves primary",
        check_removing_keeps_the_person_and_moves_primary,
    ),
)


