"""Phase 5 - the Course plan: chapters, who teaches them, and who finished what.

The audit found the Course tab had nothing behind it: `syllabusprogress` held two
counters that were empty, and `subjectteacher` overwrote a teacher change so "who taught
this before" was unanswerable. These scenarios pin the replacement:

1. **a teacher change keeps history** - the old row is closed, the new one opened, and
   the bar still credits the work to the person who did it;
2. **the share per teacher is right** - 2 of 10 for the one who left, 0 of 10 for the
   one who arrived, and the section is still 2/10 done;
3. **ticking is a permission, not a screen**: another teacher (or another section's
   teacher) is `403`; the office may;
4. **another school's chapter/section is a `404`** - never a `403` that confirms the id;
5. **unticking clears the credit**, so a chapter cannot be claimed twice;
6. **the completion number is the same one** the Classroom card and the Teachers score
   read (`course.completion`), and "no plan" is `None`, not 0%.

Runs under pytest and as `python tests/test_classroom_course.py`.
"""

import importlib
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import repository as classroom_repository
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    CHAPTER_IN_PROGRESS,
    Chapter,
    ChapterProgress,
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.course import completion, service
from app.domains.academic.classroom.course.schemas import ChapterTickIn
from app.domains.admin.platform.models import School
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Permission, Role, RolePermission, UserRole
from app.domains.people.staff.models import Employee

YEAR_NAME = "2026-27"


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


def _year(session: Session, name: str = YEAR_NAME) -> AcademicYear:
    year = AcademicYear(
        name=name,
        start_date=date(2026, 6, 1),
        end_date=date(2027, 4, 30),
        is_current=True,
    )
    session.add(year)
    session.commit()
    session.refresh(year)
    return year


def _rooms(session: Session, letters: str = "AB") -> list[Classroom]:
    klass = session.exec(
        select(ClassName).where(ClassName.classname == "Class 9")
    ).first()
    if klass is None:
        klass = ClassName(classname="Class 9", level=9)
        session.add(klass)
        session.commit()
        session.refresh(klass)

    rooms: list[Classroom] = []
    for letter in letters:
        section = session.exec(
            select(Section).where(Section.section_name == letter)
        ).first()
        if section is None:
            section = Section(section_name=letter)
            session.add(section)
            session.commit()
            session.refresh(section)
        rooms.append(ensure_room(session, klass.class_id, section.section_id))
    return rooms


def _subject(session: Session, name: str, code: str) -> Subject:
    subject = Subject(name=name, code=code)
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def _teacher(session: Session, email: str, code: str) -> Employee:
    user = User(email=email, full_name=email.split("@")[0], hashed_password="pw")
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
    return employee


def _office(session: Session) -> User:
    """The office: a login that really holds `classes.update` (role + grant rows).

    Seeded rather than faked: `AuthorizationService.has_permission` reads
    `rolepermission` when it has a session, so a test that wants the office to pass must
    grant the right the way the seed does.
    """
    role = session.exec(select(Role).where(Role.codename == "school_admin")).first()
    if role is None:
        role = Role(codename="school_admin", label="School Admin")
        session.add(role)
        session.commit()
        session.refresh(role)
    permission = session.exec(
        select(Permission).where(Permission.codename == "classes.update")
    ).first()
    if permission is None:
        permission = Permission(
            codename="classes.update", category="Classes", label="Update Classes"
        )
        session.add(permission)
        session.commit()
        session.refresh(permission)
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    user = User(email="office@test", full_name="Office", hashed_password="pw")
    user._role_names = {"school_admin"}
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


def _chapters(
    session: Session, klass_id, subject: Subject, count: int = 10
) -> list[Chapter]:
    year = session.exec(
        select(AcademicYear).where(AcademicYear.name == YEAR_NAME)
    ).first()
    rows = [
        Chapter(
            class_id=klass_id,
            subject_id=subject.id,
            academic_year_id=year.id,
            sequence=number,
            name=f"Chapter {number}",
            planned_date=date(2026, 7, 1) + timedelta(days=7 * (number - 1)),
        )
        for number in range(1, count + 1)
    ]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def seed(session: Session) -> dict:
    """One school, Class 9-A and 9-B, Mathematics with ten chapters, two teachers."""
    school = _school(session, "phase five school", "p5s")
    year = _year(session)
    first, second = _rooms(session)
    maths = _subject(session, "Mathematics", "MATH")
    outgoing = _teacher(session, "ansari@test", "EMP-P5-1")
    incoming = _teacher(session, "bose@test", "EMP-P5-2")
    outsider = _teacher(session, "chandra@test", "EMP-P5-3")
    chapters = _chapters(session, first.class_id, maths)
    office = _office(session)

    # The teacher change: Ansari taught until 2026-09-30, Bose from 2026-10-01.
    session.add(
        SubjectTeacher(
            classroom_id=first.id,
            subject_id=maths.id,
            teacher_id=outgoing.id,
            academic_year_id=year.id,
            effective_from=date(2026, 6, 1),
            effective_to=date(2026, 9, 30),
        )
    )
    session.add(
        SubjectTeacher(
            classroom_id=first.id,
            subject_id=maths.id,
            teacher_id=incoming.id,
            academic_year_id=year.id,
            effective_from=date(2026, 10, 1),
        )
    )
    session.commit()

    return {
        "school": school,
        "year": year,
        "first": first,
        "second": second,
        "maths": maths,
        "chapters": chapters,
        "outgoing": outgoing,
        "incoming": incoming,
        "outsider": outsider,
        "office": office,
    }


