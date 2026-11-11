"""Who a chat contact list may hold - the boundary in `chat/service.py`.

The rules these scenarios pin down:

    * leadership talks to anyone (`None` means "no boundary");
    * a teacher reaches the **children they teach** (the class-section they run, or
      one they take a subject in) and those children's guardians, plus their fellow
      teachers;
    * a guardian reaches the teachers of the class-section their own child sits in,
      and nobody else's;
    * a student reaches the teachers of the class-section they sit in;
    * a thread naming somebody outside that set is refused with `403`.

The shape is today's: a child has **one** placement (`student.classroom_id`, a
`classroom` row pointing at the class and the section catalog rows), a teacher's
work is `subjectteacher` (keyed by `classroom_id`) and `classroom.class_teacher_id`,
and a parent is a `Guardian` person linked through `student_guardian_relationship`.

Roles live in `user_role` now, and a request attaches them to the user object
(`auth.roles.attach_roles`) before anything asks `has_role(...)`; the scenarios
attach them the same way.

Plain functions with a `memory_session()` factory - like `test_contacts.py` - so
they run under pytest and from `__main__` without dev dependencies.
"""

from datetime import date

from fastapi import HTTPException
from sqlmodel import Session, select
from tests.test_contacts import memory_session  # noqa: F401  (the runner's factory)

from app.domains.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.auth.models import Role
from app.domains.auth.roles import attach_roles, set_user_roles
from app.domains.chat.schemas import ChatThreadCreate
from app.domains.chat.service import create_thread, get_authorized_contact_user_ids
from app.domains.schools.models import School
from app.domains.staff.models import Employee
from app.domains.students.models import Guardian, Student, StudentGuardianRelationship
from app.domains.users.models import User

#: The role catalog rows these scenarios need (a real database seeds them).
_ROLES = ("school_admin", "teacher", "guardian", "student")


