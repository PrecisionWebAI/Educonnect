"""Phase 8 - Teachers > Course.

Pinned here:

1. the list carries subjects/sections/pending/behind/completion;
2. `course.view_all` sees the roll, a teacher sees only their own row;
3. detail shows current assignments, this month's weeks and chapter progress;
4. another teacher's detail is a `404` (no existence leak), another school too;
5. `/course/my` answers from the token, not from an id in the browser;
6. a closed assignment stays in the teacher's history after a handover.
"""

import importlib
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import service as classroom_service
from app.domains.academic.classroom.academics import service as academics
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.schemas import SubjectCreate
from app.domains.academic.classroom.course import (
    lesson_plans,
    reminders,
    service,
    teacher_course,
)
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    CourseTeacherAssignIn,
    LessonPlanSubmitIn,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.permissions_repository import seed_permissions
from app.domains.auth.roles import attach_roles
from app.domains.main.notifications import events
from app.domains.main.notifications.models import Notification
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


def _school(session: Session, code: str = "TC-0001") -> School:
    school = School(name=f"Teacher Course {code}", code=code, email=f"{code}@test")
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
        email=f"{uuid4().hex[:10]}@tc.test",
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
    year = _year(session)
    first, second = _rooms(session)
    office, office_employee = _person(session, "principal", "EMP-4001")
    owner, owner_employee = _person(session, "teacher", "EMP-4002")
    first.class_teacher_id = owner_employee.id
    session.add(first)
    session.commit()
    other, other_employee = _person(session, "teacher", "EMP-4003")
    accountant, accountant_employee = _person(session, "accountant", "EMP-4004")

    maths = academics.create_subject(session, SubjectCreate(name="maths", code="MAT"))
    english = academics.create_subject(
        session, SubjectCreate(name="english", code="ENG")
    )
    maths_course = service.add_subject(
        session, first.id, AddSectionSubjectIn(name=maths.name), user=office
    )
    english_course = service.add_subject(
        session, second.id, AddSectionSubjectIn(name=english.name), user=office
    )
    service.assign_teacher(
        session,
        maths_course.classroom_subject_id,
        CourseTeacherAssignIn(teacher_id=owner_employee.id),
        user=office,
    )
    service.assign_teacher(
        session,
        english_course.classroom_subject_id,
        CourseTeacherAssignIn(teacher_id=other_employee.id),
        user=office,
    )

    chapters: list[Chapter] = []
    for sequence in (1, 2):
        chapter = Chapter(
            classroom_subject_id=maths_course.classroom_subject_id,
            academic_year_id=year.id,
            sequence=sequence,
            name=f"Chapter {sequence}",
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        chapters.append(chapter)
    chapters[0].status = CHAPTER_COMPLETED
    chapters[0].completed_on = date.today()
    chapters[0].completed_by_employee_id = owner_employee.id
    session.add(chapters[0])
    session.commit()

    return {
        "first": first,
        "second": second,
        "office": office,
        "office_employee": office_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "other": other,
        "other_employee": other_employee,
        "accountant": accountant,
        "accountant_employee": accountant_employee,
        "maths": maths,
        "english": english,
        "maths_course": maths_course,
        "english_course": english_course,
        "chapters": chapters,
    }


def _submit(session: Session, data: dict) -> None:
    today = date.today()
    lesson_plans.submit_week(
        session,
        data["maths_course"].classroom_subject_id,
        today.year,
        today.month,
        1,
        LessonPlanSubmitIn(
            topics="Fractions",
            learning_objectives="Add unlike fractions",
            expected_version=0,
        ),
        user=data["owner"],
    )


def test_the_list_carries_the_counts_and_respects_view_all():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data)

        rows = teacher_course.teacher_list(session, data["office"])
        by_id = {row.employee_id: row for row in rows}
        owner = by_id[data["owner_employee"].id]
        assert (owner.subjects_count, owner.sections_count) == (1, 1)
        assert owner.pending_approvals == 1
        assert owner.behind_subjects == 0
        assert owner.completion_percent == 50.0

        other = by_id[data["other_employee"].id]
        assert (other.subjects_count, other.sections_count) == (1, 1)
        assert other.pending_approvals == 0
        assert other.completion_percent is None

        own = teacher_course.teacher_list(session, data["owner"])
        assert [row.employee_id for row in own] == [data["owner_employee"].id]

        with pytest.raises(HTTPException) as denied:
            teacher_course.teacher_list(session, data["accountant"])
        assert denied.value.status_code == 403


