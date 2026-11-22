"""Phase 1 - the Course schema: section subjects, teacher history, weekly plans.

The conventions every test follows:

* the database is built from `SQLModel.metadata` (the same models the migration
  mirrors), in memory, with the `MODEL_MODULES` registry;
* each scenario gets its **own** session, because a failed commit poisons the next one;
* the assertions are the rules the phase was asked for: one subject row per
  section/session, one **open** teacher row per subject, one plan row per week, one
  history snapshot per version, and a closed set of status words.

The case-insensitive subject name key (`lower(name)`) is created by the migration as a
functional index, which SQLite cannot express the same way; it is exercised by the
PostgreSQL dry-run in Phase 10, and the model-level test here only covers `is_active`.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect
from sqlalchemy.exc import IntegrityError
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
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    PLAN_APPROVED,
    ClassroomSubject,
    LessonPlan,
    LessonPlanHistory,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
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


def seed(session: Session) -> dict:
    """One school, one session, one class-section, one subject, one teacher."""
    school = School(name="Course School", code="CRS-0001", email="office@crs.test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    session.add(year)
    session.commit()
    session.refresh(year)

    klass = ClassName(classname="class 9", level=11)
    section = Section(section_name="a")
    session.add(klass)
    session.add(section)
    session.commit()
    session.refresh(klass)
    session.refresh(section)

    room = Classroom(class_id=klass.class_id, section_id=section.section_id)
    subject = Subject(name="mathematics", code="MATH")
    session.add(room)
    session.add(subject)
    session.commit()
    session.refresh(room)
    session.refresh(subject)

    user = User(
        email=f"{uuid4().hex[:10]}@crs.test",
        full_name="Asha Rao",
        hashed_password="x",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    employee = Employee(
        user_id=user.id,
        employee_code="EMP-0001",
        department="Science",
        joining_date=date(2024, 6, 1),
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)

    return {
        "school": school,
        "year": year,
        "room": room,
        "subject": subject,
        "user": user,
        "employee": employee,
    }


def section_subject(session: Session, data: dict) -> ClassroomSubject:
    row = ClassroomSubject(
        classroom_id=data["room"].id,
        name=data["subject"].name,
        subject_id=data["subject"].id,
        academic_year_id=data["year"].id,
        status=COURSE_ACTIVE,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def week_plan(session: Session, cs: ClassroomSubject, data: dict) -> LessonPlan:
    plan = LessonPlan(
        classroom_subject_id=cs.id,
        academic_year_id=data["year"].id,
        year=2026,
        month=11,
        week_no=1,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 7),
        topics="Fractions",
        learning_objectives="Add unlike fractions.",
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def test_a_subject_can_be_retired_without_losing_its_rows():
    with memory_session() as session:
        data = seed(session)
        subject = data["subject"]
        assert subject.is_active is True

        subject.is_active = False
        session.add(subject)
        session.commit()

        stored = session.get(Subject, subject.id)
        assert stored is not None and stored.is_active is False


def test_one_section_subject_per_session():
    """The same subject cannot be added to a section twice in one session."""
    with memory_session() as session:
        data = seed(session)
        section_subject(session, data)

        with pytest.raises(IntegrityError):
            section_subject(session, data)
        session.rollback()


def test_one_open_teacher_row_per_section_subject():
    """A teacher change closes the old row; two open rows are refused by the database."""
    with memory_session() as session:
        data = seed(session)
        cs = section_subject(session, data)

        first = SubjectTeacher(
            classroom_id=data["room"].id,
            subject_id=data["subject"].id,
            classroom_subject_id=cs.id,
            teacher_id=data["employee"].id,
            academic_year_id=data["year"].id,
            effective_from=date(2026, 6, 1),
        )
        session.add(first)
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(
                SubjectTeacher(
                    classroom_id=data["room"].id,
                    subject_id=data["subject"].id,
                    classroom_subject_id=cs.id,
                    teacher_id=data["employee"].id,
                    academic_year_id=data["year"].id,
                    effective_from=date(2026, 7, 1),
                )
            )
            session.commit()
        session.rollback()

        # Closing the first row is what makes the next assignment legal.
        first.effective_to = date(2026, 6, 30)
        session.add(first)
        session.commit()
        session.add(
            SubjectTeacher(
                classroom_id=data["room"].id,
                subject_id=data["subject"].id,
                classroom_subject_id=cs.id,
                teacher_id=data["employee"].id,
                academic_year_id=data["year"].id,
                effective_from=date(2026, 7, 1),
            )
        )
        session.commit()
        assert len(session.exec(select(SubjectTeacher)).all()) == 2


def test_one_plan_row_per_week():
    with memory_session() as session:
        data = seed(session)
        cs = section_subject(session, data)
        week_plan(session, cs, data)

        with pytest.raises(IntegrityError):
            week_plan(session, cs, data)
        session.rollback()


def test_one_history_snapshot_per_version():
    with memory_session() as session:
        data = seed(session)
        cs = section_subject(session, data)
        plan = week_plan(session, cs, data)

        def snapshot() -> LessonPlanHistory:
            return LessonPlanHistory(
                lesson_plan_id=plan.id,
                version=1,
                start_date=plan.start_date,
                end_date=plan.end_date,
                topics=plan.topics,
                learning_objectives=plan.learning_objectives,
            )

        session.add(snapshot())
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(snapshot())
            session.commit()
        session.rollback()


def test_plan_status_is_a_closed_vocabulary():
    """There is no Draft: a plan row is written by a Submit, reviewed afterwards."""
    with memory_session() as session:
        data = seed(session)
        cs = section_subject(session, data)

        with pytest.raises(IntegrityError):
            session.add(
                LessonPlan(
                    classroom_subject_id=cs.id,
                    academic_year_id=data["year"].id,
                    year=2026,
                    month=11,
                    week_no=2,
                    start_date=date(2026, 11, 8),
                    end_date=date(2026, 11, 14),
                    status="Draft",
                )
            )
            session.commit()
        session.rollback()

        plan = week_plan(session, cs, data)
        plan.status = PLAN_APPROVED
        session.add(plan)
        session.commit()
        assert session.get(LessonPlan, plan.id).status == PLAN_APPROVED


def _unique_names(table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name
    }


def _check_names(table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name
    }


def _index_names(table) -> set[str]:
    return {index.name for index in table.indexes if index.name}


def test_the_tables_carry_the_documented_keys():
    """The model declares the same named keys the migration writes by hand.

    The constraints are read from `SQLModel.metadata` rather than reflected back from
    SQLite: SQLite reports partial indexes differently from PostgreSQL, and the point
    here is the model contract (the migration is exercised by Phase 10's dry-run).
    """
    with memory_session() as session:
        tables = set(inspect(session.get_bind()).get_table_names())
        assert {"classroomsubject", "lessonplan", "lessonplanhistory"} <= tables

        course = ClassroomSubject.__table__
        assert "uq_classroomsubject_section_subject_year" in _unique_names(course)
        assert "ck_classroomsubject_status" in _check_names(course)
        assert "ix_classroomsubject_school_classroom_status" in _index_names(course)

        plan = LessonPlan.__table__
        assert "uq_lessonplan_subject_year_month_week" in _unique_names(plan)
        assert {
            "ck_lessonplan_status",
            "ck_lessonplan_month",
            "ck_lessonplan_week",
            "ck_lessonplan_dates",
            "ck_lessonplan_version",
        } <= _check_names(plan)
        assert {
            "ix_lessonplan_school_status",
            "ix_lessonplan_subject_year_month",
            "ix_lessonplan_school_submitter",
        } <= _index_names(plan)

        history = LessonPlanHistory.__table__
        assert "uq_lessonplanhistory_plan_version" in _unique_names(history)
        assert "ix_lessonplanhistory_school_plan" in _index_names(history)

        teacher = SubjectTeacher.__table__
        assert {
            "uq_subjectteacher_open_cs",
            "uq_subjectteacher_open_legacy",
        } <= _index_names(teacher)
