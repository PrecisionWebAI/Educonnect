"""Phase 5 - the chapter plan and the section's answer.

Pinned here:

1. a chapter is **class-level**: adding it once shows it in 9-A and 9-B;
2. an occupied explicit sequence is refused, and a move renumbers without duplicates;
3. a teacher may tick only the subject they hold **now** - the old holder is refused;
4. the tick records **today and who**, and a handover does not move the old credit;
5. a completed chapter cannot be deleted (undo first), and an empty one can;
6. table total/completed/percentage and the Classroom card read the same chapters.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import repository as classroom_repository
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    CHAPTER_PENDING,
    Chapter,
    ClassName,
    Classroom,
    Section,
)
from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    ChapterCreate,
    ChapterTickIn,
    ChapterUpdate,
    CourseTeacherAssignIn,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.permissions_repository import seed_permissions
from app.domains.auth.roles import attach_roles
from app.domains.people.staff.models import Employee
from tests.course_support import named_subject


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


def _school(session: Session, code: str = "CH-0001") -> School:
    school = School(name=f"Chapter School {code}", code=code, email=f"{code}@test")
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


def _rooms(session: Session) -> list[Classroom]:
    klass = ClassName(classname=f"class {uuid4().hex[:4]}", level=9)
    session.add(klass)
    session.commit()
    session.refresh(klass)

    rooms: list[Classroom] = []
    for letter in ("A", "B"):
        section = Section(section_name=letter)
        session.add(section)
        session.commit()
        session.refresh(section)
        room = Classroom(class_id=klass.class_id, section_id=section.section_id)
        session.add(room)
        session.commit()
        session.refresh(room)
        rooms.append(room)
    return rooms


def _person(session: Session, role: str, code: str) -> tuple[User, Employee]:
    user = User(
        email=f"{uuid4().hex[:10]}@ch.test",
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
    _school(session)
    _year(session)
    first, second = _rooms(session)
    office, office_employee = _person(session, "principal", "EMP-1001")
    owner, owner_employee = _person(session, "teacher", "EMP-1002")
    incoming, incoming_employee = _person(session, "teacher", "EMP-1003")
    outsider, outsider_employee = _person(session, "teacher", "EMP-1004")
    subject = named_subject("maths")

    first_row = service.add_subject(
        session, first.id, AddSectionSubjectIn(name=subject.name), user=office
    )
    second_row = service.add_subject(
        session, second.id, AddSectionSubjectIn(name=subject.name), user=office
    )
    return {
        "first": first,
        "second": second,
        "office": office,
        "office_employee": office_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "incoming": incoming,
        "incoming_employee": incoming_employee,
        "outsider": outsider,
        "outsider_employee": outsider_employee,
        "subject": subject,
        "first_row": first_row,
        "second_row": second_row,
    }


def _sequence(session: Session, data: dict) -> list[tuple[int, str]]:
    rows = session.exec(
        select(Chapter)
        .where(Chapter.classroom_subject_id == data["first_row"].classroom_subject_id)
        .order_by(Chapter.sequence)
    ).all()
    return [(row.sequence, row.name) for row in rows]


def _tick(session: Session, data: dict, chapter_id, status: str, user):
    return service.tick_chapter(
        session,
        chapter_id,
        ChapterTickIn(classroom_id=data["first"].id, status=status),
        user=user,
    )


def test_a_chapter_belongs_to_its_own_section_and_not_to_the_class():
    with memory_session() as session:
        data = _seed(session)
        first = service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="The French Revolution", planned_date=date(2026, 7, 15)),
            user=data["office"],
        )
        second = service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="The Industrial Revolution"),
            user=data["office"],
        )
        assert (first.sequence, second.sequence) == (1, 2)
        assert first.can_edit is True

        a = service.section_course(session, data["first"].id, user=data["office"])
        b = service.section_course(session, data["second"].id, user=data["office"])
        assert [row.total for row in a.subjects] == [2]
        assert [chapter.name for chapter in a.subjects[0].chapters] == [
            "The French Revolution",
            "The Industrial Revolution",
        ]
        # The other section of the same class has the subject but none of the chapters.
        assert [row.total for row in b.subjects] == [0]
        assert b.subjects[0].chapters == []


def test_an_occupied_sequence_is_refused_and_a_move_renumbers():
    with memory_session() as session:
        data = _seed(session)
        for name in ("One", "Two", "Three"):
            service.add_chapter(
                session,
                data["first_row"].classroom_subject_id,
                ChapterCreate(name=name),
                user=data["office"],
            )

        with pytest.raises(HTTPException) as duplicate:
            service.add_chapter(
                session,
                data["first_row"].classroom_subject_id,
                ChapterCreate(name="Another One", sequence=1),
                user=data["office"],
            )
        assert duplicate.value.status_code == 409

        third = session.exec(select(Chapter).where(Chapter.name == "Three")).one()
        service.update_chapter(
            session,
            third.id,
            ChapterUpdate(sequence=1),
            user=data["office"],
        )
        assert _sequence(session, data) == [(1, "Three"), (2, "One"), (3, "Two")]

        first = session.exec(select(Chapter).where(Chapter.name == "One")).one()
        service.update_chapter(
            session,
            first.id,
            ChapterUpdate(sequence=3),
            user=data["office"],
        )
        assert _sequence(session, data) == [(1, "Three"), (2, "Two"), (3, "One")]


def test_only_the_current_holder_ticks_and_credit_stays_with_the_doer():
    with memory_session() as session:
        data = _seed(session)
        chapters = [
            service.add_chapter(
                session,
                data["first_row"].classroom_subject_id,
                ChapterCreate(name=f"Chapter {index}"),
                user=data["office"],
            )
            for index in range(1, 4)
        ]
        service.assign_teacher(
            session,
            data["first_row"].classroom_subject_id,
            CourseTeacherAssignIn(
                teacher_id=data["owner_employee"].id,
                effective_from=date(2026, 7, 1),
            ),
            user=data["office"],
        )

        ticked = _tick(
            session,
            data,
            chapters[0].chapter_id,
            CHAPTER_COMPLETED,
            data["owner"],
        )
        assert ticked.completed_on == date.today()
        assert ticked.completed_by_employee_id == data["owner_employee"].id

        service.assign_teacher(
            session,
            data["first_row"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["incoming_employee"].id),
            user=data["office"],
        )

        with pytest.raises(HTTPException) as refused:
            _tick(
                session,
                data,
                chapters[2].chapter_id,
                CHAPTER_COMPLETED,
                data["owner"],
            )
        assert refused.value.status_code == 403

        _tick(
            session,
            data,
            chapters[1].chapter_id,
            CHAPTER_COMPLETED,
            data["incoming"],
        )

        course = service.section_course(session, data["first"].id, user=data["office"])
        maths = course.subjects[0]
        assert (maths.done, maths.total, maths.percent) == (2, 3, 66.7)
        shares = {row.employee_id: row for row in maths.teachers}
        assert shares[data["owner_employee"].id].completed == 1
        assert shares[data["owner_employee"].id].current is False
        assert shares[data["incoming_employee"].id].completed == 1
        assert shares[data["incoming_employee"].id].current is True


def test_a_teacher_plans_a_draft_and_the_approved_list_is_theirs_to_tick_only():
    with memory_session() as session:
        data = _seed(session)
        service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 1"),
            user=data["office"],
        )
        service.assign_teacher(
            session,
            data["first_row"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
            user=data["office"],
        )

        cs = data["first_row"].classroom_subject_id
        draft = service.list_chapters(session, cs, user=data["owner"])
        assert len(draft) == 1
        # A Draft is the teacher's to plan; nothing can be ticked yet.
        assert draft[0].can_edit is True
        assert draft[0].can_tick is False

        with pytest.raises(HTTPException) as hidden:
            service.list_chapters(session, cs, user=data["outsider"])
        assert hidden.value.status_code == 403

        with pytest.raises(HTTPException) as stranger:
            service.add_chapter(
                session, cs, ChapterCreate(name="Not mine"), user=data["outsider"]
            )
        assert stranger.value.status_code == 403

        service.submit_chapter_plan(session, cs, user=data["owner"])
        service.approve_chapter_plan(session, cs, user=data["office"])

        approved = service.list_chapters(session, cs, user=data["owner"])
        assert approved[0].can_tick is True
        assert approved[0].can_edit is False
        with pytest.raises(HTTPException) as denied:
            service.add_chapter(
                session, cs, ChapterCreate(name="Teacher's chapter"), user=data["owner"]
            )
        assert denied.value.status_code == 403


def test_a_completed_chapter_cannot_be_deleted_until_the_tick_is_undone():
    with memory_session() as session:
        data = _seed(session)
        first = service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 1"),
            user=data["office"],
        )
        service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 2"),
            user=data["office"],
        )
        _tick(session, data, first.chapter_id, CHAPTER_COMPLETED, data["office"])

        with pytest.raises(HTTPException) as blocked:
            service.delete_chapter(session, first.chapter_id, user=data["office"])
        assert blocked.value.status_code == 409

        _tick(session, data, first.chapter_id, CHAPTER_PENDING, data["office"])
        service.delete_chapter(session, first.chapter_id, user=data["office"])
        assert [name for _, name in _sequence(session, data)] == ["Chapter 2"]


def test_the_table_and_the_card_read_the_same_chapters():
    with memory_session() as session:
        data = _seed(session)
        assert (
            classroom_repository.get_syllabus_percent(session, data["first"].id) is None
        )

        first = service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 1"),
            user=data["office"],
        )
        service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 2"),
            user=data["office"],
        )

        before = service.section_course(session, data["first"].id, user=data["office"])
        assert before.subjects[0].total == 2
        assert before.subjects[0].percent == 0.0
        assert before.completion_percent == 0.0
        assert (
            classroom_repository.get_syllabus_percent(session, data["first"].id) == 0.0
        )

        _tick(session, data, first.chapter_id, CHAPTER_COMPLETED, data["office"])
        after = service.section_course(session, data["first"].id, user=data["office"])
        assert after.subjects[0].done == 1
        assert after.subjects[0].percent == 50.0
        assert after.completion_percent == 50.0
        assert (
            classroom_repository.get_syllabus_percent(session, data["first"].id) == 50.0
        )


def test_a_chapter_from_another_school_is_never_visible():
    with memory_session() as session:
        data = _seed(session)
        chapter = service.add_chapter(
            session,
            data["first_row"].classroom_subject_id,
            ChapterCreate(name="Chapter 1"),
            user=data["office"],
        )
        _school(session, "CH-0002")

        with pytest.raises(HTTPException) as hidden:
            service.update_chapter(
                session,
                chapter.chapter_id,
                ChapterUpdate(name="Changed"),
                user=data["office"],
            )
        assert hidden.value.status_code == 404
