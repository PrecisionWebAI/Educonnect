"""Phase 10 - the seams: six flows followed across the modules that own them.

Phases 2-9 each proved their own tab. What none of them could prove is that the tabs
**agree**. Each scenario here starts at one module's write path and ends at another
module's read, on one database:

1. **a register reaches the family** - an absence writes `attendance.absent` once, and
   an approved leave turns the same day into `leave` without touching the teacher's mark;
2. **a chapter survives a teacher change** - the work stays credited to the person who
   did it, the new holder inherits the plan and not the credit, and the old holder is
   refused;
3. **a class test becomes a rank** - marks are saved per paper, published, and the
   results read ranks the cohort without telling a family about anybody else's child;
4. **a school exam is one sitting per class** - the date sheet carries a paper per class,
   and a teacher cannot plan it;
5. **a graded worksheet reaches one family** - `homework.feedback` goes to that child's
   guardians only;
6. **a period is a teacher's week** - assigning it moves `periods_per_week`, deleting it
   moves it back.

Runs under pytest.
"""

import importlib
from tests.exam_helpers import publish
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ClassName,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance import register as register_service
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.attendance.schemas import (
    AttendanceBulkCreate,
    AttendanceRowWrite,
)
from app.domains.academic.classroom.course import service as course_service
from app.domains.academic.classroom.course.schemas import ChapterTickIn
from app.domains.academic.classroom.exams.plan import service as exam_service
from app.domains.academic.classroom.exams.plan.schemas import (
    ExamCreateIn,
    MarkEntryIn,
    MarksSaveIn,
    PaperScheduleIn,
)
from app.domains.academic.classroom.homework import service as homework_service
from app.domains.academic.classroom.homework.schemas import (
    HomeworkAssignmentCreate,
    SubmissionFeedbackIn,
    SubmissionSubmitIn,
)
from app.domains.academic.classroom.students import service as student_service
from app.domains.academic.classroom.students.models import (
    Guardian,
    Student,
    StudentGuardianRelationship,
)
from app.domains.academic.classroom.students.schemas import StudentCreate
from app.domains.academic.classroom.timetable import service as timetable_service
from app.domains.academic.classroom.timetable.models import DayOfWeek
from app.domains.academic.classroom.timetable.schemas import TimetablePeriodCreate
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Permission, Role, RolePermission, UserRole
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import service as teachers_service
from app.domains.people.teachers.workload import repository as workload_repository
from app.domains.services.leave import workflow as leave_workflow
from app.domains.services.leave.schemas import LeaveApplyIn
from tests.course_support import section_subject

#: A fixed Monday, so "yesterday's due date" never depends on when the suite ran.
MON = date(2026, 11, 16)
TUE = MON + timedelta(days=1)


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


def _school(session: Session, name: str, code: str) -> School:
    school = School(name=name, code=code, email=f"{code}@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


def _user(session: Session, email: str) -> User:
    user = User(email=email, full_name=email.split("@")[0], hashed_password="pw")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _role(session: Session, codename: str) -> Role:
    role = session.exec(select(Role).where(Role.codename == codename)).first()
    if role is None:
        role = Role(codename=codename, label=codename.title())
        session.add(role)
        session.commit()
        session.refresh(role)
    return role


def _grant(session: Session, role: Role, codename: str) -> None:
    permission = session.exec(
        select(Permission).where(Permission.codename == codename)
    ).first()
    if permission is None:
        permission = Permission(codename=codename, category="Phase 10", label=codename)
        session.add(permission)
        session.commit()
        session.refresh(permission)
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.commit()


def _office(session: Session) -> User:
    """The office: `classes.update` (every classroom write) plus grading."""
    role = _role(session, "school_admin")
    for codename in (
        "classes.update",
        "homework.review",
        "homework.read",
        "attendance.mark",
        "attendance.read",
    ):
        _grant(session, role, codename)
    user = _user(session, "office@test")
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


def _teacher(session: Session, email: str, code: str) -> tuple[Employee, User]:
    """A login that really sits on the teaching roll (`labels.TEACHING_ROLES`)."""
    user = _user(session, email)
    session.add(UserRole(user_id=user.id, role_id=_role(session, "teacher").id))
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2024, 6, 1),
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee, user


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


