"""Phase 1 - the Students tab writes to the database.

The audit found the directory's add/edit/status buttons only changed the React Query
cache: reload the page and the child was gone. These scenarios pin the replacement:

1. **create** mints the admission number, writes `student.classroom_id` **and** the
   session's `enrollment` row - through the one placement writer;
2. **edit** writes the fields it was sent (and only those) and reports the new class;
3. **move** updates the *same* enrollment row for the year - never a second one, so
   the roll cannot double-count a child;
4. **deactivate → reactivate** stamps the roll dates *and* the year's history;
5. **search/scope/count** run in SQL (the browser no longer filters a capped hundred);
6. **another school** is a `404`, never a `403` - the API must not confirm the id;
7. **a teacher** (who holds `students.read` only) is refused by the route guard.

Runs under pytest and as `python tests/test_classroom_students.py`.
"""

import importlib
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.students import guardians, lifecycle, service
from app.domains.academic.classroom.students.models import Enrollment, Guardian, Student
from app.domains.academic.classroom.students.schemas import (
    GuardianWrite,
    StudentCreate,
    StudentUpdate,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission


def memory_session() -> Session:
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, name: str, code: str) -> School:
    school = School(name=name, code=code, email=f"{code}@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


def _bind(session: Session, school: School) -> None:
    """Point this session at a school - what a signed-in request does."""
    session.info["school_id"] = school.id


def _rooms(session: Session, count: int = 2) -> list:
    """`count` class-sections (Class 6-A, 6-B, ...) that students can be placed in."""
    klass = session.exec(
        select(ClassName).where(ClassName.classname == "Class 6")
    ).first()
    if klass is None:
        klass = ClassName(classname="Class 6", level=6)
        session.add(klass)
        session.commit()
        session.refresh(klass)

    rooms = []
    for letter in "ABCDEFGHIJ"[:count]:
        section = session.exec(
            select(Section).where(Section.section_name == letter)
        ).first()
        if section is None:
            section = Section(section_name=letter)
            session.add(section)
            session.commit()
            session.refresh(section)
        rooms.append(ensure_room(session, klass.class_id, section.section_id))
    return rooms


def _student(
    session: Session, name: str, number: str, room=None, gender: str = "Female"
) -> Student:
    payload = StudentCreate(
        full_name=name,
        gender=gender,
        admission_number=number,
        classroom_id=room.id if room is not None else None,
    )
    return service.create_student(session, payload)


def seed(session: Session) -> dict:
    """One school, two class-sections and three children (one of them in 6-B)."""
    school = _school(session, "phase one school", "p1s")
    _bind(session, school)
    first, second = _rooms(session, 2)

    aarav = _student(session, "aarav sharma", "P1-1", first)
    diya = _student(session, "diya patel", "P1-2", first)
    kabir = _student(session, "kabir singh", "P1-3", second, gender="Male")
    guardians.add_guardian(
        session,
        kabir.id,
        GuardianWrite(name="meera singh", phone="9000000111", relation="mother"),
    )
    return {
        "school": school,
        "first": first,
        "second": second,
        "aarav": aarav,
        "diya": diya,
        "kabir": kabir,
    }


def _enrollments(session: Session, student: Student) -> list[Enrollment]:
    return list(
        session.exec(
            select(Enrollment).where(Enrollment.student_id == student.id)
        ).all()
    )


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_create_places_the_child_and_opens_the_session(session: Session) -> None:
    """A new student is in a class *and* in this year's history from the first save."""
    data = seed(session)
    aarav = data["aarav"]

    assert aarav.classroom_id == data["first"].id
    rows = _enrollments(session, aarav)
    assert len(rows) == 1, "one placement per student per session"
    enrollment = rows[0]
    assert enrollment.classroom_id == data["first"].id
    assert enrollment.status == "active"
    assert enrollment.joined_on == date.today()

    year = session.exec(select(AcademicYear)).all()
    assert len(year) == 1, "the session row is opened once, not per student"
    assert year[0].is_current is True


def check_edit_writes_only_what_it_was_sent(session: Session) -> None:
    """The modal's save changes the fields it carries and leaves the rest alone."""
    data = seed(session)
    aarav = data["aarav"]

    read = service.update_student(
        session,
        aarav.id,
        StudentUpdate(full_name="  aarav k sharma  ", gender="Male"),
    )

    assert read.name == "aarav k sharma", "the display name is trimmed"
    assert read.gender.lower() == "male"
    assert (read.className, read.section) == ("Class 6", "A")
    assert read.admissionNo == "P1-1", "an untouched admission number stays"

    stored = session.get(Student, aarav.id)
    assert stored.full_name == "aarav k sharma"
    assert stored.date_of_birth is None, "a field the request never sent is untouched"


def check_move_updates_the_same_enrollment_row(session: Session) -> None:
    """A transfer inside one session is an update - the roll cannot double-count."""
    data = seed(session)
    kabir = data["kabir"]

    read = service.update_student(
        session, kabir.id, StudentUpdate(classroom_id=data["first"].id)
    )

    assert read.section == "A", "the read reports the new class-section"
    rows = _enrollments(session, kabir)
    assert len(rows) == 1, "still one row for the year"
    assert rows[0].classroom_id == data["first"].id
    assert rows[0].status == "active"


def check_leaving_and_returning_follow_the_roll(session: Session) -> None:
    """Deactivate/reactivate stamp the roll dates *and* the year's history."""
    data = seed(session)
    diya = data["diya"]

    lifecycle.deactivate_student(session, diya.id)
    stored = session.get(Student, diya.id)
    assert stored.deactivated_at is not None and stored.left_on == date.today()
    assert _enrollments(session, diya)[0].status == "left"
    assert service.get_student(session, diya.id).status == "Inactive"

    lifecycle.reactivate_student(session, diya.id)
    stored = session.get(Student, diya.id)
    assert stored.deactivated_at is None and stored.left_on is None
    enrollment = _enrollments(session, diya)[0]
    assert enrollment.status == "active" and enrollment.left_on is None
    assert service.get_student(session, diya.id).status == "Active"


def check_search_scope_and_count_run_in_sql(session: Session) -> None:
    """Name, admission number and guardian name all match - and the count agrees."""
    data = seed(session)

    by_name = service.get_students(session, q="AARAV")
    assert [row.name for row in by_name] == ["aarav sharma"], "search is case-blind"

    by_admission = service.get_students(session, q="P1-3")
    assert [row.admissionNo for row in by_admission] == ["P1-3"]

    by_guardian = service.get_students(session, q="meera")
    assert [row.name for row in by_guardian] == ["kabir singh"], (
        "a parent's name finds their child"
    )

    assert service.count_students(session) == 3
    assert service.count_students(session, q="aarav") == 1

    one_room = service.get_students(session, classroom_id=data["first"].id)
    assert {row.section for row in one_room} == {"A"}
    assert service.count_students(session, classroom_id=data["first"].id) == 2

    page = service.get_students(session, skip=1, limit=1)
    assert len(page) == 1, (
        "the server pages; the browser no longer slices a capped list"
    )

    # The two directory dropdowns are server filters too, so a page of 25 and the
    # "Active" chip still describe the whole roll, not one page of it.
    klass = session.exec(select(ClassName)).first()
    assert len(service.get_students(session, class_id=klass.class_id)) == 3
    lifecycle.deactivate_student(session, data["diya"].id)
    assert [r.name for r in service.get_students(session, status="Inactive")] == [
        "diya patel"
    ]
    assert service.count_students(session, status="Active") == 2


def check_another_school_is_a_404(session: Session) -> None:
    """A child of school B is invisible (404) to school A - never "forbidden"."""
    other = _school(session, "other school", "p1o")
    _bind(session, other)
    their_room = _rooms(session, 1)[0]
    theirs = _student(session, "their child", "P1O-1", their_room)

    ours = _school(session, "our school", "p1u")
    _bind(session, ours)

    calls = (
        lambda: service.get_student(session, theirs.id),
        lambda: service.update_student(
            session, theirs.id, StudentUpdate(full_name="x")
        ),
        lambda: lifecycle.deactivate_student(session, theirs.id),
    )
    for call in calls:
        try:
            call()
        except HTTPException as error:
            assert error.status_code == 404
        else:  # pragma: no cover - the assertion is the point
            raise AssertionError("another school's student was reachable")


def check_a_teacher_cannot_edit(session: Session) -> None:
    """The route guard is the permission, not the screen: a teacher is refused."""
    teacher = User(email="t@test", full_name="Teacher", hashed_password="pw")
    teacher._role_names = {"teacher"}
    admin = User(email="a@test", full_name="Admin", hashed_password="pw")
    admin._role_names = {"school_admin"}
    request = SimpleNamespace(path_params={}, query_params={})

    guard = RequirePermission("students.update")
    with pytest.raises(HTTPException) as refused:
        guard(request=request, user=teacher, session=None)
    assert refused.value.status_code == 403
    assert guard(request=request, user=admin, session=None) is admin


def check_a_family_sees_only_its_own_child(session: Session) -> None:
    """A parent's and a student's read is narrowed **in SQL**, not by the browser."""
    data = seed(session)

    parent = User(email="meera@test", full_name="Meera", hashed_password="pw")
    session.add(parent)
    session.commit()
    session.refresh(parent)
    parent._role_names = {"guardian"}
    guardian = session.exec(
        select(Guardian).where(Guardian.name == "meera singh")
    ).first()
    guardian.user_id = parent.id
    session.add(guardian)
    session.commit()

    seen = service.get_students(session, user=parent)
    assert [row.name for row in seen] == ["kabir singh"]
    assert service.count_students(session, user=parent) == 1

    try:
        service.get_student(session, data["aarav"].id, user=parent)
    except HTTPException as error:
        assert error.status_code == 404, "another child is a 404, not a 403"
    else:  # pragma: no cover - the assertion is the point
        raise AssertionError("a parent could read a classmate's record")

    child_login = User(email="kabir@test", full_name="Kabir", hashed_password="pw")
    session.add(child_login)
    session.commit()
    session.refresh(child_login)
    child_login._role_names = {"student"}
    kabir = session.get(Student, data["kabir"].id)
    kabir.user_id = child_login.id
    session.add(kabir)
    session.commit()
    assert [row.name for row in service.get_students(session, user=child_login)] == [
        "kabir singh"
    ]

    office = User(email="office@test", full_name="Office", hashed_password="pw")
    office._role_names = {"school_admin"}
    assert len(service.get_students(session, user=office)) == 3, (
        "the office is not scoped"
    )


# ---------------------------------------------------------------------------
# pytest wrappers + the no-pytest runner
# ---------------------------------------------------------------------------


def test_create_places_the_child_and_opens_the_session():
    with memory_session() as session:
        check_create_places_the_child_and_opens_the_session(session)


def test_edit_writes_only_what_it_was_sent():
    with memory_session() as session:
        check_edit_writes_only_what_it_was_sent(session)


def test_move_updates_the_same_enrollment_row():
    with memory_session() as session:
        check_move_updates_the_same_enrollment_row(session)


def test_leaving_and_returning_follow_the_roll():
    with memory_session() as session:
        check_leaving_and_returning_follow_the_roll(session)


def test_search_scope_and_count_run_in_sql():
    with memory_session() as session:
        check_search_scope_and_count_run_in_sql(session)


def test_another_school_is_a_404():
    with memory_session() as session:
        check_another_school_is_a_404(session)


def test_a_teacher_cannot_edit():
    with memory_session() as session:
        check_a_teacher_cannot_edit(session)


def test_a_family_sees_only_its_own_child():
    with memory_session() as session:
        check_a_family_sees_only_its_own_child(session)


SCENARIOS = (
    (
        "create places the child and opens the session",
        check_create_places_the_child_and_opens_the_session,
    ),
    ("edit writes only what it was sent", check_edit_writes_only_what_it_was_sent),
    (
        "a move updates the same enrollment row",
        check_move_updates_the_same_enrollment_row,
    ),
    (
        "leaving and returning follow the roll",
        check_leaving_and_returning_follow_the_roll,
    ),
    ("search, scope and count run in SQL", check_search_scope_and_count_run_in_sql),
    ("another school is a 404", check_another_school_is_a_404),
    ("a teacher cannot edit", check_a_teacher_cannot_edit),
    ("a family sees only its own child", check_a_family_sees_only_its_own_child),
)


if __name__ == "__main__":  # pragma: no cover - the no-pytest runner
    for label, scenario in SCENARIOS:
        with memory_session() as run_session:
            scenario(run_session)
        print(f"ok  {label}")
