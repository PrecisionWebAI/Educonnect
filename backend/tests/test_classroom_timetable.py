"""Phase 9 - the timetable: two clashes refused by name, and the school's own day.

The audit found the grid drawing six hardcoded periods and the API accepting "Maths and
Science, both 09:00 Monday, both 9-A". These scenarios pin the replacement:

1. **a teacher cannot be in two rooms** at the same hour - `409`, and the sentence names
   the teacher and where they already are;
2. **a class cannot hold two subjects** in one slot - `409`, naming the class and the
   subject already there;
3. **moving a period is not a clash with itself**, and moving it onto someone else's
   slot is;
4. **the bell schedule is the school's** - seeded once on first read, labelled P1..Pn
   with the breaks in their place, and a second read does not seed again;
5. **the teacher's week follows the timetable** - assigning a period adds one, clearing
   it takes one back.

Runs under pytest and as `python tests/test_classroom_timetable.py`.
"""

import importlib
from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.timetable import service
from app.domains.academic.classroom.timetable.models import BellSchedule, DayOfWeek
from app.domains.academic.classroom.timetable.schemas import TimetablePeriodCreate
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.workload import repository as workload_repository
from tests.course_support import ensure_year, section_subject


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


def _user(session: Session, email: str) -> User:
    user = User(email=email, full_name=email.split("@")[0], hashed_password="pw")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _teacher(session: Session, email: str, code: str) -> Employee:
    user = _user(session, email)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2024, 6, 1),
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _room(session: Session, class_name: str, section_name: str, level: int):
    klass = session.exec(
        select(ClassName).where(ClassName.classname == class_name)
    ).first()
    if klass is None:
        klass = ClassName(classname=class_name, level=level)
        session.add(klass)
        session.commit()
        session.refresh(klass)
    letter = session.exec(
        select(Section).where(Section.section_name == section_name)
    ).first()
    if letter is None:
        letter = Section(section_name=section_name)
        session.add(letter)
        session.commit()
        session.refresh(letter)
    return ensure_room(session, klass.class_id, letter.section_id)