def _student(session: Session, name: str, number: str, room) -> Student:
    return student_service.create_student(
        session,
        StudentCreate(
            full_name=name,
            gender="Female",
            admission_number=number,
            classroom_id=room.id,
        ),
    )


def _family(session: Session, student: Student, email: str) -> User:
    parent = _user(session, email)
    guardian = Guardian(
        name=email.split("@")[0],
        phone=f"90{abs(hash(email)) % 100000000:08d}",
        user_id=parent.id,
    )
    session.add(guardian)
    session.commit()
    session.refresh(guardian)
    session.add(
        StudentGuardianRelationship(
            student_id=student.id, guardian_id=guardian.id, is_primary=True
        )
    )
    session.commit()
    return parent


def seed(session: Session) -> dict:
    """One school: 9-A (two children, one family each), 9-B, Maths + Science, ten chapters.

    Meera holds Maths in 9-A (and is its class teacher); Bose takes it over later. The
    chapters belong to the **class**, so both sections share the plan.
    """
    _school(session, "phase ten school", "p10s")
    year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 4, 30),
        is_current=True,
    )
    session.add(year)
    session.commit()
    session.refresh(year)

    room = _room(session, "Class 9", "A", 9)
    other_room = _room(session, "Class 9", "B", 9)

    # Everything names the section's own subject; there is no school-wide one.
    maths_course = section_subject(session, room.id, "mathematics", code="MTH", year=year)
    science_course = section_subject(session, room.id, "science", code="SCI", year=year)

    meera, meera_user = _teacher(session, "meera@test", "EMP-P10-1")
    bose, bose_user = _teacher(session, "bose@test", "EMP-P10-2")
    room.class_teacher_id = meera.id
    session.add(room)
    session.add(
        SubjectTeacher(
            classroom_subject_id=maths_course.id,
            teacher_id=meera.id,
            effective_from=date(2026, 6, 1),
        )
    )
    session.commit()

    aarav = _student(session, "aarav sharma", "P10-1", room)
    kabir = _student(session, "kabir singh", "P10-2", room)
    outsider = _student(session, "zoya khan", "P10-3", other_room)
    aarav_parent = _family(session, aarav, "aarav.parent@test")
    kabir_parent = _family(session, kabir, "kabir.parent@test")
    outsider_parent = _family(session, outsider, "zoya.parent@test")

    chapters = [
        Chapter(
            classroom_subject_id=maths_course.id,
            academic_year_id=year.id,
            sequence=number,
            name=f"chapter {number}",
            planned_date=date(2026, 7, 1) + timedelta(days=7 * (number - 1)),
        )
        for number in range(1, 11)
    ]
    for row in chapters:
        session.add(row)
    session.commit()
    for row in chapters:
        session.refresh(row)

    return {
        "school": session.get(School, session.info["school_id"]),
        "year": year,
        "room": room,
        "other_room": other_room,
        "maths_course": maths_course,
        "science_course": science_course,
        "meera": meera,
        "meera_user": meera_user,
        "bose": bose,
        "bose_user": bose_user,
        "aarav": aarav,
        "kabir": kabir,
        "outsider": outsider,
        "aarav_parent": aarav_parent,
        "kabir_parent": kabir_parent,
        "outsider_parent": outsider_parent,
        "chapters": chapters,
        "office": _office(session),
    }


def _events(session: Session, event: str) -> list[Notification]:
    return list(
        session.exec(select(Notification).where(Notification.event_type == event)).all()
    )


