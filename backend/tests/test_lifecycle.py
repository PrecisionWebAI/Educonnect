"""Leaving the school - deactivate, reactivate, and what a delete is allowed to take.

Scenarios (the buttons on the Students directory and the Staff Hiring screen):

    1. a teacher with nothing else is deactivated: their `teacher` role comes off and is
       remembered, the day they left is stamped, and their login is switched off - it
       opened nothing else. Reactivating restores exactly that role and the login;
    2. a teacher who is **also a parent** is deactivated: the `teacher` role goes, the
       `guardian` role stays and the login is **left alone** - they still sign in as the
       child's parent. Staff access is gone at once, because roles are read per request;
    3. deactivating somebody already deactivated (or reactivating somebody already on the
       roll) is refused with `409` - the screen is told the state it is actually in;
    4. a student leaving the roll: `left_on` + `deactivated_at` are stamped, the directory
       reads `Inactive`, and **no login is switched off**; reactivating clears it;
    5. deleting a member of staff who is still somebody else here keeps their login (the
       roles that are not the school's stay); deleting one whose login opened nothing
       takes the login with them;
    6. deleting a student follows the same login rule: a parent who also studied here
       still signs in, a student with no other role loses the account.

Runs under pytest, and on its own without dev dependencies.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.lifecycle import LifecycleRequest
from app.core.schema import MODEL_MODULES as _MODEL_MODULES
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role, role_codenames
from app.domains.admin.platform.models import School
from app.domains.people.staff import lifecycle as staff_lifecycle
from app.domains.people.staff import service as staff_service
from app.domains.people.staff.models import Employee
from app.domains.people.staff.schemas import StaffProfileCreate
from app.domains.academic.classroom.students import guardians
from app.domains.academic.classroom.students import lifecycle as student_lifecycle
from app.domains.academic.classroom.students import service as student_service
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


def seed(session: Session) -> dict:
    """One school and the roles both sides of the product hand out."""
    for codename in ("student", "guardian", "teacher"):
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="lifecycle school", code="lcs", email="lcs@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return {"school": school}


def _hire(**overrides) -> StaffProfileCreate:
    """The hire form, filled in the way the screen fills it."""
    fields = {
        "full_name": "Hired Person",
        "department": "Science",
        "role_codenames": ["teacher"],
        "contact_email": "hired.person@test",
        "phone": "9000000701",
        "bank_name": "HDFC",
    }
    fields.update(overrides)
    return StaffProfileCreate(**fields)


def _employee(session: Session) -> Employee:
    profile = session.exec(select(Employee)).first()
    assert profile is not None, "the hire should have written an employee row"
    return profile


def _student(session: Session, name: str, number: str, user: User | None = None) -> Student:
    """A student row with an admission number - the guardian is a row of its own."""
    student = Student(
        student_first_name=name,
        full_name=name,
        admission_number=number,
        date_of_birth=date(2014, 3, 3),
        user_id=user.id if user is not None else None,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def _login(session: Session, email: str, codename: str) -> User:
    """A login holding one role (a new person the product would have created)."""
    from app.domains.auth.roles import set_user_roles

    user = User(email=email, full_name=email.split("@")[0], hashed_password="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    set_user_roles(session, user, [codename])
    return user


def _roles(session: Session, user_id) -> set[str]:
    """The roles an account holds, read through the app's own reader."""
    return set(role_codenames(session, user_id))


def _refusal(call) -> HTTPException:
    """Run `call` and return the `HTTPException` it raised (no pytest in the API image)."""
    try:
        call()
    except HTTPException as error:
        return error
    raise AssertionError("this was expected to be refused, but it went through")


# ---------------------------------------------------------------------------
# 1. a teacher with nothing else
# ---------------------------------------------------------------------------


