"""Promotion keeps history instead of overwriting last year's class."""

import importlib
from datetime import date
from types import SimpleNamespace

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
from app.domains.academic.classroom.students.models import Enrollment, Student
from app.domains.academic.classroom.students.promotion import service
from app.domains.academic.classroom.students.promotion.schemas import (
    ClassTeacherAssignmentWrite,
    PromotionBatchCreate,
    PromotionDecisionWrite,
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
    return Session(engine, expire_on_commit=False)


@pytest.fixture()
def world():
    session = memory_session()
    school = School(name="Promotion School", code="promo", email="promo@test")
    session.add(school)
    session.add(ClassName(classname="Class 1", level=1))
    session.add(ClassName(classname="Class 2", level=2))
    session.add(Section(section_name="A"))
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    class_one, class_two = session.exec(select(ClassName)).all()
    section = session.exec(select(Section)).first()
    room_one = Classroom(
        class_id=class_one.class_id, section_id=section.section_id, school_id=school.id
    )
    room_two = Classroom(
        class_id=class_two.class_id, section_id=section.section_id, school_id=school.id
    )
    from_year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
        school_id=school.id,
    )
    to_year = AcademicYear(
        name="2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
        school_id=school.id,
    )
    session.add(room_one)
    session.add(room_two)
    session.add(from_year)
    session.add(to_year)
    session.commit()
    for row in (room_one, room_two, from_year, to_year):
        session.refresh(row)

    student = Student(
        full_name="Aarav Test",
        admission_number="ADM-2026-0001",
        classroom_id=room_one.id,
        school_id=school.id,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    source = Enrollment(
        student_id=student.id,
        classroom_id=room_one.id,
        academic_year_id=from_year.id,
        school_id=school.id,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    teachers = []
    for number in (1, 2):
        user = User(
            email=f"teacher{number}@promo.test",
            full_name=f"Teacher {number}",
            hashed_password="x",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        employee = Employee(
            user_id=user.id,
            employee_code=f"EMP-{number}",
            department="academic",
            joining_date=date(2026, 4, 1),
            school_id=school.id,
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)
        teachers.append(employee)

    return SimpleNamespace(
        session=session,
        school=school,
        room_one=room_one,
        room_two=room_two,
        from_year=from_year,
        to_year=to_year,
        student=student,
        source=source,
        teachers=teachers,
    )


def test_promotion_creates_a_linked_enrollment_and_closes_the_old_one(world):
    batch = service.create_batch(
        world.session,
        PromotionBatchCreate(
            from_academic_year_id=world.from_year.id,
            to_academic_year_id=world.to_year.id,
        ),
        None,
    )
    service.put_decisions(
        world.session,
        batch.id,
        [
            PromotionDecisionWrite(
                student_id=world.student.id,
                decision="promote",
                to_classroom_id=world.room_two.id,
            )
        ],
        None,
    )

    applied = service.apply_batch(world.session, batch.id, None)

    assert applied.status == "applied"
    assert applied.decisions[0].to_enrollment_id is not None
    next_row = world.session.get(
        Enrollment, applied.decisions[0].to_enrollment_id
    )
    assert next_row.academic_year_id == world.to_year.id
    assert next_row.classroom_id == world.room_two.id
    assert next_row.previous_enrollment_id == world.source.id
    assert world.session.get(Enrollment, world.source.id).status == "promoted"


def test_a_bad_decision_is_refused_before_anything_is_written(world):
    batch = service.create_batch(
        world.session,
        PromotionBatchCreate(
            from_academic_year_id=world.from_year.id,
            to_academic_year_id=world.to_year.id,
        ),
        None,
    )

    with pytest.raises(HTTPException) as refused:
        service.put_decisions(
            world.session,
            batch.id,
            [
                PromotionDecisionWrite(
                    student_id=world.student.id,
                    decision="promote",
                    to_classroom_id=None,
                )
            ],
            None,
        )

    assert refused.value.status_code == 422
    assert world.session.exec(select(Enrollment)).all() == [world.source]


def test_a_second_class_teacher_closes_the_open_assignment(world):
    first = service.assign_class_teacher(
        world.session,
        ClassTeacherAssignmentWrite(
            classroom_id=world.room_one.id,
            academic_year_id=world.from_year.id,
            teacher_id=world.teachers[0].id,
        ),
        None,
    )
    second = service.assign_class_teacher(
        world.session,
        ClassTeacherAssignmentWrite(
            classroom_id=world.room_one.id,
            academic_year_id=world.from_year.id,
            teacher_id=world.teachers[1].id,
        ),
        None,
    )

    rows = service.list_class_teachers(world.session, world.from_year.id)
    assert {row.teacher_id for row in rows} == {
        world.teachers[0].id,
        world.teachers[1].id,
    }
    open_rows = [row for row in rows if row.effective_to is None]
    assert len(open_rows) == 1
    assert open_rows[0].teacher_id == world.teachers[1].id
    assert second.teacher_id == world.teachers[1].id
    assert first.id != second.id
    world.session.refresh(world.room_one)
    assert world.room_one.class_teacher_id == world.teachers[1].id