def _recipients(session: Session, event: str) -> set:
    return {row.user_id for row in _events(session, event)}


def _save_register(session: Session, data: dict, marks: dict, *, on_date=MON):
    return register_service.save_register(
        session,
        AttendanceBulkCreate(
            section_id=data["room"].id,
            date=on_date,
            records=[
                AttendanceRowWrite(student_id=student_id, status=status)
                for student_id, status in marks.items()
            ],
        ),
        user=data["office"],
    )


# ---------------------------------------------------------------------------
# 1. The register, the message it sends, and the leave that takes the day back
# ---------------------------------------------------------------------------


def test_an_absence_is_told_once_and_a_leave_takes_the_day_back():
    session = memory_session()
    data = seed(session)

    marks = {data["aarav"].id: "absent", data["kabir"].id: "present"}
    _save_register(session, data, marks)
    assert _recipients(session, "attendance.absent") == {data["aarav_parent"].id}, (
        "the family of the absent child, and nobody else"
    )

    # Saving the same register again is an update, and says nothing new.
    _save_register(session, data, marks)
    assert len(_events(session, "attendance.absent")) == 1

    # The family files a leave; the office approves it.
    request = leave_workflow.apply_leave(
        session,
        LeaveApplyIn(
            student_id=data["aarav"].id,
            leave_type="Medical",
            from_date=MON,
            to_date=TUE,
            reason="Fever",
        ),
        data["aarav_parent"],
    )
    assert request.status == "Pending"
    leave_workflow.decide(session, request.id, action="approve", user=data["office"])

    read = register_service.register(session, data["room"].id, MON)
    row = {line.student_id: line for line in read.rows}[data["aarav"].id]
    assert row.status == "leave", "an approved leave decides the day"
    assert row.leave_request_id == request.id

    # The teacher's mark is history, not a lie: the leave is *derived* over it.
    stored = session.exec(
        select(AttendanceRecord).where(AttendanceRecord.student_id == data["aarav"].id)
    ).one()
    assert str(stored.status) == "absent"

    summary = register_service.section_summary(session, data["room"].id, MON, TUE)
    assert {item.student_id: item for item in summary.rows}[data["aarav"].id].leave == 2


# ---------------------------------------------------------------------------
# 2. A chapter finished before a teacher change stays with that teacher
# ---------------------------------------------------------------------------


def test_a_chapter_finished_before_a_teacher_change_stays_with_that_teacher():
    session = memory_session()
    data = seed(session)

    def tick(chapter, user):
        return course_service.tick_chapter(
            session,
            chapter.id,
            ChapterTickIn(classroom_id=data["room"].id, status=CHAPTER_COMPLETED),
            user,
        )

    tick(data["chapters"][0], data["meera_user"])

    # The change: Meera's row closes on 30 September, Bose opens one on 1 October.
    held = session.exec(
        select(SubjectTeacher).where(SubjectTeacher.teacher_id == data["meera"].id)
    ).one()
    held.effective_to = date(2026, 9, 30)
    session.add(held)
    session.add(
        SubjectTeacher(
            classroom_subject_id=data["maths_course"].id,
            teacher_id=data["bose"].id,
            effective_from=date(2026, 10, 1),
        )
    )
    session.commit()

    course = course_service.section_course(
        session, data["room"].id, user=data["office"]
    )
    maths = course.subjects[0]
    assert maths.percent == 10.0
    by_employee = {row.employee_id: row for row in maths.teachers}
    assert by_employee[data["meera"].id].completed == 1, (
        "the work stays with who did it"
    )
    assert by_employee[data["meera"].id].current is False
    assert by_employee[data["bose"].id].completed == 0
    assert by_employee[data["bose"].id].current is True

    # Bose finishes the second chapter: the credit is his, and Meera's stays at one.
    tick(data["chapters"][1], data["bose_user"])
    course = course_service.section_course(
        session, data["room"].id, user=data["office"]
    )
    maths = course.subjects[0]
    assert maths.percent == 20.0
    by_employee = {row.employee_id: row for row in maths.teachers}
    assert by_employee[data["meera"].id].completed == 1
    assert by_employee[data["bose"].id].completed == 1

    # The person who left cannot tick any more.
    with pytest.raises(HTTPException) as refused:
        tick(data["chapters"][2], data["meera_user"])
    assert refused.value.status_code == 403


