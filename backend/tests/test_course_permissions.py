"""Phase 2 - the Course guards: who may read, plan, assign and approve.

These are the rules the API will enforce on every Course endpoint, tested against the
same role/permission rows a request reads:

1. **the office holds the office's rights** - principal (and therefore everyone above)
   may manage, assign, approve and see every teacher; an accountant holds none of them;
2. **a teacher owns only their subject** - the open assignment is the claim; another
   teacher of the same section is refused, and the office is allowed;
3. **a teacher change moves the claim** - closing the old row and opening the new one
   makes the new teacher the owner and leaves the old one as history;
4. **another school sees nothing** - the tenant filter turns the other school's subject
   into a non-existent row (the API's 404, never a 403 that confirms the id);
5. **the visible subjects are filtered, not hidden in the browser** - a teacher gets a
   set of their own rows, the office gets `None` ("all"), a non-academic role gets `{}`;
6. **a teacher reads their own course only**, while the office reads anybody's.

Runs under pytest and as `python tests/test_course_permissions.py`.
"""

import importlib
from datetime import date
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import scope
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.permissions_repository import seed_permissions
from app.domains.auth.roles import attach_roles
from app.domains.people.staff.models import Employee


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
    school = School(name=name, code=code, email=f"office@{code.lower()}.test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


def _person(
    session: Session, *, email: str, code: str, role: str
) -> tuple[User, Employee]:
    """A login, its employee row and one role - attached the way a request attaches it."""
    user = User(
        email=f"{uuid4().hex[:10]}-{email}",
        full_name=email.split("@")[0],
        hashed_password="x",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2024, 6, 1),
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)

    role_row = session.exec(select(Role).where(Role.codename == role)).first()
    assert role_row is not None, f"role {role} was not seeded"
    session.add(UserRole(user_id=user.id, role_id=role_row.id, is_primary=True))
    session.commit()
    attach_roles(session, user)
    return user, employee


def _year(session: Session) -> AcademicYear:
    year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    session.add(year)
    session.commit()
    session.refresh(year)
    return year