def _tick(session, data, chapter, status, user) -> object:
    return service.tick_chapter(
        session,
        chapter.id,
        ChapterTickIn(classroom_id=data["first"].id, status=status),
        user=user,
    )


def _login(session: Session, employee: Employee) -> User:
    """The login behind an employee - `tick_chapter` takes the caller, not the row."""
    return session.get(User, employee.user_id)


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_a_teacher_change_keeps_history(session: Session) -> None:
    """The timeline survives and the bar credits the person who did the work."""
    data = seed(session)

    # Two chapters were finished while the first teacher still held the subject: the
    # rows exist, so the change is history rather than a rewrite.
    for chapter in data["chapters"][:2]:
        session.add(
            ChapterProgress(
                chapter_id=chapter.id,
                classroom_id=data["first"].id,
                status=CHAPTER_COMPLETED,
                completed_on=date(2026, 9, 10),
                completed_by_employee_id=data["outgoing"].id,
            )
        )
    session.commit()

    course = service.section_course(session, data["first"].id, user=data["office"])
    subject = course.subjects[0]

    assert subject.current_teacher == "bose", "the person holding it today"
    assert subject.current_teacher_id == data["incoming"].id
    assert len(subject.teachers) == 2, "both rows survive the change"
    leaver, arrival = subject.teachers
    assert (leaver.effective_to, leaver.current) == (date(2026, 9, 30), False)
    assert (arrival.effective_to, arrival.current) == (None, True)
    assert (leaver.completed, arrival.completed) == (2, 0), (
        "the work stays with whoever finished it"
    )
    assert (subject.done, subject.total) == (2, 10)
    assert subject.percent == 20.0
    assert subject.next_chapter == "Ch 3 · Chapter 3"

    # The person holding it now ticks the next one: allowed, and credited to them.
    ticked = _tick(
        session,
        data,
        data["chapters"][2],
        CHAPTER_COMPLETED,
        _login(session, data["incoming"]),
    )
    assert ticked.status == CHAPTER_COMPLETED
    assert ticked.completed_on == date.today()
    assert ticked.completed_by_employee_id == data["incoming"].id

    after = service.section_course(
        session, data["first"].id, user=data["office"]
    ).subjects[0]
    assert (after.done, after.total, after.percent) == (3, 10, 30.0)
    assert [row.completed for row in after.teachers] == [2, 1]


def check_only_the_owner_or_the_office_may_tick(session: Session) -> None:
    """`classes.read` opens the tab; the write needs the subject (or the office)."""
    data = seed(session)
    chapter = data["chapters"][0]

    for who in (data["outsider"], data["outgoing"]):
        # A teacher of another subject, and the teacher who handed this one over.
        with pytest.raises(HTTPException) as refused:
            _tick(session, data, chapter, CHAPTER_IN_PROGRESS, _login(session, who))
        assert refused.value.status_code == 403

    ticked = _tick(session, data, chapter, CHAPTER_IN_PROGRESS, data["office"])
    assert ticked.status == CHAPTER_IN_PROGRESS
    # "In progress" is not "done": the count must not move.
    assert completion.for_subject(session, data["first"].id, data["maths"].id) == (
        0,
        10,
    )