# ---------------------------------------------------------------------------
# 3. A class test becomes ranks, and one message per family
# ---------------------------------------------------------------------------


def _paper(course_id=None, *, name=None, class_id=None, maximum="100", on=MON):
    """A date-sheet row: one section subject, or a subject name for every section."""
    return PaperScheduleIn(
        classroom_subject_id=course_id,
        subject_name=name,
        class_id=class_id,
        exam_date=on,
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_marks=Decimal(maximum),
        passing_marks=Decimal("33"),
    )


def _exam(session, data, *, papers, scope="class", status="scheduled", user=None):
    return exam_service.create_exam(
        session,
        ExamCreateIn(
            name="Mid-Term 2026",
            term="Term 1",
            exam_type="Mid term",
            scope=scope,
            classroom_id=data["room"].id if scope == "class" else None,
            class_id=data["room"].class_id if scope == "class" else None,
            academic_year_id=data["year"].id,
            start_date=MON,
            end_date=MON + timedelta(days=5),
            status=status,
            papers=papers,
        ),
        user or data["office"],
    )


def _marks(session, data, paper, rows, user=None):
    return exam_service.save_marks(
        session,
        paper.id,
        MarksSaveIn(
            entries=[
                MarkEntryIn(
                    student_id=student.id,
                    marks_obtained=score,
                    absent=score is None,
                )
                for student, score in rows
            ]
        ),
        user or data["office"],
    )


def test_a_class_test_becomes_ranks_and_one_message_per_family():
    session = memory_session()
    data = seed(session)
    exam = _exam(
        session,
        data,
        papers=[_paper(data["maths_course"].id), _paper(data["science_course"].id)],
    )
    maths = next(
        paper
        for paper in exam.papers
        if paper.classroom_subject_id == data["maths_course"].id
    )
    science = next(
        paper
        for paper in exam.papers
        if paper.classroom_subject_id == data["science_course"].id
    )

    _marks(
        session,
        data,
        maths,
        [(data["aarav"], Decimal("90")), (data["kabir"], Decimal("80"))],
    )
    _marks(
        session,
        data,
        science,
        [(data["aarav"], Decimal("80")), (data["kabir"], Decimal("80"))],
    )

    # Unpublished: the office sees a to-do list, and no family has heard anything.
    board = exam_service.results(session, exam.id, data["office"])
    assert set(board.unpublished) == {maths.id, science.id}
    assert _events(session, "exam.published") == []

    publish(session, maths.id, data["office"])
    publish(session, science.id, data["office"])

    board = exam_service.results(session, exam.id, data["office"])
    assert board.unpublished == []
    ranks = {row.student_id: row.rank for row in board.rows}
    assert ranks[data["aarav"].id] == 1
    assert ranks[data["kabir"].id] == 2
    aarav_row = next(row for row in board.rows if row.student_id == data["aarav"].id)
    assert aarav_row.total == Decimal("170")
    assert aarav_row.out_of == Decimal("200")

    # Both families are told - and only the two that sit the exam.
    assert _recipients(session, "exam.published") >= {
        data["aarav_parent"].id,
        data["kabir_parent"].id,
    }
    assert data["outsider_parent"].id not in _recipients(session, "exam.published")

    own = exam_service.results(session, exam.id, data["aarav_parent"])
    assert own.own_only is True
    assert {row.student_id for row in own.rows} == {data["aarav"].id}


