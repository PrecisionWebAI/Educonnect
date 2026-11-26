"""Phase 8 - Teachers > Course.

Pinned here:

1. the list carries class coverage and every kind of pending approval;
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
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
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

    maths = named_subject("maths")
    english = named_subject("english")
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
        assert len(owner.classes) == 1
        assert len(owner.classes[0].sections) == 1
        # The seed makes the owner class teacher of the first room (section A).
        assert [(c.class_name, c.sections) for c in owner.class_teacher_of] == [
            (owner.classes[0].class_name, ["A"])
        ]
        assert by_id[data["other_employee"].id].class_teacher_of == []

        other = by_id[data["other_employee"].id]
        assert (other.subjects_count, other.sections_count) == (1, 1)
        assert other.pending_approvals == 0

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


def test_pending_counts_a_lesson_plan_a_chapter_list_and_a_proposed_completion():
    with memory_session() as session:
        data = _seed(session)
        _submit(session, data)  # one submitted lesson-plan week

        course = session.get(
            teacher_course.ClassroomSubject, data["maths_course"].classroom_subject_id
        )
        course.chapter_plan_status = "Submitted"  # the chapter list awaits approval
        session.add(course)
        data["chapters"][1].proposed_status = CHAPTER_COMPLETED  # a completion to approve
        session.add(data["chapters"][1])
        session.commit()

        rows = teacher_course.teacher_list(session, data["office"])
        by_id = {row.employee_id: row for row in rows}
        assert by_id[data["owner_employee"].id].pending_approvals == 3
        assert by_id[data["other_employee"].id].pending_approvals == 0


def test_subjects_are_unique_and_sorted_whatever_the_case():
    unique = teacher_course._unique_subjects(
        ["Maths", "science", " maths ", "MATHS", "", None, "English"]
    )
    # Trimmed, lowercase, once each, A-Z.
    assert unique == ["english", "maths", "science"]


def test_the_list_names_each_subject_the_teacher_takes():
    with memory_session() as session:
        data = _seed(session)
        rows = teacher_course.teacher_list(session, data["office"])
        by_id = {row.employee_id: row for row in rows}
        assert by_id[data["owner_employee"].id].subjects == [
            data["maths"].name.strip().lower()
        ]
        assert by_id[data["other_employee"].id].subjects == [
            data["english"].name.strip().lower()
        ]


def test_periods_per_week_count_every_timetable_slot_naming_the_teacher():
    from datetime import time

    from app.domains.academic.classroom.timetable.models import (
        DayOfWeek,
        TimetablePeriod,
    )

    with memory_session() as session:
        data = _seed(session)
        course_id = data["maths_course"].classroom_subject_id
        for day, hour in (
            (DayOfWeek.monday, 9),
            (DayOfWeek.monday, 10),
            (DayOfWeek.tuesday, 9),
        ):
            session.add(
                TimetablePeriod(
                    classroom_id=data["first"].id,
                    classroom_subject_id=course_id,
                    teacher_id=data["owner_employee"].id,
                    day_of_week=day,
                    start_time=time(hour, 0),
                    end_time=time(hour, 45),
                )
            )
        session.commit()

        rows = teacher_course.teacher_list(session, data["office"])
        by_id = {row.employee_id: row for row in rows}
        assert by_id[data["owner_employee"].id].periods_per_week == 3
        assert by_id[data["other_employee"].id].periods_per_week == 0
        assert by_id[data["owner_employee"].id].substitutions_yearly == 0
        # The Load column: periods out of the school's whole week. The default day has 6
        # lessons and only Sunday is off, so a full week is 6 x 6 = 36 periods.
        assert teacher_course._week_capacity(session) == 36
        assert by_id[data["owner_employee"].id].load_percent == round(3 * 100 / 36)  # 8%
        assert by_id[data["owner_employee"].id].load_band == "Light"
        # No periods at all is 0%, not a blank or an error.
        assert by_id[data["other_employee"].id].load_percent == 0
        assert by_id[data["other_employee"].id].load_band == "Light"


def _slot(data: dict, teacher_id, day="monday", hour=9):
    from datetime import time

    from app.domains.academic.classroom.timetable.models import TimetablePeriod

    return TimetablePeriod(
        classroom_id=data["first"].id,
        classroom_subject_id=data["maths_course"].classroom_subject_id,
        teacher_id=teacher_id,
        day_of_week=day,
        start_time=time(hour, 0),
        end_time=time(hour, 45),
    )


def test_the_timetable_leaves_a_trail_when_a_slot_changes_hands():
    from datetime import timedelta

    from app.domains.academic.classroom.timetable.models import (
        TimetablePeriodHistory,
    )

    with memory_session() as session:
        data = _seed(session)
        owner, other = data["owner_employee"].id, data["other_employee"].id
        slot = _slot(data, owner)
        session.add(slot)
        session.commit()

        def ledger():
            return list(session.exec(select(TimetablePeriodHistory)).all())

        # Placed today: one open stretch, for the teacher it names.
        (row,) = ledger()
        assert (row.teacher_id, row.valid_to) == (owner, None)

        # Handed over the same day it was placed: nothing finished a day, so the first
        # stretch is dropped instead of kept as an empty range.
        slot.teacher_id = other
        session.add(slot)
        session.commit()
        (row,) = ledger()
        assert (row.teacher_id, row.valid_to) == (other, None)

        # Held since yesterday, then handed back: the old stretch ends yesterday-1 and
        # the new one starts today.
        row.valid_from = date.today() - timedelta(days=10)
        session.add(row)
        session.commit()
        slot.teacher_id = owner
        session.add(slot)
        session.commit()
        rows = sorted(ledger(), key=lambda item: item.valid_from)
        assert [(item.teacher_id, item.valid_to) for item in rows] == [
            (other, date.today() - timedelta(days=1)),
            (owner, None),
        ]

        # A time-only move (the bell schedule reshaping the day) is not a new stretch.
        slot.start_time = slot.start_time.replace(hour=10)
        session.add(slot)
        session.commit()
        assert len(ledger()) == 2

        # Cleared: the open stretch closes, the record of the past stays.
        session.delete(slot)
        session.commit()
        assert all(item.valid_to is not None for item in ledger())


def test_the_yearly_count_splits_a_mid_session_teacher_change_by_date():
    from datetime import time

    from app.domains.academic.classroom.timetable.history import year_load
    from app.domains.academic.classroom.timetable.models import (
        TimetablePeriodHistory,
    )
    from app.domains.admin.settings import calendar as school_calendar

    with memory_session() as session:
        data = _seed(session)
        first, second = data["owner_employee"].id, data["other_employee"].id
        common = dict(
            period_id=uuid4(),
            classroom_id=data["first"].id,
            classroom_subject_id=data["maths_course"].classroom_subject_id,
            day_of_week="monday",
            start_time=time(9, 0),
            end_time=time(9, 45),
        )
        # `first` takes Monday 9:00 through June, `second` from 1 July on.
        session.add(
            TimetablePeriodHistory(
                teacher_id=first,
                valid_from=date(2026, 6, 1),
                valid_to=date(2026, 6, 30),
                **common,
            )
        )
        session.add(
            TimetablePeriodHistory(
                teacher_id=second, valid_from=date(2026, 7, 1), valid_to=None, **common
            )
        )
        session.commit()

        start, end = date(2026, 6, 1), date(2026, 7, 31)
        loads = year_load(session, [first, second], start, end, slots_per_day=6)

        mondays_june = [
            day
            for day in school_calendar.open_days(session, start, date(2026, 6, 30))
            if day.weekday() == 0
        ]
        mondays_july = [
            day
            for day in school_calendar.open_days(session, date(2026, 7, 1), end)
            if day.weekday() == 0
        ]
        # Each person is credited only with the Mondays they actually held.
        assert loads[first].classes == len(mondays_june) > 0
        assert loads[second].classes == len(mondays_july) > 0
        # Free classes: every open day's 6 lesson slots, less the classes they were in.
        open_days = len(school_calendar.open_days(session, start, end))
        assert loads[first].free == open_days * 6 - loads[first].classes
        assert loads[second].free == open_days * 6 - loads[second].classes


def test_a_cover_moves_the_class_from_the_absent_teacher_to_the_substitute():
    from datetime import time

    from app.domains.academic.classroom.timetable.history import year_load
    from app.domains.academic.classroom.timetable.models import (
        TimetablePeriodHistory,
    )
    from app.domains.admin.settings import calendar as school_calendar

    with memory_session() as session:
        data = _seed(session)
        away, cover = data["owner_employee"].id, data["other_employee"].id
        session.add(
            TimetablePeriodHistory(
                period_id=uuid4(),
                classroom_id=data["first"].id,
                classroom_subject_id=data["maths_course"].classroom_subject_id,
                teacher_id=away,
                day_of_week="monday",
                start_time=time(9, 0),
                end_time=time(9, 45),
                valid_from=date(2026, 6, 1),
                valid_to=None,
            )
        )
        session.commit()

        start, end = date(2026, 6, 1), date(2026, 6, 30)
        open_days = school_calendar.open_days(session, start, end)
        mondays = [day for day in open_days if day.weekday() == 0]
        sunday = next(
            day for day in (start + timedelta(days=n) for n in range(30))
            if day.weekday() == 6
        )
        assert sunday not in open_days, "Sunday is the school's default weekly off"

        loads = year_load(
            session,
            [away, cover],
            start,
            end,
            slots_per_day=6,
            covers=[
                (mondays[0], cover, away),  # away on leave, covered
                (sunday, cover, away),  # school is closed: can never count
            ],
        )
        # The covered Monday is not a class the absent teacher took; it is the cover's.
        assert loads[away].classes == len(mondays) - 1
        assert loads[cover].substitutions == 1
        # Free = open-day slots with neither a class of one's own nor a cover.
        assert loads[cover].free == len(open_days) * 6 - 1
        # The absent teacher's slot was still assigned to them, so it is not "free".
        assert loads[away].free == len(open_days) * 6 - len(mondays)


def test_chapters_per_month_is_judged_on_the_whole_months_that_have_passed():
    with memory_session() as session:
        data = _seed(session)
        owner = data["owner_employee"].id
        today = date.today()
        # The seed's session starts on 1 April 2026. One chapter was finished in June
        # (a whole month ago); the seed already finished another today - this month, which
        # is still running and so is never counted.
        data["chapters"][1].status = CHAPTER_COMPLETED
        data["chapters"][1].completed_on = date(2026, 6, 10)
        data["chapters"][1].completed_by_employee_id = owner
        session.add(data["chapters"][1])
        session.commit()

        months = (today.year - 2026) * 12 + today.month - 4
        rows = teacher_course.teacher_list(session, data["office"])
        by_id = {row.employee_id: row for row in rows}
        mine = by_id[owner]
        assert (mine.chapters_completed, mine.months_counted) == (1, months)
        assert mine.chapters_per_month == round(1 / months, 1)
        # Somebody who completed nothing averages 0, not an error.
        assert by_id[data["other_employee"].id].chapters_per_month == 0.0


def test_classes_group_their_sections_and_sort_by_level():
    from app.domains.academic.classroom.course.teacher_course import (
        _class_coverage,
    )

    low, high = ClassName(classname="Class 2", level=2), ClassName(
        classname="Class 10", level=10
    )
    rooms = {
        (a := uuid4()): (high.level, high.classname, "B"),
        (b := uuid4()): (high.level, high.classname, "A"),
        (c := uuid4()): (low.level, low.classname, "C"),
    }
    grouped = _class_coverage(rooms, set(rooms))
    # Class 2 comes before Class 10, and the sections of one class share a row.
    assert [(g.class_name, g.sections) for g in grouped] == [
        ("Class 2", ["C"]),
        ("Class 10", ["A", "B"]),
    ]
    assert _class_coverage(rooms, set()) == []
    assert {a, b, c} == set(rooms)