def check_another_school_is_a_404(session: Session) -> None:
    """School B's chapter and section are invisible (404), never "forbidden"."""
    data = seed(session)

    _school(session, "other school", "p5o")
    _year(session)
    their_room = _rooms(session, "A")[0]
    their_subject = _subject(session, "Mathematics", "MATH")
    their_chapter = _chapters(session, their_room.class_id, their_subject, count=1)[0]

    session.info["school_id"] = data["school"].id

    with pytest.raises(HTTPException) as missing_section:
        service.section_course(session, their_room.id, user=data["office"])
    assert missing_section.value.status_code == 404

    with pytest.raises(HTTPException) as missing_chapter:
        service.tick_chapter(
            session,
            their_chapter.id,
            ChapterTickIn(classroom_id=data["first"].id, status=CHAPTER_COMPLETED),
            user=data["office"],
        )
    assert missing_chapter.value.status_code == 404

    with pytest.raises(HTTPException) as missing_room:
        service.tick_chapter(
            session,
            data["chapters"][0].id,
            ChapterTickIn(classroom_id=their_room.id, status=CHAPTER_COMPLETED),
            user=data["office"],
        )
    assert missing_room.value.status_code == 404


def check_unticking_clears_the_credit(session: Session) -> None:
    """Taking a chapter back drops the date and the name, so it cannot be claimed twice."""
    data = seed(session)
    bose = _login(session, data["incoming"])
    subject_of = (data["first"].id, data["maths"].id)

    _tick(session, data, data["chapters"][0], CHAPTER_COMPLETED, bose)
    assert completion.for_subject(session, *subject_of) == (1, 10)

    unticked = _tick(session, data, data["chapters"][0], CHAPTER_IN_PROGRESS, bose)
    assert unticked.status == CHAPTER_IN_PROGRESS
    assert unticked.completed_on is None
    assert unticked.completed_by_employee_id is None
    assert completion.for_subject(session, *subject_of) == (0, 10)

    course = service.section_course(session, data["first"].id, user=data["office"])
    assert [row.completed for row in course.subjects[0].teachers] == [0, 0]


def check_one_completion_number_everywhere(session: Session) -> None:
    """The card, the tab and the Teachers score read the same calculation."""
    from app.domains.people.teachers.appraisal import performance

    data = seed(session)
    bose = _login(session, data["incoming"])
    _tick(session, data, data["chapters"][0], CHAPTER_COMPLETED, bose)
    _tick(session, data, data["chapters"][1], CHAPTER_COMPLETED, bose)

    tab = service.section_course(session, data["first"].id, user=data["office"])
    assert tab.subjects[0].percent == 20.0

    # The Classroom card (same section, one number).
    assert classroom_repository.get_syllabus_percent(session, data["first"].id) == 20.0
    cards = classroom_repository.get_syllabus_per_section(session)
    assert cards[data["first"].id] == (20.0, 1), "percent and subjects tracked"
    assert cards[data["second"].id] == (0.0, 1), "9-B has the plan, nothing done"

    # The Teachers performance component (0-100, "no data" when there is no plan).
    covered = performance._syllabus(
        session, [data["incoming"].id, data["outgoing"].id, data["outsider"].id]
    )
    assert covered[data["incoming"].id] == 20
    assert data["outgoing"].id not in covered, "no subject held today, no figure"
    assert data["outsider"].id not in covered

    # A section with no chapter plan reports "no plan", not 0%.
    assert completion.for_section(session, data["second"].id) == (0, 10), (
        "9-B shares the class's plan and has done nothing"
    )
    assert completion.for_section(session, uuid4()) is None, "no plan is not 0%"


# ---------------------------------------------------------------------------
# pytest wrappers + the no-pytest runner
# ---------------------------------------------------------------------------


def test_a_teacher_change_keeps_history():
    with memory_session() as session:
        check_a_teacher_change_keeps_history(session)


def test_only_the_owner_or_the_office_may_tick():
    with memory_session() as session:
        check_only_the_owner_or_the_office_may_tick(session)


def test_another_school_is_a_404():
    with memory_session() as session:
        check_another_school_is_a_404(session)


def test_unticking_clears_the_credit():
    with memory_session() as session:
        check_unticking_clears_the_credit(session)


def test_one_completion_number_everywhere():
    with memory_session() as session:
        check_one_completion_number_everywhere(session)


SCENARIOS = (
    ("a teacher change keeps history", check_a_teacher_change_keeps_history),
    (
        "only the owner or the office may tick",
        check_only_the_owner_or_the_office_may_tick,
    ),
    ("another school is a 404", check_another_school_is_a_404),
    ("unticking clears the credit", check_unticking_clears_the_credit),
    ("one completion number everywhere", check_one_completion_number_everywhere),
)


if __name__ == "__main__":  # pragma: no cover - the no-pytest runner
    for label, scenario in SCENARIOS:
        with memory_session() as run_session:
            scenario(run_session)
        print(f"ok  {label}")
