"""Phase 4 - the table's numbers and the teacher timeline.

What is pinned here:

1. **the picker is active teachers** - a leaver and an accountant are not options;
2. **a change is history** - the old row closes the day before the new one opens, and
   the same teacher assigned twice is a no-op;
3. **credit stays with the person who did the work** - the chapter they ticked is still
   theirs after the handover;
4. **the office assigns, an HOD does not** - the server refuses the old
   `classes.assign_teacher` right for this action;
5. **an inactive account cannot be assigned**, and another school's row is a `404`;
6. **the section's completion is chapters done out of all chapters** - one subject at
   2 of 10 and one at 4 of 4 is 6 of 14 = 42.9% (not the subject average, 60%);
7. **the plan summary is this month's counts** - 3 submitted, 2 approved, 1 rejected.
"""

import importlib
from datetime import date, time
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import repository as classroom_repository
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.models import (
    PLAN_APPROVED,
    PLAN_REJECTED,
    PLAN_SUBMITTED,
    LessonPlan,
)
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    CourseTeacherAssignIn,
)
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.permissions_repository import seed_permissions
from app.domains.auth.roles import attach_roles
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.workload.models import StaffWorkloadRule
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


def _school(session: Session, code: str = "TCH-0001") -> School:
    school = School(
        name=f"Teacher School {code}",
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


def _person(
    session: Session,
    role: str,
    code: str,
    *,
    left_on: date | None = None,
) -> tuple[User, Employee]:
    user = User(
        email=f"{uuid4().hex[:10]}@tch.test",
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
        left_on=left_on,
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
    owner, owner_employee = _person(session, "teacher", "EMP-0002")
    incoming, incoming_employee = _person(session, "teacher", "EMP-0003")
    _accountant, accountant_employee = _person(session, "accountant", "EMP-0004")
    _leaver, leaver_employee = _person(
        session, "teacher", "EMP-0005", left_on=date(2025, 12, 31)
    )
    english = named_subject("english")
    maths = named_subject("maths")

    english_row = service.add_subject(
        session,
        room.id,
        AddSectionSubjectIn(name=english.name),
        user=principal,
    )
    maths_row = service.add_subject(
        session,
        room.id,
        AddSectionSubjectIn(name=maths.name),
        user=principal,
    )
    return {
        "school": school,
        "year": year,
        "room": room,
        "principal": principal,
        "principal_employee": principal_employee,
        "owner": owner,
        "owner_employee": owner_employee,
        "incoming": incoming,
        "incoming_employee": incoming_employee,
        "accountant_employee": accountant_employee,
        "leaver_employee": leaver_employee,
        "english": english,
        "maths": maths,
        "english_row": english_row,
        "maths_row": maths_row,
    }


def test_the_teacher_picker_is_active_teaching_staff():
    with memory_session() as session:
        data = _seed(session)

        options = classroom_repository.get_active_teacher_options(session)
        ids = {row[0] for row in options}

        assert data["owner_employee"].id in ids
        assert data["incoming_employee"].id in ids
        assert data["principal_employee"].id in ids, "a principal may teach"
        assert data["accountant_employee"].id not in ids
        assert data["leaver_employee"].id not in ids


def test_a_teacher_change_is_history_and_credit_stays_with_the_doer():
    with memory_session() as session:
        data = _seed(session)
        course_id = data["english_row"].classroom_subject_id

        first = service.assign_teacher(
            session,
            course_id,
            CourseTeacherAssignIn(
                teacher_id=data["owner_employee"].id,
                effective_from=date(2026, 7, 1),
            ),
            user=data["principal"],
        )
        assert first.teacher_id == data["owner_employee"].id
        assert first.warning is None

        # The same teacher, again: no new history row.
        service.assign_teacher(
            session,
            course_id,
            CourseTeacherAssignIn(
                teacher_id=data["owner_employee"].id,
                effective_from=date(2026, 8, 1),
            ),
            user=data["principal"],
        )
        assert (
            len(
                session.exec(
                    select(SubjectTeacher).where(
                        SubjectTeacher.classroom_subject_id
                        == data["english_row"].classroom_subject_id
                    )
                ).all()
            )
            == 1
        )

        chapter = Chapter(
            classroom_subject_id=data["english_row"].classroom_subject_id,
            academic_year_id=data["year"].id,
            sequence=1,
            name="Chapter 1",
            status=CHAPTER_COMPLETED,
            completed_on=date(2026, 9, 1),
            completed_by_employee_id=data["owner_employee"].id,
        )
        session.add(chapter)
        session.commit()

        service.assign_teacher(
            session,
            course_id,
            CourseTeacherAssignIn(
                teacher_id=data["incoming_employee"].id,
                effective_from=date(2026, 10, 1),
            ),
            user=data["principal"],
        )

        timeline = service.teacher_history(session, course_id)
        assert [(row.current, row.completed) for row in timeline] == [
            (False, 1),
            (True, 0),
        ]
        assert timeline[0].effective_to == date(2026, 9, 30)

        rows = session.exec(
            select(SubjectTeacher)
            .where(
                SubjectTeacher.classroom_subject_id
                == data["english_row"].classroom_subject_id
            )
            .order_by(SubjectTeacher.effective_from)
        ).all()
        assert [(row.teacher_id, row.effective_to) for row in rows] == [
            (data["owner_employee"].id, date(2026, 9, 30)),
            (data["incoming_employee"].id, None),
        ]


def test_only_an_active_teacher_with_a_teaching_role_can_be_assigned():
    with memory_session() as session:
        data = _seed(session)
        course_id = data["english_row"].classroom_subject_id

        with pytest.raises(HTTPException) as denied:
            service.assign_teacher(
                session,
                course_id,
                CourseTeacherAssignIn(teacher_id=data["leaver_employee"].id),
                user=data["principal"],
            )
        assert denied.value.status_code == 404

        with pytest.raises(HTTPException) as not_a_teacher:
            service.assign_teacher(
                session,
                course_id,
                CourseTeacherAssignIn(teacher_id=data["accountant_employee"].id),
                user=data["principal"],
            )
        assert not_a_teacher.value.status_code == 409


def test_an_hod_cannot_assign_a_teacher():
    with memory_session() as session:
        data = _seed(session)
        hod, _hod_employee = _person(session, "hod", "EMP-0006")

        with pytest.raises(HTTPException) as denied:
            service.assign_teacher(
                session,
                data["english_row"].classroom_subject_id,
                CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
                user=hod,
            )
        assert denied.value.status_code == 403


def test_a_loaded_teacher_gets_a_warning_but_the_assignment_saves():
    with memory_session() as session:
        data = _seed(session)
        session.add(StaffWorkloadRule(weekly_periods=10, overload_percent=100))
        for hour in range(8, 18):
            session.add(
                TimetablePeriod(
                    classroom_id=data["room"].id,
                    classroom_subject_id=data["english_row"].classroom_subject_id,
                    teacher_id=data["owner_employee"].id,
                    day_of_week=DayOfWeek.monday,
                    start_time=time(hour, 0),
                    end_time=time(hour, 45),
                )
            )
        session.commit()

        result = service.assign_teacher(
            session,
            data["maths_row"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
            user=data["principal"],
        )
        assert result.warning is not None
        assert "10 periods a week" in result.warning
        assert (
            session.exec(
                select(SubjectTeacher).where(
                    SubjectTeacher.classroom_subject_id
                    == data["maths_row"].classroom_subject_id
                )
            ).first()
            is not None
        )


def test_section_completion_is_completed_chapters_out_of_all_chapters():
    with memory_session() as session:
        data = _seed(session)
        for sequence in range(1, 11):
            session.add(
                Chapter(
                    classroom_subject_id=data["english_row"].classroom_subject_id,
                    academic_year_id=data["year"].id,
                    sequence=sequence,
                    name=f"English {sequence}",
                    status=CHAPTER_COMPLETED if sequence <= 2 else "Pending",
                )
            )
        for sequence in range(1, 5):
            session.add(
                Chapter(
                    classroom_subject_id=data["maths_row"].classroom_subject_id,
                    academic_year_id=data["year"].id,
                    sequence=sequence,
                    name=f"Maths {sequence}",
                    status=CHAPTER_COMPLETED,
                )
            )
        session.commit()

        course = service.section_course(
            session, data["room"].id, user=data["principal"]
        )

        # (2 + 4) / (10 + 4) = 42.9% - each subject still shows its own 20% and 100%.
        assert course.completion_percent == 42.9
        assert course.completion_subjects == 2
        assert course.subjects_count == 2
        by_subject = {row.name: row.percent for row in course.subjects}
        assert by_subject == {"english": 20.0, "maths": 100.0}
        assert (
            classroom_repository.get_syllabus_percent(session, data["room"].id) == 42.9
        )


def test_the_row_summarises_this_months_plans():
    with memory_session() as session:
        data = _seed(session)
        today = date.today()
        for week, status in enumerate(
            (PLAN_SUBMITTED, PLAN_APPROVED, PLAN_REJECTED), start=1
        ):
            session.add(
                LessonPlan(
                    classroom_subject_id=data["english_row"].classroom_subject_id,
                    academic_year_id=data["year"].id,
                    year=today.year,
                    month=today.month,
                    week_no=week,
                    start_date=date(today.year, today.month, week),
                    end_date=date(today.year, today.month, week + 4),
                    status=status,
                )
            )
        session.commit()

        course = service.section_course(
            session, data["room"].id, user=data["principal"]
        )
        english = next(row for row in course.subjects if row.name == "english")

        assert english.lesson_plan is not None
        assert (
            english.lesson_plan.submitted,
            english.lesson_plan.approved,
            english.lesson_plan.pending,
            english.lesson_plan.rejected,
        ) == (3, 1, 1, 1)


def test_another_school_cannot_touch_this_sections_subject():
    with memory_session() as session:
        data = _seed(session)
        _school(session, "TCH-0002")

        with pytest.raises(HTTPException) as hidden:
            service.assign_teacher(
                session,
                data["english_row"].classroom_subject_id,
                CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
                user=data["principal"],
            )
        assert hidden.value.status_code == 404