def _room(session: Session) -> Classroom:
    klass = ClassName(classname=f"class {uuid4().hex[:4]}", level=11)
    section = Section(section_name=uuid4().hex[:2])
    session.add(klass)
    session.add(section)
    session.commit()
    session.refresh(klass)
    session.refresh(section)

    room = Classroom(class_id=klass.class_id, section_id=section.section_id)
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def _subject(session: Session) -> Subject:
    subject = Subject(name=f"subject {uuid4().hex[:6]}", code=f"S{uuid4().hex[:6]}")
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def _section_subject(
    session: Session,
    *,
    room: Classroom,
    subject: Subject,
    year: AcademicYear,
    teacher: Employee | None = None,
) -> ClassroomSubject:
    row = ClassroomSubject(
        classroom_id=room.id,
        subject_id=subject.id,
        academic_year_id=year.id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    if teacher is not None:
        session.add(
            SubjectTeacher(
                classroom_id=room.id,
                subject_id=subject.id,
                classroom_subject_id=row.id,
                teacher_id=teacher.id,
                academic_year_id=year.id,
                effective_from=date(2026, 6, 1),
            )
        )
        session.commit()
    return row


def _seed(session: Session) -> dict:
    seed_permissions(session)  # the role catalog + every grant the app seeds at boot

    school = _school(session, "Course School", "CRS-0001")
    year = _year(session)
    room = _room(session)
    subject = _subject(session)
    principal, principal_employee = _person(
        session, email="principal@crs.test", code="EMP-0001", role="principal"
    )
    owner, owner_employee = _person(
        session, email="owner@crs.test", code="EMP-0002", role="teacher"
    )
    other, other_employee = _person(
        session, email="other@crs.test", code="EMP-0003", role="teacher"
    )
    accountant, _ = _person(
        session, email="accounts@crs.test", code="EMP-0004", role="accountant"
    )
    course_subject = _section_subject(
        session, room=room, subject=subject, year=year, teacher=owner_employee
    )

    other_school = _school(session, "Other School", "OTH-0001")
    other_year = _year(session)
    other_room = _room(session)
    other_subject = _subject(session)
    other_owner, other_owner_employee = _person(
        session, email="owner@oth.test", code="EMP-0001", role="teacher"
    )
    other_course_subject = _section_subject(
        session,
        room=other_room,
        subject=other_subject,
        year=other_year,
        teacher=other_owner_employee,
    )

    session.info["school_id"] = school.id
    return {
        "school": school,
        "year": year,
        "room": room,
        "subject": subject,
        "course_subject": course_subject,
        "principal": principal,
        "principal_employee": principal_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "other": other,
        "other_employee": other_employee,
        "accountant": accountant,
        "other_school": other_school,
        "other_room": other_room,
        "other_course_subject": other_course_subject,
        "other_owner": other_owner,
        "other_owner_employee": other_owner_employee,
    }


def test_the_office_holds_the_course_rights_and_the_teacher_does_not():
    with memory_session() as session:
        data = _seed(session)

        for check in (
            scope.can_manage_course,
            scope.can_assign_teacher,
            scope.can_approve_course,
            scope.can_view_all_courses,
        ):
            assert check(session, data["principal"]) is True
            assert check(session, data["accountant"]) is False

        assert scope.can_read_course(session, data["principal"]) is True
        assert scope.can_read_course(session, data["owner"]) is True
        assert scope.can_plan_course(session, data["owner"]) is True
        assert scope.can_manage_course(session, data["owner"]) is False
        assert scope.can_assign_teacher(session, data["owner"]) is False
        assert scope.can_approve_course(session, data["owner"]) is False
        assert scope.can_view_all_courses(session, data["owner"]) is False
        assert scope.can_read_course(session, data["accountant"]) is False


def test_a_teacher_owns_only_the_subject_they_hold():
    with memory_session() as session:
        data = _seed(session)
        course_subject = data["course_subject"]

        assert scope.is_own_course_teacher(session, data["owner"], course_subject.id)
        assert not scope.is_own_course_teacher(
            session, data["other"], course_subject.id
        )
        assert scope.may_edit_plan(session, data["owner"], course_subject.id)
        assert not scope.may_edit_plan(session, data["other"], course_subject.id)
        assert scope.may_edit_plan(session, data["principal"], course_subject.id)

        assert scope.may_read_section_course(session, data["owner"], data["room"].id)
        assert not scope.may_read_section_course(
            session, data["accountant"], data["room"].id
        )


def test_a_teacher_change_moves_the_claim():
    with memory_session() as session:
        data = _seed(session)
        course_subject = data["course_subject"]

        old = session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.classroom_subject_id == course_subject.id,
                SubjectTeacher.effective_to.is_(None),
            )
        ).first()
        assert old is not None
        old.effective_to = date(2026, 9, 30)
        session.add(old)
        session.add(
            SubjectTeacher(
                classroom_id=data["room"].id,
                subject_id=data["subject"].id,
                classroom_subject_id=course_subject.id,
                teacher_id=data["other_employee"].id,
                academic_year_id=data["year"].id,
                effective_from=date(2026, 10, 1),
            )
        )
        session.commit()

        assert not scope.is_own_course_teacher(
            session, data["owner"], course_subject.id
        )
        assert scope.is_own_course_teacher(session, data["other"], course_subject.id)
        assert not scope.may_edit_plan(session, data["owner"], course_subject.id)
        assert scope.may_edit_plan(session, data["other"], course_subject.id)


def test_another_school_is_a_missing_row_not_a_denial():
    with memory_session() as session:
        data = _seed(session)

        session.info["school_id"] = data["other_school"].id
        assert not scope.is_own_course_teacher(
            session, data["owner"], data["course_subject"].id
        )
        assert not scope.may_edit_plan(
            session, data["owner"], data["course_subject"].id
        )
        assert (
            scope.visible_course_subject_ids(session, data["owner"], data["room"].id)
            == set()
        )
        assert not scope.may_read_section_course(
            session, data["owner"], data["room"].id
        )

        # The other school's own teacher still owns their own subject.
        assert scope.is_own_course_teacher(
            session, data["other_owner"], data["other_course_subject"].id
        )


def test_visible_subjects_are_filtered_on_the_server():
    with memory_session() as session:
        data = _seed(session)

        assert scope.visible_course_subject_ids(
            session, data["owner"], data["room"].id
        ) == {data["course_subject"].id}
        assert (
            scope.visible_course_subject_ids(
                session, data["principal"], data["room"].id
            )
            is None
        )
        assert (
            scope.visible_course_subject_ids(
                session, data["accountant"], data["room"].id
            )
            == set()
        )


def test_the_office_reads_any_teacher_but_a_teacher_reads_self():
    with memory_session() as session:
        data = _seed(session)

        assert scope.may_read_teacher_course(
            session, data["principal"], data["other_employee"].id
        )
        assert scope.may_read_teacher_course(
            session, data["owner"], data["owner_employee"].id
        )
        assert not scope.may_read_teacher_course(
            session, data["owner"], data["other_employee"].id
        )
        assert not scope.may_read_teacher_course(
            session, data["accountant"], data["owner_employee"].id
        )
