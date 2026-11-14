"""The cover board: who is away, who can stand in, and the three writes.

Every test here is a sentence somebody would otherwise have to take on trust:

* the board is **derived** - opening it writes nothing, and a leave cancelled at
  08:05 removes the ask;
* a colleague who does not teach the subject is never offered, and one who is on
  leave or already in another room is offered **with the reason they cannot**;
* the same department and the same class-section come first, and the lighter
  timetable decides the rest;
* one adult per room (`UNIQUE(school, period, date)`) answers `409`, not a second
  assignment and not a 500;
* approving twice changes nothing and writes no second audit line, and a withdrawn
  cover **frees** the slot for somebody else.

Runs on in-memory SQLite, like the rest of this module's suite.
"""

import importlib
from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
)
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers.models import StaffAuditLog, TeacherSubject
from app.domains.people.teachers.substitution import service
from app.domains.people.teachers.substitution.models import (
    SubstitutionAssignment,
    SubstitutionRequest,
)
from app.domains.people.teachers.substitution.schemas import SubstitutionAssignIn
from app.domains.services.leave.models import LeaveRequest

#: A Monday - the timetable is a weekday, and the board asks for a date.
DAY = date(2026, 11, 9)


def engine():
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


def session_for(created, school_id=None):
    session = Session(created, expire_on_commit=False)
    if school_id is not None:
        session.info["school_id"] = school_id
    return session


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("hod", "Head of Department"),
        ("teacher", "Teacher"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _user(session: Session, name: str, school_id, roles: tuple[str, ...]) -> User:
    user = User(
        email=f"{name.lower().replace(' ', '.')}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for codename in roles:
        grant_role(session, user, codename)
    return user


def _person(
    session: Session,
    school_id,
    code: str,
    *,
    name=None,
    roles=("teacher",),
    department="Science",
) -> tuple[User, Employee]:
    user = _user(session, name or f"Staff {code}", school_id, roles)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=department,
        joining_date=date(2023, 6, 1),
        email=f"{code.lower()}@test",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


def _school(session: Session, name: str = "Test School", code: str = "SUB-0001"):
    school = School(
        name=name,
        code=code,
        email=f"office@{code.lower()}.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


@pytest.fixture()
def seeded():
    """One Monday: one absent Physics teacher, three who could stand in, one clash.

    * **Teacher One** teaches Physics and is on approved Sick leave on `DAY` - the
      absence the board is about;
    * **Teacher Two** teaches Physics in the same department and is free;
    * **Teacher Three** teaches Physics in Maths - free, but a different department;
    * **Teacher Four** teaches Physics and has 09:00 in another room, so the first
      period is a clash for them and the second is not;
    * **Teacher Five** teaches Maths only - never a candidate for a Physics period;
    * **Hod One** is a head of department (Science) and teaches Physics.
    """
    session = session_for(engine())
    _roles(session)
    school = _school(session)
    session.info["school_id"] = school.id

    principal = _user(session, "Principal One", school.id, ("principal",))
    one_user, one = _person(session, school.id, "EMP-0001", name="Teacher One")
    two_user, two = _person(session, school.id, "EMP-0002", name="Teacher Two")
    three_user, three = _person(
        session, school.id, "EMP-0003", name="Teacher Three", department="Maths"
    )
    four_user, four = _person(session, school.id, "EMP-0004", name="Teacher Four")
    _, five = _person(
        session, school.id, "EMP-0005", name="Teacher Five", department="Maths"
    )
    hod_user, hod = _person(
        session, school.id, "EMP-0006", name="Hod One", roles=("hod",)
    )

    classname = ClassName(classname="Class 9", level=9)
    section = Section(section_name="A")
    section_b = Section(section_name="B")
    session.add_all([classname, section, section_b])
    session.commit()
    session.refresh(classname)
    session.refresh(section)
    session.refresh(section_b)

    room = Classroom(
        class_id=classname.class_id, section_id=section.section_id, class_teacher_id=one.id
    )
    other = Classroom(
        class_id=classname.class_id, section_id=section_b.section_id
    )
    physics = Subject(name="Physics", code="PHY")
    maths = Subject(name="Maths", code="MAT")
    session.add_all([room, other, physics, maths])
    session.commit()
    for row in (room, other, physics, maths):
        session.refresh(row)

    for employee, subject in (
        (one, physics),
        (two, physics),
        (three, physics),
        (four, physics),
        (hod, physics),
        (five, maths),
    ):
        session.add(TeacherSubject(teacher_id=employee.id, subject_id=subject.id))
    session.commit()

    # One's Monday: two Physics periods in the same room.
    first = TimetablePeriod(
        classroom_id=room.id,
        subject_id=physics.id,
        teacher_id=one.id,
        day_of_week=DayOfWeek.monday,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    second = TimetablePeriod(
        classroom_id=room.id,
        subject_id=physics.id,
        teacher_id=one.id,
        day_of_week=DayOfWeek.monday,
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    # Four's Monday: 09:00 in another room - a clash for the first period only.
    clash = TimetablePeriod(
        classroom_id=other.id,
        subject_id=physics.id,
        teacher_id=four.id,
        day_of_week=DayOfWeek.monday,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    session.add_all([first, second, clash])
    session.commit()
    for row in (first, second, clash):
        session.refresh(row)

    leave = LeaveRequest(
        requester_user_id=one_user.id,
        leave_type="Sick",
        from_date=DAY,
        to_date=DAY,
        days=1,
        status="Approved",
    )
    session.add(leave)
    session.commit()
    session.refresh(leave)

    return SimpleNamespace(
        session=session,
        school=school,
        principal=principal,
        one_user=one_user,
        one=one,
        two=two,
        three=three,
        four=four,
        hod=hod,
        hod_user=hod_user,
        first=first,
        second=second,
        leave=leave,
    )


def _payload(seeded, *, substitute=None, period=None):
    return SubstitutionAssignIn(
        period_id=(period or seeded.first).id,
        on_date=DAY,
        absent_employee_id=seeded.one.id,
        substitute_employee_id=(substitute or seeded.two).id,
    )



# --- the board --------------------------------------------------------------


def test_the_board_lists_the_absence_with_its_periods(seeded):
    """One approved Sick leave, two Physics periods, both open."""
    board = service.board(seeded.session, DAY, seeded.principal)

    assert [row.employee_id for row in board.absences] == [seeded.one.id]
    assert board.absences[0].reason == "Sick"
    assert board.absences[0].leave_type == "Sick"
    assert board.absences[0].total_periods == 2
    assert board.absences[0].open_periods == 2

    assert board.total == 2
    assert board.covered == 0
    assert board.open == 2
    assert board.timetable_empty is False
    assert all(row.assignment is None for row in board.periods)
    assert {row.slot for row in board.periods} == {"09:00-10:00", "10:00-11:00"}
    assert {row.subject for row in board.periods} == {"Physics"}


def test_reading_the_board_writes_nothing(seeded):
    """A `GET` that created rows would fill a table every time somebody looked."""
    service.board(seeded.session, DAY, seeded.principal)
    service.board(seeded.session, DAY, seeded.principal)

    assert seeded.session.exec(select(SubstitutionRequest)).all() == []
    assert seeded.session.exec(select(SubstitutionAssignment)).all() == []


def test_a_cancelled_leave_removes_the_ask(seeded):
    """The board derives the absence; nothing was copied to keep it alive."""
    seeded.leave.status = "Cancelled"
    seeded.session.add(seeded.leave)
    seeded.session.commit()

    board = service.board(seeded.session, DAY, seeded.principal)
    assert board.absences == []
    assert board.total == 0


def test_a_day_nobody_is_away_is_not_an_empty_timetable(seeded):
    """`0 open` and "this school has no Monday" are different answers."""
    quiet = service.board(seeded.session, date(2026, 11, 16), seeded.principal)
    assert quiet.absences == []
    assert quiet.total == 0
    # A Monday with a timetable is not "empty" - there is simply nobody away.
    assert quiet.timetable_empty is False

    sunday = service.board(seeded.session, date(2026, 11, 15), seeded.principal)
    assert sunday.timetable_empty is True


# --- the candidates ---------------------------------------------------------


def _candidates(seeded, period=None):
    return service.candidates_for(
        seeded.session, (period or seeded.first).id, DAY, seeded.principal
    )


def test_a_colleague_who_does_not_teach_the_subject_is_never_offered(seeded):
    """`teachersubject` is the gate - not "who is free"."""
    answer = _candidates(seeded)
    offered = {row.employee_id for row in answer.candidates}
    blocked = {row.employee_id for row in answer.blocked}

    assert seeded.two.id in offered
    # Teacher Five teaches Maths only: not offered, and not "blocked" either.
    assert all(row.name != "Teacher Five" for row in answer.candidates)
    assert all(row.name != "Teacher Five" for row in answer.blocked)
    assert seeded.one.id not in offered | blocked


def test_the_same_department_comes_first(seeded):
    """Two and Three are both free and equally loaded; the Science one leads."""
    answer = _candidates(seeded)
    order = [row.employee_id for row in answer.candidates]
    scores = {row.employee_id: row.score for row in answer.candidates}

    assert scores[seeded.two.id] > scores[seeded.three.id]
    assert order.index(seeded.two.id) < order.index(seeded.three.id)
    two = next(row for row in answer.candidates if row.employee_id == seeded.two.id)
    assert two.same_department is True
    assert "Science department" in two.reason


def test_a_clash_is_explained_not_hidden(seeded):
    """Teacher Four has 09:00 in another room: refused, in words."""
    answer = _candidates(seeded)
    refused = {row.employee_id: row.reason for row in answer.blocked}

    assert refused[seeded.four.id].startswith("Teaching ")
    assert "09:00" in refused[seeded.four.id]

    # ... and at 10:00 they are free, because the clash was that hour only.
    second = _candidates(seeded, seeded.second)
    assert seeded.four.id in {row.employee_id for row in second.candidates}



# --- assigning --------------------------------------------------------------


def test_assigning_records_the_cover_notifies_and_audits(seeded):
    """One write: the row, the notification and the audit line, together."""
    result = service.assign(seeded.session, _payload(seeded), seeded.principal)

    assert result.status == labels.ASSIGNED
    assert result.substitute_name == "Teacher Two"
    assert result.absent_name == "Teacher One"

    stored = seeded.session.exec(select(SubstitutionAssignment)).one()
    assert stored.period_id == seeded.first.id
    assert stored.on_date == DAY

    notices = seeded.session.exec(select(Notification)).all()
    assert len(notices) == 1
    assert notices[0].user_id == seeded.two.user_id
    assert notices[0].kind == "Substitution"

    audit = seeded.session.exec(
        select(StaffAuditLog).where(StaffAuditLog.section == "substitution")
    ).all()
    assert len(audit) == 1
    assert audit[0].employee_id == seeded.one.id
    assert "covered by Teacher Two" in audit[0].summary

    request = seeded.session.exec(select(SubstitutionRequest)).one()
    assert request.reason == "Sick"
    assert request.employee_id == seeded.one.id


def test_one_adult_per_room(seeded):
    """The second cover for the same period is a `409`, not a second row."""
    service.assign(seeded.session, _payload(seeded), seeded.principal)

    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session, _payload(seeded, substitute=seeded.three), seeded.principal
        )
    assert problem.value.status_code == 409
    assert "already covered by Teacher Two" in problem.value.detail
    assert len(seeded.session.exec(select(SubstitutionAssignment)).all()) == 1


def test_a_cover_the_chosen_person_cannot_take_is_refused_with_the_reason(seeded):
    """Teacher Four is in another room at 09:00; the answer says which room."""
    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session, _payload(seeded, substitute=seeded.four), seeded.principal
        )
    assert problem.value.status_code == 409
    assert "cannot take this period" in problem.value.detail
    assert "Teaching " in problem.value.detail


def test_somebody_who_does_not_teach_the_subject_cannot_be_assigned(seeded):
    """The id the screen sends is re-checked, not trusted."""
    five = seeded.session.exec(
        select(Employee).where(Employee.employee_code == "EMP-0005")
    ).one()
    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session, _payload(seeded, substitute=five), seeded.principal
        )
    assert problem.value.status_code == 409
    assert "does not teach Physics" in problem.value.detail



def test_a_period_is_covered_for_the_day_it_is_taught(seeded):
    """A Monday period asked about on a Tuesday is a `409`, naming the weekday."""
    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session,
            SubstitutionAssignIn(
                period_id=seeded.first.id,
                on_date=date(2026, 11, 10),
                absent_employee_id=seeded.one.id,
                substitute_employee_id=seeded.two.id,
            ),
            seeded.principal,
        )
    assert problem.value.status_code == 409
    assert "tuesday" in problem.value.detail.lower()


def test_a_period_that_is_not_the_absent_teachers_is_refused(seeded):
    """Four's 09:00 cannot be covered "for" Teacher One."""
    fours = seeded.session.exec(
        select(TimetablePeriod).where(TimetablePeriod.teacher_id == seeded.four.id)
    ).one()
    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session,
            SubstitutionAssignIn(
                period_id=fours.id,
                on_date=DAY,
                absent_employee_id=seeded.one.id,
                substitute_employee_id=seeded.two.id,
            ),
            seeded.principal,
        )
    assert problem.value.status_code == 409


def test_nobody_needs_cover_without_an_absence(seeded):
    """An approved leave is what makes the ask; there is no other way in."""
    seeded.leave.status = "Cancelled"
    seeded.session.add(seeded.leave)
    seeded.session.commit()

    with pytest.raises(HTTPException) as problem:
        service.assign(seeded.session, _payload(seeded), seeded.principal)
    assert problem.value.status_code == 404


def test_a_person_cannot_be_their_own_substitute():
    """Refused at the edge, so the service never sees the payload."""
    same = uuid4()
    with pytest.raises(ValidationError):
        SubstitutionAssignIn(
            period_id=uuid4(),
            on_date=DAY,
            absent_employee_id=same,
            substitute_employee_id=same,
        )


# --- the department rule ----------------------------------------------------


def test_a_head_of_department_covers_their_own_department(seeded):
    """Hod One is Science, and Teacher One is Science: allowed."""
    result = service.assign(seeded.session, _payload(seeded), seeded.hod_user)
    assert result.status == labels.ASSIGNED


def test_a_head_of_department_cannot_cover_another_department(seeded):
    """Teacher Three is Maths: not a Science head's to cover (`403`)."""
    with pytest.raises(HTTPException) as problem:
        service._require_assign(seeded.session, seeded.hod_user, seeded.three)
    assert problem.value.status_code == 403
    assert "own department" in problem.value.detail


def test_a_teacher_may_read_the_board_but_not_arrange_cover(seeded):
    """The board is everybody's day; arranging it is the office's."""
    # A teacher-only account reads its own absence and nothing else.
    board = service.board(seeded.session, DAY, seeded.one_user)
    assert [row.employee_id for row in board.absences] == [seeded.one.id]

    with pytest.raises(HTTPException) as problem:
        service.assign(seeded.session, _payload(seeded), seeded.one_user)
    assert problem.value.status_code == 403


# --- approving and withdrawing ----------------------------------------------


def test_approving_signs_the_cover_and_is_idempotent(seeded):
    """A second signature changes nothing - not the status, not the audit trail."""
    assigned = service.assign(seeded.session, _payload(seeded), seeded.principal)
    approved = service.approve(
        seeded.session, assigned.id, "confirmed at assembly", seeded.principal
    )
    assert approved.status == labels.APPROVED
    assert approved.note == "confirmed at assembly"
    assert approved.decided_at is not None

    stamped = approved.decided_at
    again = service.approve(seeded.session, assigned.id, None, seeded.principal)
    assert again.status == labels.APPROVED
    assert again.decided_at == stamped

    audit = seeded.session.exec(
        select(StaffAuditLog).where(StaffAuditLog.section == "substitution")
    ).all()
    # One line for the assignment, one for the approval - and no third.
    assert len(audit) == 2
    assert any("cover approved" in row.summary for row in audit)


def test_only_the_office_signs_a_cover_off(seeded):
    """An HOD arranges cover; the principal (and above) signs it."""
    assigned = service.assign(seeded.session, _payload(seeded), seeded.hod_user)
    with pytest.raises(HTTPException) as problem:
        service.approve(seeded.session, assigned.id, None, seeded.hod_user)
    assert problem.value.status_code == 403


def test_withdrawing_frees_the_slot_for_somebody_else(seeded):
    """The cover is deleted, so the unique key no longer holds the room."""
    assigned = service.assign(seeded.session, _payload(seeded), seeded.principal)
    service.remove(seeded.session, assigned.id, "she is back", seeded.principal)

    assert seeded.session.exec(select(SubstitutionAssignment)).all() == []

    replacement = service.assign(
        seeded.session, _payload(seeded, substitute=seeded.three), seeded.principal
    )
    assert replacement.substitute_name == "Teacher Three"

    audit = seeded.session.exec(
        select(StaffAuditLog).where(StaffAuditLog.section == "substitution")
    ).all()
    assert any("withdrawn" in row.summary for row in audit)
    # Both substitutes were told: assigned, withdrawn, assigned again.
    notices = seeded.session.exec(select(Notification)).all()
    assert len(notices) == 3
    assert any(notice.title == "Substitution withdrawn" for notice in notices)


def test_the_board_reads_the_cover_back(seeded):
    """After the write, the derived board says covered - not `open`."""
    service.assign(seeded.session, _payload(seeded), seeded.principal)
    board = service.board(seeded.session, DAY, seeded.principal)

    assert board.covered == 1
    assert board.open == 1
    covered = next(row for row in board.periods if row.assignment is not None)
    assert covered.assignment.substitute_name == "Teacher Two"
    assert covered.assignment.status == labels.ASSIGNED
    assert board.absences[0].open_periods == 1


def test_a_covered_period_offers_no_candidates(seeded):
    """Offering a second name would invite the `409` the key is going to give."""
    service.assign(seeded.session, _payload(seeded), seeded.principal)
    answer = _candidates(seeded)

    assert answer.candidates == []
    assert answer.blocked == []
    assert answer.assignment is not None
    assert answer.assignment.substitute_name == "Teacher Two"


def test_cover_is_for_the_date_it_is_needed(seeded):
    """The same Monday slot, a different Monday, has no absence behind it."""
    service.assign(seeded.session, _payload(seeded), seeded.principal)
    with pytest.raises(HTTPException) as problem:
        service.assign(
            seeded.session,
            SubstitutionAssignIn(
                period_id=seeded.first.id,
                on_date=date(2026, 11, 16),  # the next Monday
                absent_employee_id=seeded.one.id,
                substitute_employee_id=seeded.three.id,
            ),
            seeded.principal,
        )
    assert problem.value.status_code == 404
    assert len(seeded.session.exec(select(SubstitutionAssignment)).all()) == 1