# ---------------------------------------------------------------------------
# 4. A school exam is one sitting per class
# ---------------------------------------------------------------------------


def test_a_school_exam_carries_one_paper_per_class_and_a_teacher_cannot_plan_it():
    session = memory_session()
    data = seed(session)

    with pytest.raises(HTTPException) as refused:
        _exam(
            session,
            data,
            scope="school",
            papers=[_paper(name="mathematics", class_id=data["room"].class_id)],
            user=data["meera_user"],
        )
    assert refused.value.status_code == 403, "planning the whole school is the office's"

    # A school exam is one sitting per **class**, so the second paper needs a class of
    # its own - 9-A and 9-B are two sections of one class and share a `class_id`.
    tenth = _room(session, "Class 10", "A", 10)
    section_subject(session, tenth.id, "mathematics", code="MTH", year=data["year"])
    exam = _exam(
        session,
        data,
        scope="school",
        papers=[
            _paper(name="mathematics", class_id=data["room"].class_id),
            _paper(name="mathematics", class_id=tenth.class_id),
        ],
    )
    assert exam.scope == "school"
    assert {paper.class_id for paper in exam.papers} == {
        data["room"].class_id,
        tenth.class_id,
    }, "one sitting per class, on the day the date sheet names"
    assert all(paper.subject == "mathematics" for paper in exam.papers)
    assert all(paper.exam_date == MON for paper in exam.papers)


# ---------------------------------------------------------------------------
# 5. A graded worksheet reaches one family
# ---------------------------------------------------------------------------


def test_homework_feedback_reaches_that_family_only():
    session = memory_session()
    data = seed(session)

    assignment = homework_service.create_homework(
        session,
        HomeworkAssignmentCreate(
            title="Trig worksheet",
            description="Questions 1-10",
            section_id=data["room"].id,
            classroom_subject_id=data["maths_course"].id,
            teacher_id=data["meera"].id,
            due_date=TUE,
        ),
    )
    assert _recipients(session, "homework.assigned") >= {
        data["aarav_parent"].id,
        data["kabir_parent"].id,
    }

    handed_in = homework_service.submit_homework(
        session,
        SubmissionSubmitIn(homework_id=assignment.id, student_id=data["aarav"].id),
        now=datetime(2026, 11, 16, 18, 0),
    )
    assert handed_in.is_late is False, "an evening before the due date is on time"

    graded = homework_service.grade_submission(
        session,
        handed_in.id,
        SubmissionFeedbackIn(marks_awarded=Decimal("9"), teacher_feedback="Neat work"),
        data["meera_user"],
        now=datetime(2026, 11, 17, 9, 0),
    )
    assert graded.marksAwarded == Decimal("9")

    # The child who handed nothing in hears nothing, and neither does their family.
    assert _recipients(session, "homework.feedback") == {data["aarav_parent"].id}


# ---------------------------------------------------------------------------
# 6. A period is a teacher's week
# ---------------------------------------------------------------------------


def test_assigning_a_period_moves_the_teachers_week():
    session = memory_session()
    data = seed(session)

    before = teachers_service.staff_summary(session)
    assert before.total == 2, "both logins sit on the teaching roll"
    assert before.periods_per_week == 0
    assert before.without_timetable == 2

    period = timetable_service.create_period(
        session,
        TimetablePeriodCreate(
            section_id=data["room"].id,
            classroom_subject_id=data["maths_course"].id,
            teacher_id=data["meera"].id,
            day_of_week=DayOfWeek.monday,
            start_time=time(9, 0),
            end_time=time(9, 45),
        ),
    )

    after = teachers_service.staff_summary(session)
    assert after.periods_per_week == 1, "the Teachers tile counts the timetable"
    assert after.without_timetable == 1
    assert len(workload_repository.week_periods(session, data["meera"].id)) == 1

    timetable_service.delete_period(session, period.id)
    assert teachers_service.staff_summary(session).periods_per_week == 0
