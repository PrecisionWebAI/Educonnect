"""Phase 10 - one Course story followed from subject to approval to handover.

This is the seam test the screens rely on: the same rows are read by the Classroom tab,
the Teachers tab and the notification bell. If one of those grows a second calculation,
this test fails.
"""

import importlib
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import (
    approvals,
    lesson_plans,
    service,
    teacher_course,
)
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    ChapterCreate,
    ChapterTickIn,
    CourseTeacherAssignIn,
    LessonPlanSubmitIn,
    RejectIn,
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


def _school(session: Session, code: str = "E2-0001") -> School:
    school = School(name=f"Course E2E {code}", code=code, email=f"{code}@test")
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


def _rooms(session: Session) -> tuple[Classroom, Classroom]:
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
    return rooms[0], rooms[1]


def _person(session: Session, role: str, code: str) -> tuple[User, Employee]:
    user = User(
        email=f"{uuid4().hex[:10]}@e2.test",
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

def test_the_course_flow_agrees_with_itself_at_every_step():
    with memory_session() as session:
        seed_permissions(session)
        _school(session)
        _year(session)
        first, second = _rooms(session)
        office, _office_employee = _person(session, "principal", "EMP-5001")
        owner, owner_employee = _person(session, "teacher", "EMP-5002")
        incoming, incoming_employee = _person(session, "teacher", "EMP-5003")

        maths = named_subject("maths")
        maths_course = service.add_subject(
            session, first.id, AddSectionSubjectIn(name=maths.name), user=office
        )
        custom_course = service.add_subject(
            session,
            second.id,
            AddSectionSubjectIn(name="English 1"),
            user=office,
        )
        service.assign_teacher(
            session,
            maths_course.classroom_subject_id,
            CourseTeacherAssignIn(
                teacher_id=owner_employee.id,
                effective_from=date.today() - timedelta(days=1),
            ),
            user=office,
        )
        service.assign_teacher(
            session,
            custom_course.classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=incoming_employee.id),
            user=office,
        )

        chapters = [
            service.add_chapter(
                session,
                maths_course.classroom_subject_id,
                ChapterCreate(name=f"Chapter {index}"),
                user=office,
            )
            for index in (1, 2)
        ]
        service.tick_chapter(
            session,
            chapters[0].chapter_id,
            ChapterTickIn(classroom_id=first.id, status=CHAPTER_COMPLETED),
            user=owner,
        )

        today = date.today()
        lesson_plans.submit_week(
            session,
            maths_course.classroom_subject_id,
            today.year,
            today.month,
            1,
            LessonPlanSubmitIn(
                topics="Fractions",
                learning_objectives="Add unlike fractions",
                expected_version=0,
            ),
            user=owner,
        )
        second_week = lesson_plans.submit_week(
            session,
            maths_course.classroom_subject_id,
            today.year,
            today.month,
            2,
            LessonPlanSubmitIn(
                topics="Decimals",
                learning_objectives="Convert fractions",
                expected_version=0,
            ),
            user=owner,
        )
        first_week = next(
            week
            for week in lesson_plans.month_plan(
                session,
                maths_course.classroom_subject_id,
                today.year,
                today.month,
                user=office,
            )
            if week.week_no == 1
        )
        approvals.approve(session, first_week.plan_id, 1, office)
        approvals.reject(
            session,
            second_week.plan_id,
            RejectIn(reason="Add the Friday assessment.", expected_version=1),
            office,
        )
        corrected = lesson_plans.submit_week(
            session,
            maths_course.classroom_subject_id,
            today.year,
            today.month,
            2,
            LessonPlanSubmitIn(
                topics="Decimals revised",
                learning_objectives="Convert fractions",
                assessment="Friday quiz",
                expected_version=1,
            ),
            user=owner,
        )
        approvals.approve(session, corrected.plan_id, 2, office)

        service.assign_teacher(
            session,
            maths_course.classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=incoming_employee.id),
            user=office,
        )
        service.tick_chapter(
            session,
            chapters[1].chapter_id,
            ChapterTickIn(classroom_id=first.id, status=CHAPTER_COMPLETED),
            user=incoming,
        )

        classroom = service.section_course(session, first.id, user=office)
        classroom_maths = classroom.subjects[0]
        assert (classroom_maths.done, classroom_maths.total) == (2, 2)
        assert classroom_maths.percent == 100.0
        assert classroom_maths.lesson_plan.approved == 2

        teacher = teacher_course.teacher_detail(
            session, incoming_employee.id, office
        )
        assignment = next(
            row
            for row in teacher.assignments
            if row.current and row.subject == "maths"
        )
        assert (assignment.done, assignment.total, assignment.percent) == (
            2,
            2,
            100.0,
        )
        assert [week.status for week in assignment.weeks[:2]] == [
            "Approved",
            "Approved",
        ]

        listed = {
            row.employee_id: row
            for row in teacher_course.teacher_list(session, office)
        }[incoming_employee.id]
        assert (listed.subjects_count, listed.sections_count) == (2, 2)
        assert listed.pending_approvals == 0
        assert listed.completion_percent == 100.0

        summary = teacher_course.summary(session, office)
        assert summary.pending_approvals == 0
        assert summary.completion_percent == 100.0

        submitted = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_SUBMITTED
            )
        ).all()
        approved = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_APPROVED
            )
        ).all()
        rejected = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_REJECTED
            )
        ).all()
        assert len(submitted) == 3, "week 1, week 2, and the corrected week 2"
        assert len(approved) == 2
        assert len(rejected) == 1
        assert all(message.user_id == office.id for message in submitted)
        assert all(message.user_id == owner.id for message in approved + rejected)

        past = session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.teacher_id == owner_employee.id
            )
        ).one()
        assert past.effective_to is not None

        _school(session, "E2-0002")
        with pytest.raises(HTTPException) as hidden:
            service.section_course(session, first.id, user=office)
        assert hidden.value.status_code == 404
        with pytest.raises(HTTPException) as hidden_teacher:
            teacher_course.teacher_detail(session, incoming_employee.id, office)
        assert hidden_teacher.value.status_code == 404