def test_detail_has_weeks_chapters_and_the_right_caller():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data)

        detail = teacher_course.teacher_detail(
            session, data["owner_employee"].id, data["office"]
        )
        assert detail.name == data["owner"].full_name
        current = detail.assignments[0]
        assert (current.current, current.subject, current.total, current.done) == (
            True,
            "maths",
            2,
            1,
        )
        assert current.percent == 50.0
        assert current.weeks[0].status == "Submitted"
        assert current.chapters[0].status == CHAPTER_COMPLETED
        assert current.chapters[0].completed_by == data["owner"].full_name

        self_detail = teacher_course.teacher_detail(
            session, data["owner_employee"].id, data["owner"]
        )
        assert self_detail.employee_id == data["owner_employee"].id

        with pytest.raises(HTTPException) as hidden:
            teacher_course.teacher_detail(
                session, data["owner_employee"].id, data["other"]
            )
        assert hidden.value.status_code == 404


def test_my_course_uses_the_token_and_another_school_is_404():
    with memory_session() as session:
        data = _seed(session)

        mine = teacher_course.my_course(session, data["owner"])
        assert mine.employee_id == data["owner_employee"].id
        assert mine.assignments[0].subject == "maths"

        _school(session, "TC-0002")
        with pytest.raises(HTTPException) as hidden:
            teacher_course.teacher_detail(
                session, data["owner_employee"].id, data["office"]
            )
        assert hidden.value.status_code == 404


def test_a_submit_notifies_the_approvers_once_per_version():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data)

        messages = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_SUBMITTED
            )
        ).all()
        assert len(messages) == 1
        assert messages[0].user_id == data["office"].id
        assert "Week 1" in messages[0].body
        assert messages[0].dedupe_key.endswith(":v1:submitted")


def test_the_reminder_job_nudges_only_unplanned_finished_weeks():
    with memory_session() as session:
        data = _seed(session)

        first = reminders.remind_unsubmitted(session)
        assert first > 0, "the month has at least one finished week without a plan"
        assert reminders.remind_unsubmitted(session) == 0, "the dedupe key holds"

        messages = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_REMINDER
            )
        ).all()
        assert all(
            message.user_id in (data["owner"].id, data["other"].id)
            for message in messages
        )


def test_summary_and_the_classroom_card_agree():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data)

        summary = teacher_course.summary(session, data["office"])
        assert (summary.subject_count, summary.pending_approvals) == (2, 1)
        assert summary.completion_percent == 50.0

        section = teacher_course.section_summary(
            session, data["first"].id, data["office"]
        )
        assert (section.subject_count, section.pending_approvals) == (1, 1)
        assert section.completion_percent == 50.0

        groups = classroom_service.overview(session)
        card = next(
            section
            for group in groups
            for section in group.sections
            if section.sectionId == data["first"].id
        )
        assert card.pendingApprovals == 1
        assert card.syllabusPercent == 50.0


def test_a_closed_assignment_stays_in_the_teachers_history():
    with memory_session() as session:
        data = _seed(session)

        held = session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.teacher_id == data["owner_employee"].id
            )
        ).one()
        held.effective_from = date.today() - timedelta(days=1)
        held.effective_to = date.today()
        session.add(held)
        session.add(
            SubjectTeacher(
                classroom_id=data["first"].id,
                subject_id=data["maths"].id,
                classroom_subject_id=data["maths_course"].classroom_subject_id,
                teacher_id=data["other_employee"].id,
                academic_year_id=held.academic_year_id,
                effective_from=date.today(),
            )
        )
        session.commit()

        history = teacher_course.teacher_detail(
            session, data["owner_employee"].id, data["office"]
        )
        assert [
            (row.current, row.effective_to is not None) for row in history.assignments
        ] == [(False, True)]

        current = teacher_course.teacher_detail(
            session, data["other_employee"].id, data["office"]
        )
        assert any(
            row.current and row.subject == "maths" for row in current.assignments
        )