def seed(session: Session) -> dict:
    """One school: 9-A and 9-B, Maths + Science, two teachers."""
    school = School(name="phase nine timetable", code="p9t", email="p9t@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    room = _room(session, "Class 9", "A", 9)
    other_room = _room(session, "Class 9", "B", 9)
    maths = section_subject(session, room.id, "mathematics", code="MTH")
    science = section_subject(session, room.id, "science", code="SCI")
    # The other section has its own copies - a subject is never shared between rooms.
    courses = {
        (room.id, "mathematics"): maths,
        (room.id, "science"): science,
        (other_room.id, "mathematics"): section_subject(
            session, other_room.id, "mathematics", code="MTH"
        ),
        (other_room.id, "science"): section_subject(
            session, other_room.id, "science", code="SCI"
        ),
    }

    meera = _teacher(session, "meera@test", "EMP-P9T-1")
    bose = _teacher(session, "bose@test", "EMP-P9T-2")

    return {
        "room": room,
        "other_room": other_room,
        "maths": maths,
        "science": science,
        "courses": courses,
        "meera": meera,
        "bose": bose,
    }


def _slot(
    data, *, room=None, teacher=None, subject=None, day=DayOfWeek.monday, start=9
):
    room = room or data["room"]
    name = (subject or data["maths"]).name
    return TimetablePeriodCreate(
        section_id=room.id,
        classroom_subject_id=data["courses"][(room.id, name)].id,
        teacher_id=(teacher or data["meera"]).id,
        day_of_week=day,
        start_time=time(start, 0),
        end_time=time(start + 1, 0),
    )


def test_each_academic_year_has_its_own_week():
    """The same slot may run in 2026-27 and again in 2027-28; reads see one year."""
    session = memory_session()
    data = seed(session)
    school_id = session.info["school_id"]
    first_year = ensure_year(session)  # the seed already opened 2026-27
    second_year = AcademicYear(
        name="2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
        school_id=school_id,
    )
    session.add(second_year)
    session.commit()

    first = service.create_period(session, _slot(data))
    assert first.academic_year_id == first_year.id

    first_year.is_current = False
    session.add(first_year)
    session.commit()
    second_year.is_current = True
    session.add(second_year)
    session.commit()

    second = service.create_period(session, _slot(data, subject=data["science"]))
    assert second.academic_year_id == second_year.id

    rows = service.get_timetable_by_class(
        session, data["room"].class_id, data["room"].id
    )
    assert [row.academic_year_id for row in rows] == [second_year.id]

    historic = service.get_timetable_by_class(
        session,
        data["room"].class_id,
        data["room"].id,
        academic_year_id=first_year.id,
    )
    assert [row.academic_year_id for row in historic] == [first_year.id]
    with pytest.raises(HTTPException) as read_only:
        service.update_period(session, first.id, _slot(data))
    assert read_only.value.status_code == 409


def test_a_teacher_cannot_be_in_two_rooms_at_once():
    session = memory_session()
    data = seed(session)

    first = service.create_period(session, _slot(data))
    assert first.section_id == data["room"].id

    with pytest.raises(HTTPException) as refused:
        service.create_period(
            session, _slot(data, room=data["other_room"], subject=data["science"])
        )
    assert refused.value.status_code == 409
    detail = str(refused.value.detail)
    assert "meera" in detail.lower(), "the sentence names the teacher"
    assert "09:00" in detail and "Monday" in detail


def test_a_class_cannot_hold_two_subjects_in_one_slot():
    session = memory_session()
    data = seed(session)
    service.create_period(session, _slot(data))

    with pytest.raises(HTTPException) as refused:
        service.create_period(
            session, _slot(data, subject=data["science"], teacher=data["bose"])
        )
    assert refused.value.status_code == 409
    detail = str(refused.value.detail)
    assert "9-A" in detail, "the sentence names the class-section"
    assert "mathem" in detail.lower(), "and the subject already sitting there"


def test_moving_a_period_is_not_a_clash_with_itself():
    session = memory_session()
    data = seed(session)
    period = service.create_period(session, _slot(data))

    # Saved unchanged: no clash with its own row.
    same = service.update_period(session, period.id, _slot(data))
    assert same.start_time == time(9, 0)

    # Moved to a free hour: fine.
    moved = service.update_period(
        session, period.id, _slot(data, day=DayOfWeek.tuesday, start=11)
    )
    assert moved.day_of_week == DayOfWeek.tuesday

    # Someone else's slot now: refused, and the refusal names that room.
    service.create_period(
        session,
        _slot(
            data,
            room=data["other_room"],
            day=DayOfWeek.tuesday,
            start=11,
            teacher=data["bose"],
            subject=data["science"],
        ),
    )
    with pytest.raises(HTTPException) as refused:
        service.update_period(
            session,
            moved.id,
            _slot(data, day=DayOfWeek.tuesday, start=11, room=data["other_room"]),
        )
    assert refused.value.status_code == 409
    assert "9-B" in str(refused.value.detail)


def test_the_bell_schedule_is_seeded_once_and_labels_its_periods():
    session = memory_session()
    seed(session)

    first = service.bell_schedule(session)
    assert [slot.label for slot in first] == [
        "P1",
        "P2",
        "Break",
        "P3",
        "P4",
        "Break",
        "P5",
        "P6",
    ], "six teaching periods with the two breaks where they belong"
    assert [slot.period_no for slot in first] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert first[2].is_break is True
    assert first[0].start_time == time(8, 0) and first[0].end_time == time(8, 45)

    again = service.bell_schedule(session)
    assert len(again) == len(first)
    assert len(session.exec(select(BellSchedule)).all()) == 8, (
        "a second read seeds nothing"
    )

    # The school's own rows win over the default: this day starts at 7:30.
    for row in session.exec(select(BellSchedule)).all():
        session.delete(row)
    session.commit()
    session.add(
        BellSchedule(
            period_no=1,
            start_time=time(7, 30),
            end_time=time(8, 15),
            is_break=False,
        )
    )
    session.commit()
    own = service.bell_schedule(session)
    assert len(own) == 1
    assert own[0].start_time == time(7, 30)
    assert own[0].label == "P1"


def test_assigning_a_period_changes_the_teacher_week_by_one():
    session = memory_session()
    data = seed(session)

    assert workload_repository.week_periods(session, data["meera"].id) == []

    period = service.create_period(session, _slot(data))
    assert len(workload_repository.week_periods(session, data["meera"].id)) == 1

    service.delete_period(session, period.id)
    assert workload_repository.week_periods(session, data["meera"].id) == []


def test_saving_the_period_setup_moves_every_placed_period():
    from app.domains.academic.classroom.timetable.schemas import (
        BellScheduleWrite,
        BreakWrite,
    )

    session = memory_session()
    data = seed(session)
    service.bell_schedule(session)  # default day: P1 08:00, P2 08:45 ...
    service.create_period(session=session, period_in=_slot(data, start=8))

    out = service.set_bell_schedule(
        session,
        BellScheduleWrite(
            periods=3,
            breaks=[BreakWrite(after_period=1, minutes=15)],
            start_time=time(9, 0),
            period_minutes=40,
        ),
    )
    assert [s.label for s in out] == ["P1", "Break", "P2", "P3"]
    moved = service.get_timetable_by_class(
        session=session,
        class_id=data["room"].class_id,
        section_id=data["room"].id,
    )
    assert moved[0].start_time == time(9, 0)
    assert moved[0].end_time == time(9, 40)
