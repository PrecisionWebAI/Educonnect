"""The admission form obeys "one contact, one person" - the Phase-4 wiring.

The rule itself lives in `app/core/contacts.py`; this file checks that the **admission
write path** actually calls it, through the real service functions:

    1. saving a form under a guardian's number that belongs to another family is
       refused (`409`), and nothing half-written is left behind;
    2. a **sibling's** form reuses the guardian already on file - one guardian row, one
       login, one number, two links;
    3. there is **no draft** to park a half-filled form in, so a form that leaves the
       family's contact out is refused up front (`422`) and stores nothing;
    4. editing the guardian contact moves that person's login, guardian row **and** staff
       row together (`sync_contact`);
    5. the form's popup (`contact_lookup`) names the person and their children.

Like `test_contacts.py`, the scenarios are plain functions that build their own
throw-away SQLite schema, so they need no fixtures and no dev dependencies.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES as _MODEL_MODULES
from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.operations.admission import service as admissions
from app.domains.operations.admission.schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationUpdate,
)
from app.domains.auth.models import Role
from app.domains.admin.platform.models import School
from app.domains.people.staff.models import Employee
from app.domains.academic.classroom.students.models import Guardian, Student, StudentGuardianRelationship
from app.domains.admin.users.models import User

#: The role catalog rows the promotion grants (a real database seeds them).
_ROLES = ("student", "guardian", "teacher")


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

def seed(session: Session) -> dict:
    """A school, the class catalog, and **another** family already on file.

    `other` is the family whose number a second family must not borrow: a guardian
    with their own phone, address and login.
    """
    for codename in _ROLES:
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="admission contacts school", code="acs", email="acs@test")
    session.add(school)
    session.add(ClassName(classname="class 1", level=1, stage="primary"))
    session.add(Section(section_name="A"))
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    other_user = User(
        email="other.parent@test",
        full_name="other parent",
        hashed_password="x",
        is_active=True,
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)
    other = Guardian(
        name="other parent",
        phone="9000000202",
        email="other.parent@test",
        user_id=other_user.id,
    )
    session.add(other)
    session.commit()
    session.refresh(other)
    return {"school": school, "other": other, "other_user": other_user}


def form(**overrides) -> AdmissionApplicationCreate:
    """A form the office could send: complete, and therefore a student.

    There is no draft any more, so there is no half-filled variant to ask for: the
    helper describes a form that is ready to be admitted, and the one scenario that
    wants an incomplete one builds it explicitly.
    """
    values = {
        "student_first_name": "child",
        "student_last_name": "one",
        "date_of_birth": date(2015, 1, 1),
        "gender": "Male",
        "applied_for_class_level": "class 1",
        "applied_section_preference": "A",
        "guardian_name": "parent person",
        "guardian_relation": "father",
        "guardian_phone": "9000000101",
        "guardian_email": "parent@test",
    }
    values.update(overrides)
    return AdmissionApplicationCreate(**values)


def _refusal(session: Session, **kwargs) -> HTTPException:
    try:
        admissions.create_application(session, form(**kwargs))
    except HTTPException as error:
        return error
    raise AssertionError("the form was accepted, but the contact is not free")


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_registering_another_familys_number_is_refused(session: Session) -> None:
    """The second family cannot be filed under the first family's number."""
    seed(session)
    refused = _refusal(session, guardian_phone="9000000202")
    assert refused.status_code == 409
    assert "other parent" in refused.detail
    # Nothing half-written: a refused registration leaves **no** student row behind.
    assert session.exec(select(Student)).all() == []


def check_a_sibling_reuses_the_guardian_on_file(session: Session) -> None:
    """A family's second child shares one guardian row, one login and one number."""
    seed(session)
    first = admissions.create_application(session, form(student_first_name="anya"))
    assert first.credentials, "the first registration created the family's logins"

    second = admissions.create_application(
        session,
        form(student_first_name="arjun", student_email="arjun.own@test"),
    )

    guardians = session.exec(select(Guardian)).all()
    # The school's own `other` family plus **one** guardian for this family.
    assert len(guardians) == 2
    by_name = {guardian.name: guardian for guardian in guardians}
    parent = by_name["parent person"]
    assert parent.email == "parent@test"

    links = session.exec(
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.guardian_id == parent.id
        )
    ).all()
    assert len(links) == 2, "both children are linked to the same guardian"
    assert [link.is_primary for link in links] == [True, True]

    assert second.credentials is not None
    guardian_logins = [item for item in second.credentials if item.role == "guardian"]
    assert guardian_logins and guardian_logins[0].created is False, (
        "the guardian login was reused, not created again"
    )


