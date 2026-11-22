"""Phase 7 - the principal's approval flow.

Pinned here:

1. the queue holds only submitted weeks, with the full six fields;
2. approve stamps the history, sets `approved_version`, and repeating it is `200`;
3. a stale `expected_version` is `409`, and another school is `404`;
4. reject needs a reason, stores it, and tells the teacher;
5. a rejected week can be corrected and returns to the queue as a new version;
6. bulk approve saves the valid rows and reports the stale ones in `skipped`;
7. only `course.approve` may review; a teacher cannot;
8. after a teacher change, the new holder can correct a pending week.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics import service as academics
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
)
from app.domains.academic.classroom.academics.schemas import SubjectCreate
from app.domains.academic.classroom.course import (
    approvals,
    lesson_plans,
    service,
)
from app.domains.academic.classroom.course.models import (
    PLAN_APPROVED,
    PLAN_REJECTED,
    LessonPlan,
    LessonPlanHistory,
)
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    ApproveManyIn,
    ApproveManyItem,
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


def _school(session: Session, code: str = "AP-0001") -> School:
    school = School(name=f"Approval School {code}", code=code, email=f"{code}@test")
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
        email=f"{uuid4().hex[:10]}@ap.test",
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
    office, office_employee = _person(session, "principal", "EMP-3001")
    owner, owner_employee = _person(session, "teacher", "EMP-3002")
    incoming, incoming_employee = _person(session, "teacher", "EMP-3003")
    outsider, outsider_employee = _person(session, "teacher", "EMP-3004")
    subject = academics.create_subject(session, SubjectCreate(name="maths", code="MAT"))
    course = service.add_subject(
        session, room.id, AddSectionSubjectIn(name=subject.name), user=office
    )
    service.assign_teacher(
        session,
        course.classroom_subject_id,
        CourseTeacherAssignIn(teacher_id=owner_employee.id),
        user=office,
    )
    return {
        "room": room,
        "office": office,
        "office_employee": office_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "incoming": incoming,
        "incoming_employee": incoming_employee,
        "outsider": outsider,
        "outsider_employee": outsider_employee,
        "subject": subject,
        "course": course,
    }


def _submit(
    session: Session,
    data: dict,
    *,
    week_no: int = 1,
    expected_version: int = 0,
    user=None,
    topics: str = "Fractions",
):
    today = date.today()
    return lesson_plans.submit_week(
        session,
        data["course"].classroom_subject_id,
        today.year,
        today.month,
        week_no,
        LessonPlanSubmitIn(
            topics=topics,
            learning_objectives="Add unlike fractions",
            expected_version=expected_version,
        ),
        user=user or data["owner"],
    )


def _plan(session: Session, data: dict, week_no: int = 1) -> LessonPlan:
    return session.exec(
        select(LessonPlan).where(
            LessonPlan.classroom_subject_id == data["course"].classroom_subject_id,
            LessonPlan.week_no == week_no,
        )
    ).one()


def test_the_queue_holds_submitted_weeks_with_the_full_plan():
    with memory_session() as session:
        data = _seed(session)
        submitted = _submit(session, data)

        rows = approvals.review_queue(session, data["office"])
        assert len(rows) == 1
        assert rows[0].plan_id == submitted.plan_id
        assert rows[0].topics == "Fractions"
        assert rows[0].learning_objectives == "Add unlike fractions"
        assert rows[0].submitted_by == data["owner"].full_name
        assert rows[0].expected_version == 1
        assert approvals.count_review_queue(session, data["office"]) == 1

        with pytest.raises(HTTPException) as denied:
            approvals.review_queue(session, data["owner"])
        assert denied.value.status_code == 403


def test_approve_stamps_the_history_and_repeating_it_is_idempotent():
    with memory_session() as session:
        data = _seed(session)
        submitted = _submit(session, data)

        decision = approvals.approve(session, submitted.plan_id, 1, data["office"])
        assert (decision.status, decision.approved_version) == ("Approved", 1)
        plan = _plan(session, data)
        assert (plan.status, plan.reviewed_by_user_id) == (
            PLAN_APPROVED,
            data["office"].id,
        )
        history = session.exec(
            select(LessonPlanHistory).where(
                LessonPlanHistory.lesson_plan_id == plan.id,
                LessonPlanHistory.version == 1,
            )
        ).one()
        assert history.approved_at is not None
        assert history.approved_by_user_id == data["office"].id
        assert approvals.count_review_queue(session, data["office"]) == 0
        assert (
            service.section_course(session, data["room"].id, user=data["office"])
            .subjects[0]
            .lesson_plan.approved
            == 1
        )

        again = approvals.approve(session, submitted.plan_id, 1, data["office"])
        assert (again.status, again.version) == ("Approved", 1)

        messages = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_APPROVED
            )
        ).all()
        assert len(messages) == 1
        assert messages[0].user_id == data["owner"].id


def test_a_stale_expected_version_is_conflict_and_reject_needs_a_reason():
    with memory_session() as session:
        data = _seed(session)
        submitted = _submit(session, data)

        with pytest.raises(HTTPException) as stale:
            approvals.approve(session, submitted.plan_id, 0, data["office"])
        assert stale.value.status_code == 409

        with pytest.raises(ValidationError):
            RejectIn(reason="   ", expected_version=1)

        rejected = approvals.reject(
            session,
            submitted.plan_id,
            RejectIn(reason="Add the Friday assessment.", expected_version=1),
            data["office"],
        )
        assert rejected.status == PLAN_REJECTED
        assert rejected.rejection_reason == "Add the Friday assessment."
        plan = _plan(session, data)
        assert plan.rejection_reason == "Add the Friday assessment."

        history = session.exec(
            select(LessonPlanHistory).where(
                LessonPlanHistory.lesson_plan_id == plan.id,
                LessonPlanHistory.version == 1,
            )
        ).one()
        assert history.rejected_at is not None
        assert history.rejection_reason == "Add the Friday assessment."

        messages = session.exec(
            select(Notification).where(
                Notification.event_type == events.EVENT_COURSE_WEEK_REJECTED
            )
        ).all()
        assert len(messages) == 1
        assert "Add the Friday assessment." in messages[0].body

        corrected = _submit(
            session,
            data,
            expected_version=1,
            topics="Fractions corrected",
        )
        assert (corrected.status, corrected.version) == ("Submitted", 2)
        assert corrected.rejection_reason is None
        assert approvals.count_review_queue(session, data["office"]) == 1


def test_bulk_approve_saves_valid_rows_and_reports_stale_ones():
    with memory_session() as session:
        data = _seed(session)
        first = _submit(session, data, week_no=1)
        second = _submit(session, data, week_no=2, topics="Decimals")

        result = approvals.approve_many(
            session,
            ApproveManyIn(
                items=[
                    ApproveManyItem(plan_id=first.plan_id, expected_version=1),
                    ApproveManyItem(plan_id=second.plan_id, expected_version=0),
                ]
            ),
            data["office"],
        )
        assert result.approved == [first.plan_id]
        assert [(row.plan_id, row.status) for row in result.skipped] == [
            (second.plan_id, "skipped")
        ]
        assert _plan(session, data, week_no=1).status == PLAN_APPROVED
        assert _plan(session, data, week_no=2).status == "Submitted"


def test_only_the_office_reviews_and_another_school_is_invisible():
    with memory_session() as session:
        data = _seed(session)
        submitted = _submit(session, data)

        with pytest.raises(HTTPException) as denied:
            approvals.approve(session, submitted.plan_id, 1, data["owner"])
        assert denied.value.status_code == 403

        _school(session, "AP-0002")
        with pytest.raises(HTTPException) as hidden:
            approvals.approve(session, submitted.plan_id, 1, data["office"])
        assert hidden.value.status_code == 404


def test_a_pending_week_follows_the_subject_to_its_new_teacher():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data, week_no=2, topics="Decimals")

        service.assign_teacher(
            session,
            data["course"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["incoming_employee"].id),
            user=data["office"],
        )

        corrected = _submit(
            session,
            data,
            week_no=2,
            expected_version=1,
            user=data["incoming"],
            topics="Decimals revised",
        )
        assert (corrected.status, corrected.version) == ("Submitted", 2)

        with pytest.raises(HTTPException) as old_holder:
            _submit(
                session,
                data,
                week_no=2,
                expected_version=2,
                user=data["owner"],
            )
        assert old_holder.value.status_code == 403

        approvals.approve(session, corrected.plan_id, 2, data["office"])
        weeks = lesson_plans.month_plan(
            session,
            data["course"].classroom_subject_id,
            date.today().year,
            date.today().month,
            user=data["incoming"],
        )
        week_two = next(week for week in weeks if week.week_no == 2)
        assert week_two.status == PLAN_APPROVED
        assert week_two.can_edit is False
        assert week_two.can_request_change is True