def scenario_teacher_only():
    session = memory_session()
    seed(session)
    staff_service.create_profile(session, _hire())
    profile = _employee(session)
    user_id = profile.user_id

    read = staff_lifecycle.deactivate_profile(
        session, profile.id, LifecycleRequest(reason="resigned")
    )
    assert read.action == "deactivated"
    assert read.rolesWithdrawn == ["teacher"]
    assert read.rolesKept == []
    assert read.loginKept is False, "it opened nothing else, so it is switched off"
    assert read.loginActive is False
    assert "switched off" in read.message
    assert read.reason == "resigned"

    # The account: no roles, not active. The record: still there, stamped.
    assert _roles(session, user_id) == set()
    assert session.get(User, user_id).is_active is False
    session.refresh(profile)
    assert profile.deactivated_at is not None
    assert profile.left_on == date.today()
    assert profile.deactivated_roles == "teacher"
    assert session.get(Employee, profile.id) is not None, "nothing is deleted"

    # The screen says what happened: the Hired tab's read carries the lifecycle.
    from app.domains.people.staff.service import list_profiles

    listed = [row for row in list_profiles(session) if row.id == profile.id][0]
    assert listed.isActive is False
    assert listed.loginActive is False
    assert listed.deactivatedRoles == ["teacher"]
    assert listed.leftOn == date.today().isoformat()

    back = staff_lifecycle.reactivate_profile(session, profile.id)
    assert back.action == "reactivated"
    assert back.rolesRestored == ["teacher"]
    assert _roles(session, user_id) == {"teacher"}
    assert session.get(User, user_id).is_active is True
    assert role_codenames(session, user_id)[0] == "teacher", "it is the primary role again"
    session.refresh(profile)
    assert profile.deactivated_at is None
    assert profile.left_on is None
    assert profile.deactivated_roles is None


# ---------------------------------------------------------------------------
# 2. a teacher who is also a parent
# ---------------------------------------------------------------------------


def scenario_parent_teacher_keeps_the_login():
    session = memory_session()
    seed(session)

    child = _student(session, "parent teacher child", "LCS-1")
    guardians.add_guardian(
        session,
        child.id,
        GuardianWrite(
            name="Rekha Nair", phone="9000000801", email="rekha.nair@test", relation="mother"
        ),
    )
    # The same person is hired - the hire links the login they already sign in with.
    staff_service.create_profile(
        session,
        _hire(
            full_name="Rekha Nair",
            contact_email="rekha.nair@test",
            phone="9000000801",
        ),
    )
    profile = _employee(session)
    user_id = profile.user_id
    assert _roles(session, user_id) == {"guardian", "teacher"}

    read = staff_lifecycle.deactivate_profile(session, profile.id)
    assert read.rolesWithdrawn == ["teacher"]
    assert read.rolesKept == ["guardian"]
    assert read.loginKept is True, "they are still this child's parent"
    assert read.loginActive is True
    assert "keep signing in" in read.message

    # Staff access is gone the moment the roles change (they are read per request)...
    assert _roles(session, user_id) == {"guardian"}
    # ...and the login is untouched: it still opens the parent side.
    user = session.get(User, user_id)
    assert user.is_active is True
    assert role_codenames(session, user_id)[0] == "guardian", "the parent hat is now primary"

    back = staff_lifecycle.reactivate_profile(session, profile.id)
    assert back.rolesRestored == ["teacher"]
    assert _roles(session, user_id) == {"guardian", "teacher"}
    assert back.rolesKept == ["guardian"]


# ---------------------------------------------------------------------------
# 3. the same button twice
# ---------------------------------------------------------------------------


def scenario_refuses_repeating_the_action():
    session = memory_session()
    seed(session)
    staff_service.create_profile(session, _hire())
    profile = _employee(session)

    staff_lifecycle.deactivate_profile(session, profile.id)
    again = _refusal(lambda: staff_lifecycle.deactivate_profile(session, profile.id))
    assert again.status_code == 409, again.detail
    assert "already off" in again.detail

    staff_lifecycle.reactivate_profile(session, profile.id)
    twice = _refusal(lambda: staff_lifecycle.reactivate_profile(session, profile.id))
    assert twice.status_code == 409, twice.detail
    assert "already on" in twice.detail


# ---------------------------------------------------------------------------
# 4. a student leaves the roll
# ---------------------------------------------------------------------------


def scenario_student_left_the_roll():
    session = memory_session()
    seed(session)
    user = _login(session, "student.one@test", "student")
    student = _student(session, "leaving child", "LCS-2", user)

    read = student_lifecycle.deactivate_student(
        session,
        student.id,
        LifecycleRequest(left_on=date(2026, 3, 31), reason="moved away"),
    )
    assert read.action == "deactivated"
    assert read.leftOn == "2026-03-31", "the day the office says they left"
    assert read.rolesWithdrawn == []
    assert read.rolesKept == ["student"]
    assert read.loginKept is True and read.loginActive is True
    assert "untouched" in read.message

    directory = student_service.get_student(session, student.id)
    assert directory.status == "Inactive"
    assert directory.leftOn == "2026-03-31"
    assert directory.deactivatedAt is not None

    # The rule: a student's login is never switched off.
    assert session.get(User, user.id).is_active is True
    assert _roles(session, user.id) == {"student"}
    session.refresh(student)
    # The row is the student's own record, and leaving the roll changes the two
    # lifecycle columns and nothing else: there is no workflow status left to flip,
    # and the number and login they came in with stay theirs.
    assert student.admission_number == "LCS-2"
    assert student.user_id == user.id

    back = student_lifecycle.reactivate_student(session, student.id)
    assert back.action == "reactivated"
    directory = student_service.get_student(session, student.id)
    assert directory.status == "Active"
    assert directory.leftOn is None and directory.deactivatedAt is None

    twice = _refusal(lambda: student_lifecycle.reactivate_student(session, student.id))
    assert twice.status_code == 409, twice.detail
    assert "already on the roll" in twice.detail


