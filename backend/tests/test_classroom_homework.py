"""Phase 9 - homework: assigned, handed in, graded, and the diary line.

The audit found the loop half-drawn: `homeworksubmission` had no arrival time, no late
flag and no grade, the board printed an empty "Submitted" column, and the class log
never said which subject a line was about. These scenarios pin the finished loop:

1. **assigning tells the section** - each child and their guardians get one message,
   and a second save does not ring the bell twice;
2. **handing in is stamped** - `submitted_at` is set, `is_late` is decided from the due
   date (a moved due date cannot un-late yesterday), and another section's child is
   refused;
3. **grading is the teacher's** - the assignment's teacher, the class teacher or the
   office; a score and a remark land on the row with `graded_at`, and **that** family is
   told - not the whole class;
4. **the board shows the missing** - a child who has not handed anything in appears as a
   row with no submission id, which is what "nothing to grade" means;
5. **the diary names its subject and period**, refuses another room's period, and
   refuses a second line for the same day and period.

Runs under pytest and as `python tests/test_classroom_homework.py`.
"""

import importlib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.homework import service
from app.domains.academic.classroom.homework.models import (
    HomeworkSubmission,
    SubmissionStatus,
)
from app.domains.academic.classroom.homework.schemas import (
    ClassLogCreate,
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
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Permission, Role, RolePermission, UserRole
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee
from tests.course_support import section_subject

TODAY = date(2026, 11, 17)


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


def _office(session: Session, email: str = "office@test") -> User:
    """A login that holds `classes.update` (the office) plus homework permissions."""
    role = _role(session, "school_admin")
    for codename in ("classes.update", "homework.review", "homework.read"):
        _grant(session, role, codename)
    user = _user(session, email)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


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
        phone=f"90{uuid4().int % 100000000:08d}",
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


def _teacher(session: Session, email: str, code: str) -> tuple[Employee, User]:
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
    return employee, user


def seed(session: Session) -> dict:
    """One school: 9-A with two children (one family each), 9-B, Maths."""
    _school(session, "phase nine school", "p9h")
    room = _room(session, "Class 9", "A", 9)
    other = _room(session, "Class 9", "B", 9)
    maths = section_subject(session, room.id, "mathematics", code="MTH")
    other_maths = section_subject(session, other.id, "mathematics", code="MTH")

    employee, teacher_user = _teacher(session, "meera@test", "EMP-P9-1")
    room.class_teacher_id = employee.id
    session.add(room)
    session.add(
        SubjectTeacher(
            classroom_subject_id=maths.id,
            teacher_id=employee.id,
            effective_from=date(2026, 6, 1),
        )
    )
    session.commit()

    aarav = _student(session, "aarav sharma", "P9-1", room)
    kabir = _student(session, "kabir singh", "P9-2", room)
    outsider_child = _student(session, "zoya khan", "P9-3", other)
    aarav_parent = _family(session, aarav, "aarav.parent@test")
    kabir_parent = _family(session, kabir, "kabir.parent@test")
    outsider_parent = _family(session, outsider_child, "zoya.parent@test")

    # A child with their own login, so "the student hears it" is checkable.
    aarav_login = _user(session, "aarav@test")
    aarav.user_id = aarav_login.id
    session.add(aarav)
    session.commit()

    office = _office(session)
    stranger, stranger_user = _teacher(session, "stranger@test", "EMP-P9-9")

    period = TimetablePeriod(
        classroom_id=room.id,
        classroom_subject_id=maths.id,
        teacher_id=employee.id,
        day_of_week=DayOfWeek.tuesday,
        start_time=time(9, 50),
        end_time=time(10, 35),
    )
    session.add(period)
    session.commit()
    session.refresh(period)

    return {
        "room": room,
        "other_room": other,
        "maths": maths,
        "other_maths": other_maths,
        "employee": employee,
        "teacher_user": teacher_user,
        "aarav": aarav,
        "kabir": kabir,
        "outsider_child": outsider_child,
        "aarav_parent": aarav_parent,
        "kabir_parent": kabir_parent,
        "outsider_parent": outsider_parent,
        "aarav_login": aarav_login,
        "office": office,
        "stranger": stranger,
        "stranger_user": stranger_user,
        "period": period,
    }


def _grant(session: Session, role: Role, codename: str) -> None:
    permission = session.exec(
        select(Permission).where(Permission.codename == codename)
    ).first()
    if permission is None:
        permission = Permission(codename=codename, category="Homework", label=codename)
        session.add(permission)
        session.commit()
        session.refresh(permission)
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.commit()


# ---------------------------------------------------------------------------
# Helpers - one place that assigns the homework the scenarios poke at
# ---------------------------------------------------------------------------


def _assign(session, data, *, due=None, title="Trig worksheet"):
    return service.create_homework(
        session,
        HomeworkAssignmentCreate(
            title=title,
            description="Questions 1-10",
            section_id=data["room"].id,
            classroom_subject_id=data["maths"].id,
            teacher_id=data["employee"].id,
            due_date=due or TODAY + timedelta(days=1),
        ),
    )


def _events(session, event: str) -> list[Notification]:
    return list(
        session.exec(select(Notification).where(Notification.event_type == event)).all()
    )


def _submit(session, data, homework_id, student_id, *, when=None):
    return service.submit_homework(
        session,
        SubmissionSubmitIn(homework_id=homework_id, student_id=student_id),
        now=when,
    )


# ---------------------------------------------------------------------------
# 1. Assigning
# ---------------------------------------------------------------------------


def test_assigning_tells_the_section_once():
    session = memory_session()
    data = seed(session)

    homework = _assign(session, data)

    assert homework.section_id == data["room"].id
    assert homework.className.endswith("9-A")
    assert homework.subject == "mathematics"
    assert homework.due == "Tomorrow"
    assert (homework.submitted, homework.total) == (0, 2)

    told = _events(session, service.EVENT_ASSIGNED)
    recipients = {row.user_id for row in told}
    assert data["aarav_login"].id in recipients, "the child with a login hears it"
    assert data["aarav_parent"].id in recipients
    assert data["kabir_parent"].id in recipients
    assert len(told) == 3, "one message per person, not per role"

    # A second pass over the same event does not ring the bell again.
    from app.domains.academic.classroom.homework.models import HomeworkAssignment

    row = session.get(HomeworkAssignment, homework.id)
    assert (
        service._tell_section(
            session,
            row,
            event=service.EVENT_ASSIGNED,
            title="again",
            body="again",
            dedupe_key=service.EVENT_ASSIGNED,
        )
        == 0
    )
    assert len(_events(session, service.EVENT_ASSIGNED)) == 3


# ---------------------------------------------------------------------------
# 2. Handing in
# ---------------------------------------------------------------------------


def test_handing_in_is_stamped_and_a_late_one_stays_late():
    session = memory_session()
    data = seed(session)

    homework = _assign(session, data)
    on_time = _submit(
        session, data, homework.id, data["aarav"].id, when=datetime(2026, 11, 17, 10, 0)
    )
    assert on_time.is_late is False
    assert on_time.status == SubmissionStatus.submitted
    assert on_time.submitted_at == datetime(2026, 11, 17, 10, 0)

    late_homework = _assign(
        session, data, due=TODAY - timedelta(days=2), title="Late one"
    )
    late = _submit(
        session,
        data,
        late_homework.id,
        data["kabir"].id,
        when=datetime(2026, 11, 17, 8, 0),
    )
    assert late.is_late is True, "the due date was two days ago"

    with pytest.raises(HTTPException) as refused:
        _submit(session, data, homework.id, data["outsider_child"].id)
    assert refused.value.status_code == 422
    assert "class-section" in str(refused.value.detail)

    # Handing it in again after it was graded does not un-grade it.
    service.grade_submission(
        session,
        on_time.id,
        SubmissionFeedbackIn(teacher_feedback="Good work"),
        data["teacher_user"],
        now=datetime(2026, 11, 17, 12, 0),
    )
    again = _submit(
        session, data, homework.id, data["aarav"].id, when=datetime(2026, 11, 17, 13, 0)
    )
    assert again.status == SubmissionStatus.graded
    assert again.submitted_at == datetime(2026, 11, 17, 13, 0)
    assert session.get(HomeworkSubmission, on_time.id).teacher_feedback == "Good work"


# ---------------------------------------------------------------------------
# 3. Grading
# ---------------------------------------------------------------------------


def test_grading_belongs_to_the_teacher_and_only_that_family_hears_it():
    session = memory_session()
    data = seed(session)
    homework = _assign(session, data)
    submission = _submit(session, data, homework.id, data["aarav"].id)

    with pytest.raises(HTTPException) as refused:
        service.grade_submission(
            session,
            submission.id,
            SubmissionFeedbackIn(marks_awarded=Decimal("8.5")),
            data["stranger_user"],
        )
    assert refused.value.status_code == 403

    with pytest.raises(HTTPException) as empty:
        service.grade_submission(
            session, submission.id, SubmissionFeedbackIn(), data["teacher_user"]
        )
    assert empty.value.status_code == 422

    with pytest.raises(HTTPException) as negative:
        service.grade_submission(
            session,
            submission.id,
            SubmissionFeedbackIn(marks_awarded=Decimal("-1")),
            data["teacher_user"],
        )
    assert negative.value.status_code == 422

    graded = service.grade_submission(
        session,
        submission.id,
        SubmissionFeedbackIn(
            marks_awarded=Decimal("8.5"), teacher_feedback="Neat work"
        ),
        data["teacher_user"],
        now=datetime(2026, 11, 17, 12, 0, 0),
    )
    assert graded.status == "Graded"
    assert graded.marksAwarded == Decimal("8.50")
    assert graded.feedback == "Neat work"
    assert graded.submittedAt != "", "the row kept its arrival time"

    heard = _events(session, service.EVENT_FEEDBACK)
    recipients = {row.user_id for row in heard}
    assert recipients == {data["aarav_login"].id, data["aarav_parent"].id}
    assert data["kabir_parent"].id not in recipients, "another family is not told"
    assert all(row.kind == "Homework" for row in heard)

    # The same second again: no second bell. A real correction (a later moment) is heard.
    service.grade_submission(
        session,
        submission.id,
        SubmissionFeedbackIn(marks_awarded=Decimal("9")),
        data["teacher_user"],
        now=datetime(2026, 11, 17, 12, 0, 0),
    )
    assert len(_events(session, service.EVENT_FEEDBACK)) == 2

    service.grade_submission(
        session,
        submission.id,
        SubmissionFeedbackIn(marks_awarded=Decimal("9.5")),
        data["office"],
        now=datetime(2026, 11, 17, 12, 5, 0),
    )
    assert len(_events(session, service.EVENT_FEEDBACK)) == 4, (
        "the office may grade too"
    )


# ---------------------------------------------------------------------------
# 4. The board
# ---------------------------------------------------------------------------


def test_the_board_shows_who_has_not_handed_in():
    session = memory_session()
    data = seed(session)
    homework = _assign(session, data)
    _submit(session, data, homework.id, data["aarav"].id)

    rows = service.list_submissions(session, data["room"].id)
    by_student = {row.studentId: row for row in rows}
    assert len(rows) == 2, "one line per child, handed in or not"
    assert by_student[data["aarav"].id].id is not None
    assert by_student[data["aarav"].id].status == "Submitted"
    assert by_student[data["kabir"].id].id is None, "nothing to grade yet"
    assert by_student[data["kabir"].id].status == "Pending"

    board = service.get_homework_by_section(session, data["room"].id)
    assert (board[0].submitted, board[0].total) == (1, 2)


# ---------------------------------------------------------------------------
# 5. The diary
# ---------------------------------------------------------------------------


def test_the_diary_names_its_subject_and_period_and_refuses_a_duplicate():
    session = memory_session()
    data = seed(session)

    log = service.create_class_log(
        session,
        ClassLogCreate(
            section_id=data["room"].id,
            teacher_id=data["employee"].id,
            timetableperiod_id=data["period"].id,
            classroom_subject_id=data["maths"].id,
            date=TODAY,
            note="Trigonometric ratios - exercise 8.2",
        ),
        data["teacher_user"],
    )
    assert log.section_id == data["room"].id
    assert log.classroom_subject_id == data["maths"].id

    diary = service.list_diary(session, data["room"].id)
    assert len(diary) == 1
    assert diary[0].subject == "mathematics"
    assert diary[0].period == "09:50 - 10:35"
    assert diary[0].day == "Tue"
    assert diary[0].date == "2026-11-17"

    with pytest.raises(HTTPException) as duplicate:
        service.create_class_log(
            session,
            ClassLogCreate(
                section_id=data["room"].id,
                teacher_id=data["employee"].id,
                timetableperiod_id=data["period"].id,
                classroom_subject_id=data["maths"].id,
                date=TODAY,
                note="written twice",
            ),
            data["teacher_user"],
        )
    assert duplicate.value.status_code == 409

    # Another room's period cannot be logged from this section.
    from app.domains.academic.classroom.timetable.models import TimetablePeriod

    foreign = TimetablePeriod(
        classroom_id=data["other_room"].id,
        classroom_subject_id=data["other_maths"].id,
        teacher_id=data["stranger"].id,
        day_of_week=DayOfWeek.tuesday,
        start_time=time(9, 50),
        end_time=time(10, 35),
    )
    session.add(foreign)
    session.commit()
    session.refresh(foreign)
    with pytest.raises(HTTPException) as wrong_room:
        service.create_class_log(
            session,
            ClassLogCreate(
                section_id=data["room"].id,
                teacher_id=data["employee"].id,
                timetableperiod_id=foreign.id,
                date=TODAY,
                note="not this room",
            ),
            data["teacher_user"],
        )
    assert wrong_room.value.status_code == 422

    # The day-level line is one per day too (the partial unique index).
    day_level = ClassLogCreate(
        section_id=data["room"].id,
        teacher_id=data["employee"].id,
        date=TODAY + timedelta(days=1),
        note="Revision",
    )
    service.create_class_log(session, day_level, data["teacher_user"])
    with pytest.raises(HTTPException) as twice:
        service.create_class_log(session, day_level, data["teacher_user"])
    assert twice.value.status_code == 409
