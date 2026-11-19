"""Phase 3 - the subject master and Add Subject: the school's list, and a section's rows.

What is pinned here:

1. **a custom name joins the master list once** - "English 1" gets a generated code, and
   typing it again is a `409`, not a second row;
2. **rename and retire** - a rename cannot shadow another name, and a retired subject
   leaves the picker while `include_inactive` still shows it;
3. **the section's dropdown hides what it already has** - active and archived rows both
   count, because re-adding would collide with the unique key;
4. **archive keeps the work, delete refuses it** - an archived row disappears from the
   default tab but is still readable; a row with a plan or a completed chapter is `409`
   with "archive instead";
5. **a teacher cannot manage** - add/archive/restore/delete are the office's rights on
   the server, not a hidden button;
6. **a teacher sees only their subject** in the section tab; the office sees every row;
7. **another school's section subject is a `404`**, never a `403` that confirms the id.

Runs under pytest and as `python tests/test_course_subjects.py`.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics import service as academics
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ChapterProgress,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.schemas import (
    SubjectCreate,
    SubjectUpdate,
)
from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    COURSE_ARCHIVED,
    LessonPlan,
)
from app.domains.academic.classroom.course.schemas import AddSectionSubjectIn
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


def _person(session: Session, role: str, code: str) -> tuple[User, Employee]:
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
    room = _room(session)
    principal, principal_employee = _person(session, "principal", "EMP-0001")
    teacher, teacher_employee = _person(session, "teacher", "EMP-0002")
    english = academics.create_subject(
        session, SubjectCreate(name="english", code="ENG")
    )
    maths = academics.create_subject(session, SubjectCreate(name="maths", code="MAT"))
    return {
        "school": school,
        "year": year,
        "room": room,
        "principal": principal,
        "principal_employee": principal_employee,
        "teacher": teacher,
        "teacher_employee": teacher_employee,
        "english": english,
        "maths": maths,
    }


def test_a_custom_subject_joins_the_master_list_once():
    with memory_session() as session:
        _seed(session)

        created = academics.create_subject(session, SubjectCreate(name="English 1"))
        assert created.name == "english 1"
        assert created.code == "E1", "initials of 'english 1'"
        assert created.is_active is True

        with pytest.raises(HTTPException) as duplicate:
            academics.create_subject(session, SubjectCreate(name="ENGLISH 1"))
        assert duplicate.value.status_code == 409

        with pytest.raises(HTTPException) as code_taken:
            academics.create_subject(session, SubjectCreate(name="English", code="E1"))
        assert code_taken.value.status_code == 409


def test_a_subject_can_be_renamed_and_retired_without_shadowing_another():
    with memory_session() as session:
        data = _seed(session)
        subject = academics.create_subject(session, SubjectCreate(name="mathematics"))

        renamed = academics.update_subject(
            session, subject.id, SubjectUpdate(name="Algebra")
        )
        assert renamed.name == "algebra"

        with pytest.raises(HTTPException) as clash:
            academics.update_subject(
                session, subject.id, SubjectUpdate(name=data["english"].name)
            )
        assert clash.value.status_code == 409

        academics.update_subject(session, subject.id, SubjectUpdate(is_active=False))
        assert "algebra" not in {row.name for row in academics.get_subjects(session)}
        assert "algebra" in {
            row.name for row in academics.get_subjects(session, include_inactive=True)
        }


def test_a_teacher_cannot_manage_a_section_subject():
    with memory_session() as session:
        data = _seed(session)

        with pytest.raises(HTTPException) as add_denied:
            service.add_subject(
                session,
                data["room"].id,
                AddSectionSubjectIn(subject_id=data["english"].id),
                user=data["teacher"],
            )
        assert add_denied.value.status_code == 403

        row = service.add_subject(
            session,
            data["room"].id,
            AddSectionSubjectIn(subject_id=data["english"].id),
            user=data["principal"],
        )
        for call in (service.archive_subject, service.restore_subject):
            with pytest.raises(HTTPException) as denied:
                call(session, row.classroom_subject_id, user=data["teacher"])
            assert denied.value.status_code == 403

        with pytest.raises(HTTPException) as delete_denied:
            service.delete_subject(
                session, row.classroom_subject_id, user=data["teacher"]
            )
        assert delete_denied.value.status_code == 403


def test_the_section_dropdown_hides_what_it_already_has():
    with memory_session() as session:
        data = _seed(session)
        room = data["room"]

        available = {
            subject.name
            for subject in service.available_subjects(
                session, room.id, user=data["principal"]
            )
        }
        assert available == {"english", "maths"}

        added = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(subject_id=data["english"].id),
            user=data["principal"],
        )
        assert added.status == COURSE_ACTIVE

        available = {
            subject.name
            for subject in service.available_subjects(
                session, room.id, user=data["principal"]
            )
        }
        assert available == {"maths"}, "the added subject leaves the dropdown"

        custom = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(name="English 1"),
            user=data["principal"],
        )
        assert custom.subject == "english 1"
        assert "english 1" in {
            subject.name for subject in academics.get_subjects(session)
        }

        with pytest.raises(HTTPException) as duplicate:
            service.add_subject(
                session,
                room.id,
                AddSectionSubjectIn(name="ENGLISH 1"),
                user=data["principal"],
            )
        assert duplicate.value.status_code == 409


def test_archive_keeps_the_rows_and_delete_refuses_work():
    with memory_session() as session:
        data = _seed(session)
        room = data["room"]
        row = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(subject_id=data["english"].id),
            user=data["principal"],
        )

        course = service.section_course(session, room.id, user=data["principal"])
        assert course.subjects[0].can_delete is True

        archived = service.archive_subject(
            session, row.classroom_subject_id, user=data["principal"]
        )
        assert archived.status == COURSE_ARCHIVED

        assert (
            service.section_course(session, room.id, user=data["principal"]).subjects
            == []
        )
        shown = service.section_course(
            session, room.id, user=data["principal"], include_archived=True
        )
        assert shown.subjects[0].status == COURSE_ARCHIVED
        assert shown.subjects[0].can_restore is True

        restored = service.restore_subject(
            session, row.classroom_subject_id, user=data["principal"]
        )
        assert restored.status == COURSE_ACTIVE

        chapter = Chapter(
            class_id=room.class_id,
            subject_id=data["english"].id,
            academic_year_id=data["year"].id,
            sequence=1,
            name="Chapter 1",
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        session.add(
            ChapterProgress(
                chapter_id=chapter.id,
                classroom_id=room.id,
                status=CHAPTER_COMPLETED,
                completed_on=date(2026, 7, 1),
            )
        )
        session.commit()

        with pytest.raises(HTTPException) as completed:
            service.delete_subject(
                session, row.classroom_subject_id, user=data["principal"]
            )
        assert completed.value.status_code == 409
        assert "archive" in completed.value.detail.lower()

        plan_row = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(subject_id=data["maths"].id),
            user=data["principal"],
        )
        session.add(
            LessonPlan(
                classroom_subject_id=plan_row.classroom_subject_id,
                academic_year_id=data["year"].id,
                year=2026,
                month=11,
                week_no=1,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 7),
            )
        )
        session.commit()

        course = service.section_course(session, room.id, user=data["principal"])
        plan_subject = next(
            subject
            for subject in course.subjects
            if subject.classroom_subject_id == plan_row.classroom_subject_id
        )
        assert plan_subject.can_delete is False
        with pytest.raises(HTTPException) as planned:
            service.delete_subject(
                session, plan_row.classroom_subject_id, user=data["principal"]
            )
        assert planned.value.status_code == 409


def test_a_teacher_sees_only_their_own_subject_in_the_course_tab():
    with memory_session() as session:
        data = _seed(session)
        room = data["room"]
        _other_user, other_employee = _person(session, "teacher", "EMP-0003")

        english = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(subject_id=data["english"].id),
            user=data["principal"],
        )
        maths = service.add_subject(
            session,
            room.id,
            AddSectionSubjectIn(subject_id=data["maths"].id),
            user=data["principal"],
        )
        session.add_all(
            [
                SubjectTeacher(
                    classroom_id=room.id,
                    subject_id=data["english"].id,
                    classroom_subject_id=english.classroom_subject_id,
                    teacher_id=data["teacher_employee"].id,
                    academic_year_id=data["year"].id,
                    effective_from=date(2026, 6, 1),
                ),
                SubjectTeacher(
                    classroom_id=room.id,
                    subject_id=data["maths"].id,
                    classroom_subject_id=maths.classroom_subject_id,
                    teacher_id=other_employee.id,
                    academic_year_id=data["year"].id,
                    effective_from=date(2026, 6, 1),
                ),
            ]
        )
        session.commit()

        own = service.section_course(session, room.id, user=data["teacher"])
        assert [row.classroom_subject_id for row in own.subjects] == [
            english.classroom_subject_id
        ]

        office = service.section_course(session, room.id, user=data["principal"])
        assert {row.classroom_subject_id for row in office.subjects} == {
            english.classroom_subject_id,
            maths.classroom_subject_id,
        }


def test_another_schools_section_subject_is_a_404():
    with memory_session() as session:
        data = _seed(session)
        row = service.add_subject(
            session,
            data["room"].id,
            AddSectionSubjectIn(subject_id=data["english"].id),
            user=data["principal"],
        )

        _school(session, code="OTH-0001")  # binds the session to another school
        with pytest.raises(HTTPException) as missing:
            service.archive_subject(
                session, row.classroom_subject_id, user=data["principal"]
            )
        assert missing.value.status_code == 404
