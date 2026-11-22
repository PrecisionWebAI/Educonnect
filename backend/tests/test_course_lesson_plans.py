"""Phase 6 - the weekly lesson plan, submitted (not drafted).

Pinned here:

1. the month is Week 1-4, plus Week 5 only when it has a 29th;
2. submit writes the working row **and** the immutable history snapshot;
3. a stale `expected_version` is a `409`, not an overwrite;
4. `topics` + `learning_objectives` are required and fields are capped;
5. an approved week is locked until `intent="change"`, and the approved snapshot stays;
6. a rejected week can be corrected and resubmitted, clearing the old reason;
7. only the current holder (or the office) writes; another school is a `404`;
8. the Course row's summary counts the submit in the current month.
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
from app.domains.academic.classroom.course import lesson_plans, service, teaching_days
from app.domains.academic.classroom.course.models import (
    PLAN_APPROVED,
    PLAN_REJECTED,
    LessonPlan,
    LessonPlanHistory,
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


def _school(session: Session, code: str = "LP-0001") -> School:
    school = School(name=f"Lesson School {code}", code=code, email=f"{code}@test")
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
    klass = ClassName(classname=f"class {uuid4().hex[:4]}", level=9)
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
        email=f"{uuid4().hex[:10]}@lp.test",
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
    room = _room(session)
    office, office_employee = _person(session, "principal", "EMP-2001")
    owner, owner_employee = _person(session, "teacher", "EMP-2002")
    outsider, outsider_employee = _person(session, "teacher", "EMP-2003")
    subject = named_subject("maths")
    course = service.add_subject(
        session, room.id, AddSectionSubjectIn(name=subject.name), user=office
    )
    return {
        "room": room,
        "office": office,
        "office_employee": office_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "outsider": outsider,
        "outsider_employee": outsider_employee,
        "subject": subject,
        "course": course,
    }


def _submit(
    session: Session,
    data: dict,
    *,
    year: int,
    month: int,
    week_no: int,
    expected_version: int = 0,
    user=None,
    topics: str = "Fractions",
    objectives: str = "Add unlike fractions",
    intent: str | None = None,
    **overrides,
):
    payload = LessonPlanSubmitIn(
        topics=topics,
        learning_objectives=objectives,
        expected_version=expected_version,
        intent=intent,
        **overrides,
    )
    return lesson_plans.submit_week(
        session,
        data["course"].classroom_subject_id,
        year,
        month,
        week_no,
        payload,
        user=user or data["office"],
    )


def _plan(session: Session, data: dict) -> LessonPlan:
    return session.exec(
        select(LessonPlan).where(
            LessonPlan.classroom_subject_id == data["course"].classroom_subject_id
        )
    ).one()


def test_week_five_exists_only_when_the_month_has_a_29th():
    with memory_session() as session:
        data = _seed(session)

        november = lesson_plans.month_plan(
            session, data["course"].classroom_subject_id, 2026, 11, user=data["office"]
        )
        february = lesson_plans.month_plan(
            session, data["course"].classroom_subject_id, 2027, 2, user=data["office"]
        )
        # A leap February is outside this 2026-27 subject; the calendar rule itself is
        # still checked on the week helper.
        leap_february = teaching_days.week_ranges(session, 2028, 2)

        assert [week.week_no for week in november] == [1, 2, 3, 4, 5]
        assert [week.week_no for week in february] == [1, 2, 3, 4]
        assert [week.week_no for week in leap_february] == [1, 2, 3, 4, 5]
        assert november[0].start_date == date(2026, 11, 1)
        assert november[4].start_date == date(2026, 11, 29)
        assert november[0].teaching_days, "the real open days are sent to the tab"


def test_a_month_outside_the_academic_year_is_refused_not_defaulted():
    with memory_session() as session:
        data = _seed(session)
        course_id = data["course"].classroom_subject_id

        # April-December fall in the start year, January-March in the next one.
        for year, month in ((2026, 4), (2026, 12), (2027, 1), (2027, 3)):
            weeks = lesson_plans.month_plan(
                session, course_id, year, month, user=data["office"]
            )
            assert weeks, f"{month}/{year} is inside 2026-27"

        # March 2026 belongs to the previous year, April 2027 to the next.
        for year, month in ((2026, 3), (2027, 4), (2025, 12)):
            with pytest.raises(HTTPException) as refused:
                lesson_plans.month_plan(
                    session, course_id, year, month, user=data["office"]
                )
            assert refused.value.status_code == 422
            assert "2026-27" in str(refused.value.detail)

            with pytest.raises(HTTPException) as refused_submit:
                _submit(session, data, year=year, month=month, week_no=1)
            assert refused_submit.value.status_code == 422


def test_submit_writes_the_plan_and_an_immutable_snapshot():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()

        week = _submit(
            session,
            data,
            year=today.year,
            month=today.month,
            week_no=1,
        )

        assert (week.status, week.version, week.expected_version) == (
            "Submitted",
            1,
            1,
        )
        assert week.topics == "Fractions"
        assert week.can_edit is True

        plan = _plan(session, data)
        history = session.exec(
            select(LessonPlanHistory).where(LessonPlanHistory.lesson_plan_id == plan.id)
        ).one()
        assert (history.version, history.topics) == (1, "Fractions")

        course = service.section_course(session, data["room"].id, user=data["office"])
        summary = course.subjects[0].lesson_plan
        assert summary is not None
        assert (summary.submitted, summary.pending, summary.approved) == (1, 1, 0)


def test_a_stale_expected_version_is_a_conflict_not_an_overwrite():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()

        _submit(session, data, year=today.year, month=today.month, week_no=1)

        with pytest.raises(HTTPException) as stale:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                expected_version=0,
            )
        assert stale.value.status_code == 409

        second = _submit(
            session,
            data,
            year=today.year,
            month=today.month,
            week_no=1,
            expected_version=1,
            topics="Fractions II",
        )
        assert second.version == 2
        assert second.topics == "Fractions II"
        assert (
            len(
                session.exec(
                    select(LessonPlanHistory).where(
                        LessonPlanHistory.lesson_plan_id == _plan(session, data).id
                    )
                ).all()
            )
            == 2
        )


def test_required_fields_and_the_length_cap_are_enforced():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()

        with pytest.raises(HTTPException) as topics:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                topics="   ",
            )
        assert topics.value.status_code == 422

        with pytest.raises(HTTPException) as objectives:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                objectives="",
            )
        assert objectives.value.status_code == 422

        with pytest.raises(HTTPException) as too_long:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                topics="x" * 2001,
            )
        assert too_long.value.status_code == 422


def test_an_approved_week_needs_an_explicit_change_and_keeps_the_approved_snapshot():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()
        first = _submit(session, data, year=today.year, month=today.month, week_no=1)

        plan = _plan(session, data)
        plan.status = PLAN_APPROVED
        plan.approved_version = first.version
        session.add(plan)
        session.commit()

        weeks = lesson_plans.month_plan(
            session,
            data["course"].classroom_subject_id,
            today.year,
            today.month,
            user=data["office"],
        )
        locked = weeks[0]
        assert locked.can_edit is False
        assert locked.can_request_change is True

        with pytest.raises(HTTPException) as locked_error:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                expected_version=1,
            )
        assert locked_error.value.status_code == 409

        changed = _submit(
            session,
            data,
            year=today.year,
            month=today.month,
            week_no=1,
            expected_version=1,
            topics="Fractions revised",
            intent="change",
        )
        assert (changed.status, changed.version) == ("Submitted", 2)
        assert changed.approved_version == 1
        assert changed.approved is not None
        assert changed.approved.topics == "Fractions"
        assert changed.topics == "Fractions revised"


def test_a_rejected_week_can_be_corrected_and_the_reason_clears():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()
        _submit(session, data, year=today.year, month=today.month, week_no=1)

        plan = _plan(session, data)
        plan.status = PLAN_REJECTED
        plan.rejection_reason = "Add the assessment for Friday."
        session.add(plan)
        session.commit()

        fixed = _submit(
            session,
            data,
            year=today.year,
            month=today.month,
            week_no=1,
            expected_version=1,
            assessment="Friday quiz",
        )
        assert (fixed.status, fixed.version) == ("Submitted", 2)
        assert fixed.rejection_reason is None
        assert fixed.assessment == "Friday quiz"


def test_only_the_current_holder_or_the_office_writes():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()
        service.assign_teacher(
            session,
            data["course"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
            user=data["office"],
        )

        with pytest.raises(HTTPException) as hidden:
            lesson_plans.month_plan(
                session,
                data["course"].classroom_subject_id,
                today.year,
                today.month,
                user=data["outsider"],
            )
        assert hidden.value.status_code == 403

        with pytest.raises(HTTPException) as not_the_teacher:
            _submit(
                session,
                data,
                year=today.year,
                month=today.month,
                week_no=1,
                user=data["outsider"],
            )
        assert not_the_teacher.value.status_code == 403

        own = _submit(
            session,
            data,
            year=today.year,
            month=today.month,
            week_no=1,
            user=data["owner"],
        )
        assert own.status == "Submitted"


def test_a_week_that_does_not_exist_is_refused():
    with memory_session() as session:
        data = _seed(session)

        with pytest.raises(HTTPException) as no_week:
            _submit(session, data, year=2026, month=2, week_no=5)
        assert no_week.value.status_code == 422


def test_another_school_cannot_read_or_submit_this_plan():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()
        _school(session, "LP-0002")

        with pytest.raises(HTTPException) as hidden_read:
            lesson_plans.month_plan(
                session,
                data["course"].classroom_subject_id,
                today.year,
                today.month,
                user=data["office"],
            )
        assert hidden_read.value.status_code == 404

        with pytest.raises(HTTPException) as hidden_write:
            _submit(session, data, year=today.year, month=today.month, week_no=1)
        assert hidden_write.value.status_code == 404