def _school(session: Session) -> School:
    for codename in _ROLES:
        session.add(Role(codename=codename, label=codename.title()))
    school = School(name="chat test school", code="ch", email="ch@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    # Bind the session to the school the way a request does; every row written
    # from here belongs to it.
    session.info["school_id"] = school.id
    return school


def _login(session: Session, email: str, name: str, role: str) -> User:
    """One person with their role row, attached the way a request attaches it."""
    user = User(email=email, full_name=name, hashed_password="x", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    set_user_roles(session, user, [role])
    attach_roles(session, user)
    return user


def _build(session: Session) -> dict:
    """A small school: two class-sections, their staff, and two families."""
    _school(session)

    klass = ClassName(classname="Class 9", stage="secondary", level=9)
    letters = [Section(section_name="A"), Section(section_name="B")]
    session.add_all([klass, *letters])
    session.commit()

    room_a = Classroom(class_id=klass.class_id, section_id=letters[0].section_id)
    room_b = Classroom(class_id=klass.class_id, section_id=letters[1].section_id)
    session.add_all([room_a, room_b])
    session.commit()

    admin = _login(session, "admin@test.com", "Admin", "school_admin")
    math = _login(session, "math@test.com", "Math Teacher", "teacher")
    art = _login(session, "art@test.com", "Art Teacher", "teacher")
    child_a = _login(session, "child.a@test.com", "Child A", "student")
    child_b = _login(session, "child.b@test.com", "Child B", "student")
    parent_a = _login(session, "parent.a@test.com", "Parent A", "guardian")
    parent_b = _login(session, "parent.b@test.com", "Parent B", "guardian")

    math_employee = Employee(
        user_id=math.id,
        employee_code="EMP-0001",
        department="Math",
        qualification="B.Ed",
        joining_date=date(2020, 1, 1),
    )
    art_employee = Employee(
        user_id=art.id,
        employee_code="EMP-0002",
        department="Art",
        qualification="B.Ed",
        joining_date=date(2020, 1, 1),
    )
    session.add_all([math_employee, art_employee])
    session.commit()

    subject = Subject(name="Math", code="M1")
    session.add(subject)
    session.commit()

    # Math runs 9-A as its class teacher; Art only takes a subject in 9-B.
    room_a.class_teacher_id = math_employee.id
    session.add(room_a)
    session.add(
        SubjectTeacher(
            classroom_id=room_b.id, subject_id=subject.id, teacher_id=art_employee.id
        )
    )
    session.commit()

    # Child A sits in 9-A, Child B in 9-B; one guardian each.
    student_a = Student(
        user_id=child_a.id,
        full_name="Child A",
        admission_number="CH-1",
        date_of_birth=date(2012, 1, 1),
        classroom_id=room_a.id,
    )
    student_b = Student(
        user_id=child_b.id,
        full_name="Child B",
        admission_number="CH-2",
        date_of_birth=date(2012, 1, 1),
        classroom_id=room_b.id,
    )
    session.add_all([student_a, student_b])
    session.commit()

    guardian_a = Guardian(
        name="Parent A",
        phone="9000000001",
        email="parent.a@test.com",
        user_id=parent_a.id,
    )
    guardian_b = Guardian(
        name="Parent B",
        phone="9000000002",
        email="parent.b@test.com",
        user_id=parent_b.id,
    )
    session.add_all([guardian_a, guardian_b])
    session.commit()
    session.add_all(
        [
            StudentGuardianRelationship(
                student_id=student_a.id,
                guardian_id=guardian_a.id,
                relationship_type="mother",
                is_primary=True,
            ),
            StudentGuardianRelationship(
                student_id=student_b.id,
                guardian_id=guardian_b.id,
                relationship_type="father",
                is_primary=True,
            ),
        ]
    )
    session.commit()

    return {
        "admin": admin,
        "math": math,
        "art": art,
        "child_a": child_a,
        "child_b": child_b,
        "parent_a": parent_a,
        "parent_b": parent_b,
    }


def check_leadership_has_no_boundary(session: Session) -> None:
    """Leadership talks to anyone: the answer is `None`, not a long list."""
    people = _build(session)
    assert get_authorized_contact_user_ids(session, people["admin"]) is None


def check_a_teacher_reaches_their_own_class_section(session: Session) -> None:
    """The Math teacher runs 9-A, so 9-A's child and that child's guardian."""
    people = _build(session)
    allowed = get_authorized_contact_user_ids(session, people["math"])
    assert allowed is not None
    assert people["admin"].id in allowed  # leadership is always reachable
    assert people["art"].id in allowed  # teachers talk to teachers
    assert people["child_a"].id in allowed  # the class-section they run
    assert people["parent_a"].id in allowed  # and that child's guardian
    assert people["child_b"].id not in allowed  # another class-section's child
    assert people["parent_b"].id not in allowed


def check_a_guardian_reaches_their_childs_teachers(session: Session) -> None:
    people = _build(session)
    allowed = get_authorized_contact_user_ids(session, people["parent_a"])
    assert allowed is not None
    assert people["admin"].id in allowed
    assert people["math"].id in allowed  # runs 9-A, where their child sits
    assert people["art"].id not in allowed  # takes 9-B, not their child's class


def check_a_student_reaches_their_class_sections_teachers(session: Session) -> None:
    people = _build(session)
    allowed = get_authorized_contact_user_ids(session, people["child_b"])
    assert allowed is not None
    assert people["art"].id in allowed  # takes Math in 9-B
    assert people["math"].id not in allowed  # runs 9-A, not 9-B


def check_a_thread_outside_the_boundary_is_refused(session: Session) -> None:
    people = _build(session)
    try:
        create_thread(
            session,
            ChatThreadCreate(
                is_group=False, participant_user_ids=[people["parent_b"].id]
            ),
            people["math"].id,
        )
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("9-A's teacher must not be able to message 9-B's parent")

    # ...while the parent of the class-section they run is accepted.
    thread = create_thread(
        session,
        ChatThreadCreate(is_group=False, participant_user_ids=[people["parent_a"].id]),
        people["math"].id,
    )
    assert thread is not None


SCENARIOS = (
    ("chat: leadership talks to anyone", check_leadership_has_no_boundary),
    (
        "chat: a teacher reaches their own class-section's family",
        check_a_teacher_reaches_their_own_class_section,
    ),
    (
        "chat: a guardian reaches their child's teachers",
        check_a_guardian_reaches_their_childs_teachers,
    ),
    (
        "chat: a student reaches their class-section's teachers",
        check_a_student_reaches_their_class_sections_teachers,
    ),
    (
        "chat: a thread outside the boundary is refused",
        check_a_thread_outside_the_boundary_is_refused,
    ),
)