# ---------------------------------------------------------------------------
# 5. deleting a member of staff
# ---------------------------------------------------------------------------


def scenario_delete_staff_takes_only_their_own_rows():
    session = memory_session()
    seed(session)

    # (a) a teacher who is also a parent: the staff row goes, the login stays
    child = _student(session, "staff parent child", "LCS-3")
    guardians.add_guardian(
        session,
        child.id,
        GuardianWrite(
            name="Vikram Rao", phone="9000000901", email="vikram.rao@test", relation="father"
        ),
    )
    staff_service.create_profile(
        session,
        _hire(
            full_name="Vikram Rao",
            contact_email="vikram.rao@test",
            phone="9000000901",
        ),
    )
    parent_teacher = _employee(session)
    parent_teacher_id = parent_teacher.id
    parent_user_id = parent_teacher.user_id

    staff_lifecycle.delete_profile(session, parent_teacher_id)
    assert session.get(Employee, parent_teacher_id) is None
    assert session.get(User, parent_user_id) is not None, "the parent still signs in"
    assert _roles(session, parent_user_id) == {"guardian"}
    guardian = session.exec(
        select(Guardian).where(Guardian.email == "vikram.rao@test")
    ).first()
    assert guardian is not None, "the family's own row is untouched"

    # (b) a teacher whose login opened nothing else: it goes with them
    staff_service.create_profile(
        session,
        _hire(
            full_name="Alone Teacher",
            contact_email="alone.teacher@test",
            phone="9000000902",
        ),
    )
    alone = session.exec(
        select(Employee).where(Employee.email == "alone.teacher@test")
    ).first()
    assert alone is not None
    alone_user_id = alone.user_id
    staff_lifecycle.delete_profile(session, alone.id)
    assert session.get(User, alone_user_id) is None, "their last role went with them"


# ---------------------------------------------------------------------------
# 6. the same rule when a student is deleted
# ---------------------------------------------------------------------------


def scenario_delete_student_keeps_the_login_that_opens_something_else():
    session = memory_session()
    seed(session)

    # A login that is a parent's **and** a student's: it keeps opening the parent side.
    both = _login(session, "adult.learner@test", "guardian")
    grant_role(session, both, "student")
    assert _roles(session, both.id) == {"guardian", "student"}
    child = _student(session, "adult learner", "LCS-4", both)

    result = student_service.delete_student(session, child.id)
    assert result["loginRemoved"] is False
    assert session.get(User, both.id) is not None
    assert _roles(session, both.id) == {"guardian"}

    # A student with no other role: their account goes with the row.
    only = _login(session, "only.student@test", "student")
    plain_child = _student(session, "plain student", "LCS-5", only)
    plain = student_service.delete_student(session, plain_child.id)
    assert plain["loginRemoved"] is True
    assert session.get(User, only.id) is None


SCENARIOS = (
    ("a teacher with nothing else is deactivated and reactivated", scenario_teacher_only),
    ("a teacher-parent keeps their login", scenario_parent_teacher_keeps_the_login),
    ("the same button twice is refused", scenario_refuses_repeating_the_action),
    ("a student leaves the roll without losing their login", scenario_student_left_the_roll),
    (
        "deleting staff takes only their own rows",
        scenario_delete_staff_takes_only_their_own_rows,
    ),
    (
        "deleting a student keeps a login that opens something else",
        scenario_delete_student_keeps_the_login_that_opens_something_else,
    ),
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


def test_teacher_only():
    scenario_teacher_only()


def test_parent_teacher_keeps_the_login():
    scenario_parent_teacher_keeps_the_login()


def test_refuses_repeating_the_action():
    scenario_refuses_repeating_the_action()


def test_student_left_the_roll():
    scenario_student_left_the_roll()


def test_delete_staff_takes_only_their_own_rows():
    scenario_delete_staff_takes_only_their_own_rows()


def test_delete_student_keeps_the_login_that_opens_something_else():
    scenario_delete_student_keeps_the_login_that_opens_something_else()