def check_a_form_missing_the_family_is_refused(session: Session) -> None:
    """There is no draft to park a half-filled form in, so it is refused - and gone.

    What used to be "save it as a draft and warn about it later" is a `422` on the way
    in: nothing is written, so the directory can trust every row it lists. (A form with
    no phone number at all is refused even earlier, by the schema: the field is
    required, and `CanonicalRequest` turns a blank phone into `None`.)
    """
    seed(session)
    incomplete = AdmissionApplicationCreate(
        student_first_name="child",
        applied_for_class_level="class 1",
        guardian_name="",
        guardian_phone="9000000102",
        guardian_email="",
    )
    try:
        admissions.create_application(session, incomplete)
    except HTTPException as error:
        assert error.status_code == 422
        assert "the guardian's name" in error.detail
        assert "the guardian's email" in error.detail
    else:
        raise AssertionError("a form with no way to reach the family was accepted")
    # Nothing half-written: a refused form leaves **no** student row behind.
    assert session.exec(select(Student)).all() == []


def check_editing_the_contact_moves_the_whole_person(session: Session) -> None:
    """The guardian's login, guardian row and staff row follow one edit."""
    seed(session)
    registered = admissions.create_application(session, form())
    student = session.get(Student, registered.id)
    guardian = session.exec(
        select(Guardian).where(Guardian.name == "parent person")
    ).first()
    assert guardian is not None and guardian.user_id is not None

    # The same person also works here (a teacher whose child studies here).
    session.add(
        Employee(
            user_id=guardian.user_id,
            employee_code="EMP-ACS-1",
            department="science",
            joining_date=date(2021, 4, 1),
            email="parent@test",
            phone="9000000101",
        )
    )
    session.commit()

    update = AdmissionApplicationUpdate(
        **{
            **form().model_dump(),
            "guardian_email": "moved@test",
            "guardian_phone": "9000000303",
        }
    )
    admissions.update_application(session, student.id, update)

    session.refresh(guardian)
    user = session.get(User, guardian.user_id)
    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    assert guardian.email == "moved@test" and guardian.phone == "9000000303"
    assert user.email == "moved@test", "the login follows the guardian"
    assert employee.email == "moved@test" and employee.phone == "9000000303"


def check_the_popup_names_the_person_and_their_children(session: Session) -> None:
    """`contact_lookup` is what the form shows when the office tabs out."""
    seed(session)
    admissions.create_application(session, form())

    found = admissions.contact_lookup(session, phone="+91 90000 00101")
    assert found["found"] is True
    assert found["name"] == "parent person"
    assert found["guardianId"] is not None
    assert set(found["roles"]) >= {"guardian"}
    assert [child["name"] for child in found["children"]] == ["child one"]

    free = admissions.contact_lookup(session, phone="9777777777")
    assert free["found"] is False


# ---------------------------------------------------------------------------
# What pytest collects (each test builds its own in-memory database)
# ---------------------------------------------------------------------------


def test_registering_another_familys_number_is_refused():
    with memory_session() as session:
        check_registering_another_familys_number_is_refused(session)


def test_a_sibling_reuses_the_guardian_on_file():
    with memory_session() as session:
        check_a_sibling_reuses_the_guardian_on_file(session)


def test_a_form_missing_the_family_is_refused():
    with memory_session() as session:
        check_a_form_missing_the_family_is_refused(session)


def test_editing_the_contact_moves_the_whole_person():
    with memory_session() as session:
        check_editing_the_contact_moves_the_whole_person(session)


def test_the_popup_names_the_person_and_their_children():
    with memory_session() as session:
        check_the_popup_names_the_person_and_their_children(session)


#: (label, scenario) - the same list pytest covers, runnable without dev deps.
SCENARIOS = (
    (
        "registering under another family's number is refused",
        check_registering_another_familys_number_is_refused,
    ),
    (
        "a sibling reuses the guardian already on file",
        check_a_sibling_reuses_the_guardian_on_file,
    ),
    ("a form with no family contact is refused", check_a_form_missing_the_family_is_refused),
    (
        "editing the contact moves the whole person",
        check_editing_the_contact_moves_the_whole_person,
    ),
    (
        "contact_lookup names the person and their children",
        check_the_popup_names_the_person_and_their_children,
    ),
)


