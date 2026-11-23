"""Classroom-owned subjects: the Phase 1 rules.

Pinned here:
* a name is unique only inside one classroom + academic year;
* another classroom may use the same name;
* rename changes one row and leaves the other classroom untouched;
* an archived name may be added again, while restoring it next to an active
  duplicate is a 409;
* the tenant boundary is a 404, not a 403.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
)
from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    ClassroomSubjectUpdate,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.permissions_repository import seed_permissions
from app.domains.auth.roles import attach_roles


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


def _school(session: Session, code: str = "SUB-0001") -> School:
    school = School(
        name=f"Subject School {code}",
        code=code,
        email=f"office@{code.lower()}.test",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


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


def _person(session: Session, role: str, code: str):
    from app.domains.people.staff.models import Employee

    user = User(
        email=f"{uuid4().hex[:10]}@sub.test",
        full_name=f"{role} {code}",
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
    assert role_row is not None
    session.add(UserRole(user_id=user.id, role_id=role_row.id, is_primary=True))
    session.commit()
    attach_roles(session, user)
    return user, employee


def _seed(session: Session) -> dict:
    seed_permissions(session)
    school = _school(session)
    year = _year(session)
    first = _room(session)
    second = _room(session)
    principal, _ = _person(session, "principal", "EMP-0001")
    teacher, _ = _person(session, "teacher", "EMP-0002")
    return {
        "school": school,
        "year": year,
        "first": first,
        "second": second,
        "principal": principal,
        "teacher": teacher,
    }


def test_same_name_twice_in_one_classroom_is_refused_case_insensitively():
    with memory_session() as session:
        data = _seed(session)
        room = data["first"]
        service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(name="Computer Science"),
            user=data["principal"],
        )

        with pytest.raises(HTTPException) as duplicate:
            service.add_subject(
                session,
                room.id,
                AddSectionSubjectIn(name="  COMPUTER   SCIENCE "),
                user=data["principal"],
            )
        assert duplicate.value.status_code == 409


def test_same_name_in_two_classrooms_is_allowed_and_rename_is_isolated():
    with memory_session() as session:
        data = _seed(session)
        first = service.add_subject(
            session,
            data["first"].id,
            AddSectionSubjectIn(name="Computer Science"),
            user=data["principal"],
        )
        second = service.add_subject(
            session,
            data["second"].id,
            AddSectionSubjectIn(name="Computer Science"),
            user=data["principal"],
        )

        service.rename_subject(
            session,
            first.classroom_subject_id,
            ClassroomSubjectUpdate(name="Computer"),
            user=data["principal"],
        )

        first_row = session.get(ClassroomSubject, first.classroom_subject_id)
        second_row = session.get(ClassroomSubject, second.classroom_subject_id)
        assert first_row is not None and first_row.name == "computer"
        assert second_row is not None and second_row.name == "computer science"
        assert "subject_id" not in ClassroomSubject.__table__.columns, (
            "a section subject has no school-wide subject behind it"
        )


def test_archived_name_can_be_added_again_and_restore_duplicate_is_409():
    with memory_session() as session:
        data = _seed(session)
        room = data["first"]
        old = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(name="English 1"),
            user=data["principal"],
        )
        service.archive_subject(
            session, old.classroom_subject_id, user=data["principal"]
        )

        fresh = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(name="English 1"),
            user=data["principal"],
        )
        assert fresh.status == "Active"

        with pytest.raises(HTTPException) as duplicate:
            service.restore_subject(
                session, old.classroom_subject_id, user=data["principal"]
            )
        assert duplicate.value.status_code == 409


def test_a_teacher_cannot_add_or_rename():
    with memory_session() as session:
        data = _seed(session)
        with pytest.raises(HTTPException) as add_refused:
            service.add_subject(
                session,
                data["first"].id,
                AddSectionSubjectIn(name="Maths"),
                user=data["teacher"],
            )
        assert add_refused.value.status_code == 403

        row = service.add_subject(
            session,
            data["first"].id,
            AddSectionSubjectIn(name="Maths"),
            user=data["principal"],
        )
        with pytest.raises(HTTPException) as rename_refused:
            service.rename_subject(
                session,
                row.classroom_subject_id,
                ClassroomSubjectUpdate(name="Mathematics"),
                user=data["teacher"],
            )
        assert rename_refused.value.status_code == 403


def test_another_schools_subject_is_a_404():
    with memory_session() as session:
        data = _seed(session)
        row = service.add_subject(
            session,
            data["first"].id,
            AddSectionSubjectIn(name="History"),
            user=data["principal"],
        )

        other = _school(session, "SUB-0002")
        assert other.id != data["school"].id
        with pytest.raises(HTTPException) as hidden:
            service.rename_subject(
                session,
                row.classroom_subject_id,
                ClassroomSubjectUpdate(name="World History"),
                user=data["principal"],
            )
        assert hidden.value.status_code == 404

