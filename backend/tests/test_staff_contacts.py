"""The hire and interview forms - one contact, one person.

Scenarios (exactly what the Staff Hiring screens produce):

    1. hiring somebody the school does not have yet creates their login, puts them on
       the staff roll and hands back a first-time password once;
    2. hiring a **parent** who is already on file links the person: their existing login
       gains the staff role (no second login, no new password) and their guardian access
       stays - one login, one number, two roles;
    3. a number that belongs to another family is refused (`409`) when the hire is saved,
       naming who holds it;
    4. hiring an email that is already on the staff roll is refused (`422`) - the person
       is on the roll, their record is the one to open;
    5. the interview form follows the same rule: a contact that belongs to somebody else
       is refused (`409`), while the person themselves (a parent applying to teach, same
       name, their own number) is accepted and noted as already on file;
    6. `GET /hiring/contact-lookup` answers with who the contact belongs to, their roles
       and their children - the payload the form's popup shows.

Runs under pytest, and on its own without dev dependencies.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core import contacts
from app.core.schema import MODEL_MODULES as _MODEL_MODULES
from app.domains.auth.models import Role, UserRole
from app.domains.operations.staff_hiring import service as hiring_service
from app.domains.operations.staff_hiring.models import HiringCandidate
from app.domains.operations.staff_hiring.schemas import HiringCandidateCreate
from app.domains.admin.platform.models import School
from app.domains.people.staff import service as staff_service
from app.domains.people.staff.models import Employee
from app.domains.people.staff.schemas import StaffProfileCreate
from app.domains.academic.classroom.students import guardians
from app.domains.academic.classroom.students.models import Guardian, Student
from app.domains.academic.classroom.students.schemas import GuardianWrite
from app.domains.admin.users.models import User


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
    """Two families (each with their guardian) and the roles a hire can ask for."""
    for codename in ("student", "guardian", "teacher"):
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="hire contact school", code="hcs", email="hcs@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    child = _student(session, "hire child", "HCS-1")
    guardians.add_guardian(
        session,
        child.id,
        GuardianWrite(
            name="Pooja Verma",
            phone="9000000301",
            email="pooja.verma@test",
            relation="mother",
        ),
    )
    other = _student(session, "other child", "HCS-2")
    guardians.add_guardian(
        session,
        other.id,
        GuardianWrite(name="other family", phone="9000000302", email="other.family@test"),
    )
    return {"child": child, "other": other}


def _hire(**overrides) -> StaffProfileCreate:
    """The hire form, filled in the way the screen fills it."""
    fields = {
        "full_name": "New Teacher",
        "department": "Science",
        "role_codenames": ["teacher"],
        "contact_email": "new.teacher@test",
        "phone": "9000000401",
        "bank_name": "HDFC",
    }
    fields.update(overrides)
    return StaffProfileCreate(**fields)


def _candidate(**overrides) -> HiringCandidateCreate:
    """The interview form, filled in the way the screen fills it."""
    fields = {
        "candidate_name": "Interview Person",
        "department": "Science",
        "role": "Teacher",
        "applied_for": "teacher",
        "phone": "9000000501",
        "email": "interview.person@test",
    }
    fields.update(overrides)
    return HiringCandidateCreate(**fields)


def _roles_of(session: Session, user_id) -> set[str]:
    rows = session.exec(select(UserRole).where(UserRole.user_id == user_id)).all()
    codes = {row.role_codename for row in rows if getattr(row, "role_codename", None)}
    if codes:
        return codes
    roles = {role.id: role.codename for role in session.exec(select(Role)).all()}
    return {roles.get(row.role_id, "") for row in rows} - {""}


def _refusal(call):
    """Run `call` and return the `HTTPException` it raised.

    The API image has no pytest, so the scenarios assert refusals themselves instead of
    using `pytest.raises`.
    """
    try:
        call()
    except HTTPException as error:
        return error
    raise AssertionError("this was expected to be refused, but it went through")


# ---------------------------------------------------------------------------
# 1. a brand-new person: login + staff roll + password once
# ---------------------------------------------------------------------------


def scenario_new_hire():
    session = memory_session()
    seed(session)

    read = staff_service.create_profile(session, _hire())

    assert read.credentials is not None, "a new hire must be handed a first-time password"
    credential = read.credentials[0]
    assert credential.created is True
    assert credential.password, "the first-time password comes back once"
    assert credential.email == "new.teacher@test"

    user = session.exec(select(User).where(User.email == "new.teacher@test")).first()
    assert user is not None, "the hire creates the person's login"
    assert user.is_active is True
    assert _roles_of(session, user.id) == {"teacher"}

    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    assert employee is not None, "the hire writes the staff record"
    assert employee.email == "new.teacher@test"
    assert employee.phone == "9000000401"


# ---------------------------------------------------------------------------
# 2. the person is already here: one login, two roles
# ---------------------------------------------------------------------------


def scenario_hire_links_a_person_already_on_file():
    session = memory_session()
    seed(session)

    guardian = session.exec(
        select(Guardian).where(Guardian.email == "pooja.verma@test")
    ).first()
    assert guardian is not None
    person_id = guardian.user_id
    assert person_id is not None, "the family's guardian has their own login"

    read = staff_service.create_profile(
        session,
        _hire(
            full_name="Pooja Verma",
            contact_email="pooja.verma@test",
            phone="9000000301",
        ),
    )

    # The hire did not mint a second login: it added the staff role to the one they have.
    logins = session.exec(select(User).where(User.email == "pooja.verma@test")).all()
    assert len(logins) == 1, "one person, one login"
    assert logins[0].id == person_id
    assert read.credentials is not None and read.credentials[0].created is False
    assert read.credentials[0].password is None, "their password is not reset by a hire"

    roles = _roles_of(session, person_id)
    assert "teacher" in roles, "the staff role is added"
    assert "guardian" in roles, "their guardian access stays"

    employee = session.exec(select(Employee).where(Employee.user_id == person_id)).first()
    assert employee is not None, "the hire writes their staff record"
    assert employee.phone == "9000000301"
    # One person, one contact: the guardian row and the staff row agree.
    assert guardian.user_id == person_id


# ---------------------------------------------------------------------------
# 3. somebody else's number is refused
# ---------------------------------------------------------------------------


def scenario_hire_refuses_somebody_elses_contact():
    session = memory_session()
    seed(session)

    refusal = _refusal(
        lambda: staff_service.create_profile(
            session,
            _hire(
                full_name="Stranger",
                contact_email="stranger@test",
                phone="9000000302",  # the other family's number
            ),
        )
    )
    assert refusal.status_code == 409, refusal.detail
    assert "other family" in refusal.detail
    assert session.exec(select(User).where(User.email == "stranger@test")).first() is None


# ---------------------------------------------------------------------------
# 4. already on the staff roll
# ---------------------------------------------------------------------------


def scenario_hire_refuses_a_second_staff_record():
    session = memory_session()
    seed(session)
    staff_service.create_profile(session, _hire())

    refusal = _refusal(
        lambda: staff_service.create_profile(session, _hire(full_name="New Teacher Again"))
    )
    assert refusal.status_code == 422, refusal.detail
    assert "staff roll" in refusal.detail
    employees = session.exec(
        select(Employee).where(Employee.email == "new.teacher@test")
    ).all()
    assert len(employees) == 1, "no second staff record for the same login"


# ---------------------------------------------------------------------------
# 5. the interview form follows the same rule
# ---------------------------------------------------------------------------


def scenario_interview_form():
    session = memory_session()
    seed(session)

    # somebody new: accepted
    fresh = hiring_service.create_candidate(session, _candidate())
    # Names are stored canonicalised (lower case), like every other form's.
    assert fresh.candidate_name == "interview person"
    assert not (fresh.interview_note or ""), "nothing to note about a fresh contact"

    # somebody else's number: refused, naming the holder
    refusal = _refusal(
        lambda: hiring_service.create_candidate(
            session, _candidate(candidate_name="Walk In", phone="9000000302")
        )
    )
    assert refusal.status_code == 409, refusal.detail
    assert "other family" in refusal.detail

    # the person themselves: a parent applying to teach keeps their own contact
    same = hiring_service.create_candidate(
        session,
        _candidate(
            candidate_name="pooja verma",
            phone="9000000301",
            email="pooja.verma@test",
        ),
    )
    assert "already on file" in (same.interview_note or ""), same.interview_note
    assert len(session.exec(select(HiringCandidate)).all()) == 2, "the walk-in was not written"


# ---------------------------------------------------------------------------
# 6. the popup payload
# ---------------------------------------------------------------------------


def scenario_contact_lookup_payload():
    session = memory_session()
    seed(session)

    found = contacts.contact_read(session=session, phone="9000000301")
    assert found["found"] is True
    # Names are stored canonicalised (lower case): the popup shows what is on file.
    assert found["name"] == "pooja verma"
    assert "guardian" in found["roles"]
    assert found["guardianId"], "the popup can link the person it found"
    assert len(found["children"]) == 1
    assert found["children"][0]["name"] == "hire child"
    assert "hire child" in found["message"]

    # An email lands on the same person through their login - and still shows the child.
    by_email = contacts.contact_read(session=session, email="pooja.verma@test")
    assert by_email["found"] is True
    assert by_email["guardianId"], "one contact, one person: the family side comes too"
    assert len(by_email["children"]) == 1

    empty = contacts.contact_read(session=session, phone="9999999999")
    assert empty["found"] is False


SCENARIOS = (
    ("a new hire gets a login and a staff record", scenario_new_hire),
    ("hiring a parent links their existing login", scenario_hire_links_a_person_already_on_file),
    ("another family's number is refused", scenario_hire_refuses_somebody_elses_contact),
    ("an email already on the staff roll is refused", scenario_hire_refuses_a_second_staff_record),
    ("the interview form follows the contact rule", scenario_interview_form),
    ("the contact lookup answers with person, roles and children", scenario_contact_lookup_payload),
)


def run_all() -> int:
    """Plain-function runner (the API image has no pytest)."""
    failures = 0
    for label, scenario in SCENARIOS:
        try:
            scenario()
        except Exception as error:  # noqa: BLE001 - the runner reports, it does not raise
            failures += 1
            print(f"FAIL  {label}: {type(error).__name__}: {error}")
        else:
            print(f"ok    {label}")
    print(f"{len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run_all())


# --- pytest wrappers (each scenario above is one test) -----------------------


def test_new_hire():
    scenario_new_hire()


def test_hire_links_a_person_already_on_file():
    scenario_hire_links_a_person_already_on_file()


def test_hire_refuses_somebody_elses_contact():
    scenario_hire_refuses_somebody_elses_contact()


def test_hire_refuses_a_second_staff_record():
    scenario_hire_refuses_a_second_staff_record()


def test_interview_form():
    scenario_interview_form()


def test_contact_lookup_payload():
    scenario_contact_lookup_payload()


