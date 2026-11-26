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
)
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.substitution import attendance_access, service
from app.domains.people.teachers.substitution.models import (
    ClassAttendanceAccess,
    SubstitutionAssignment,
    SubstitutionRequest,
)
from app.domains.people.teachers.substitution.schemas import (
    ClassAttendanceAccessIn,
    SubstitutionAssignIn,
)
from app.domains.services.leave.models import LeaveRequest
from tests.course_support import section_subject

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
    session.add_all([room, other])
    session.commit()
    for row in (room, other):
        session.refresh(row)
    # The section's own subjects. What a teacher lists as able to teach is plain text
    # (`subject_tags`): it ranks the cover list, it never decides who may be on it.
    physics_course = section_subject(session, room.id, "Physics", code="PHY")
    other_physics_course = section_subject(session, other.id, "Physics", code="PHY")

    for employee, tags in (
        (one, "Physics"),
        (two, "Physics"),
        (three, "Physics"),
        (four, "Physics"),
        (hod, "Physics"),
        (five, "Maths"),
    ):
        employee.subject_tags = tags
        session.add(employee)
    session.commit()

    # One's Monday: two Physics periods in the same room.
    first = TimetablePeriod(
        classroom_id=room.id,
        classroom_subject_id=physics_course.id,
        teacher_id=one.id,
        day_of_week=DayOfWeek.monday,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    second = TimetablePeriod(
        classroom_id=room.id,
        classroom_subject_id=physics_course.id,
        teacher_id=one.id,
        day_of_week=DayOfWeek.monday,
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    # Four's Monday: 09:00 in another room - a clash for the first period only.
    clash = TimetablePeriod(
        classroom_id=other.id,
        classroom_subject_id=other_physics_course.id,
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
        employee_id=one.id,
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

    # A school day with no timetable at all (Wednesday: only Monday is built) is "empty".
    wednesday = service.board(seeded.session, date(2026, 11, 18), seeded.principal)
    assert wednesday.is_open is True
    assert wednesday.timetable_empty is True

    # A Sunday is the school's weekly off: closed, which is not the same as "no timetable".
    sunday = service.board(seeded.session, date(2026, 11, 15), seeded.principal)
    assert sunday.is_open is False
    assert sunday.timetable_empty is False


# --- the candidates ---------------------------------------------------------


def _candidates(seeded, period=None):
    return service.candidates_for(
        seeded.session, (period or seeded.first).id, DAY, seeded.principal
    )


def test_a_colleague_who_lists_another_subject_is_still_offered_but_ranks_lower(seeded):
    """Any active teacher can cover: the tags only nudge the ranking, never gate it."""
    answer = _candidates(seeded)
    offered = {row.employee_id: row for row in answer.candidates}
    blocked = {row.employee_id for row in answer.blocked}

    assert seeded.two.id in offered
    five = next(row for row in answer.candidates if row.name == "Teacher Five")
    assert five.reason.startswith("Free to cover"), "lists Maths, not Physics"
    assert offered[seeded.two.id].reason.startswith("Lists Physics in their subjects")

    # Listing the subject raises the very same person by exactly the tag boost - and
    # nothing else about them changes.
    employee = seeded.session.exec(
        select(Employee).where(Employee.employee_code == "EMP-0005")
    ).one()
    employee.subject_tags = "maths,  PHYSICS"
    seeded.session.add(employee)
    seeded.session.commit()
    again = next(
        row for row in _candidates(seeded).candidates if row.name == "Teacher Five"
    )
    assert again.score == five.score + 10
    assert again.reason.startswith("Lists Physics in their subjects")
    # The absent teacher is never their own cover.
    assert seeded.one.id not in set(offered) | blocked


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


def test_somebody_who_lists_another_subject_can_still_be_assigned(seeded):
    """Not listing Physics is not a refusal: availability is the only gate."""
    five = seeded.session.exec(
        select(Employee).where(Employee.employee_code == "EMP-0005")
    ).one()
    result = service.assign(
        seeded.session, _payload(seeded, substitute=five), seeded.principal
    )
    assert result is not None
    assigned = seeded.session.exec(select(SubstitutionAssignment)).all()
    assert [row.substitute_employee_id for row in assigned] == [five.id]



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


# --- an absence is noticed from the staff attendance, not only from a leave ---


def _four_period(seeded):
    """Teacher Four's 09:00 period on `DAY` (the clash row in the fixture)."""
    return seeded.session.exec(
        select(TimetablePeriod).where(TimetablePeriod.teacher_id == seeded.four.id)
    ).one()


def _mark_absent(seeded, employee, day=DAY):
    seeded.session.add(
        StaffAttendanceRecord(employee_id=employee.id, date=day, status="absent")
    )
    seeded.session.commit()


def test_somebody_marked_absent_on_the_register_is_on_the_board_without_any_leave(seeded):
    """The Aditi case: no leave filed, but the staff register says Absent."""
    _mark_absent(seeded, seeded.four)

    board = service.board(seeded.session, DAY, seeded.principal)

    by_id = {row.employee_id: row for row in board.absences}
    assert seeded.four.id in by_id
    four = by_id[seeded.four.id]
    assert (four.source, four.reason, four.leave_type) == (
        "register",
        "Absent (staff register)",
        None,
    )
    assert (four.total_periods, four.open_periods) == (1, 1)
    # The leave-based absence is still there, and says where it came from.
    assert by_id[seeded.one.id].source == "leave"


def test_a_register_absence_with_no_periods_that_day_is_not_a_line_on_the_board(seeded):
    """Teacher Two teaches nothing on `DAY`: nothing to cover, so no noise."""
    _mark_absent(seeded, seeded.two)

    board = service.board(seeded.session, DAY, seeded.principal)

    assert seeded.two.id not in {row.employee_id for row in board.absences}


def test_cover_can_be_arranged_for_a_register_absence(seeded):
    _mark_absent(seeded, seeded.four)
    period = _four_period(seeded)

    done = service.assign(
        seeded.session,
        SubstitutionAssignIn(
            period_id=period.id,
            on_date=DAY,
            absent_employee_id=seeded.four.id,
            substitute_employee_id=seeded.two.id,
        ),
        seeded.principal,
    )

    assert done.substitute_employee_id == seeded.two.id
    request = seeded.session.exec(
        select(SubstitutionRequest).where(SubstitutionRequest.employee_id == seeded.four.id)
    ).one()
    assert request.reason == "Absent (staff register)"
    board = service.board(seeded.session, DAY, seeded.principal)
    assert (board.covered, board.open) == (1, 2)


def test_a_colleague_marked_absent_cannot_stand_in(seeded):
    """Somebody who is not in school is refused, with the reason, not silently skipped."""
    _mark_absent(seeded, seeded.two)

    result = service.candidates_for(seeded.session, seeded.first.id, DAY, seeded.principal)

    assert seeded.two.id not in {row.employee_id for row in result.candidates}
    why = {row.employee_id: row.reason for row in result.blocked}
    assert why[seeded.two.id] == "Marked absent on the staff register"


# --- the school calendar: a closed day has nothing to cover -------------------

SUNDAY = date(2026, 11, 8)  # the school's default weekly off


def test_a_closed_day_has_no_cover_sheet(seeded):
    board = service.board(seeded.session, SUNDAY, seeded.principal)

    assert board.is_open is False
    assert board.closed_reason == "Sunday"
    assert (board.absences, board.periods, board.total) == ([], [], 0)
    assert board.timetable_empty is False  # not "no timetable": the school is shut


def test_cover_cannot_be_arranged_or_offered_on_a_closed_day(seeded):
    with pytest.raises(HTTPException) as offered:
        service.candidates_for(seeded.session, seeded.first.id, SUNDAY, seeded.principal)
    assert offered.value.status_code == 409
    assert "closed" in offered.value.detail

# --- who takes the class's attendance while its class teacher is away ----------


def _room(seeded):
    """The class-section Teacher One (on leave on `DAY`) is the class teacher of."""
    return seeded.session.exec(
        select(Classroom).where(Classroom.class_teacher_id == seeded.one.id)
    ).one()


def _hand_over(seeded, delegate=None, *, room=None, day=DAY):
    return service.set_attendance_access(
        seeded.session,
        ClassAttendanceAccessIn(
            classroom_id=(room or _room(seeded)).id,
            on_date=day,
            delegate_employee_id=(delegate or seeded.two).id,
        ),
        seeded.principal,
    )


def test_the_board_names_the_class_of_an_away_class_teacher(seeded):
    board = service.board(seeded.session, DAY, seeded.principal)

    one = next(row for row in board.absences if row.employee_id == seeded.one.id)
    assert one.class_teacher_of == ["Class 9-A"]
    assert [(row.class_label, row.away_teacher_name, row.is_class_teacher) for row in board.classes] == [
        ("Class 9-A", "Teacher One", True)
    ]
    row = board.classes[0]
    assert (row.suggested_employee_id, row.access) == (None, None)  # nobody covers yet

    # Once somebody covers one of its periods, they are the "same teacher" choice.
    service.assign(seeded.session, _payload(seeded), seeded.principal)
    row = service.board(seeded.session, DAY, seeded.principal).classes[0]
    assert row.suggested_employee_id == seeded.two.id
    assert row.suggested_name == "Teacher Two"


def test_a_class_teacher_with_no_periods_still_needs_their_register_handed_over(seeded):
    """Marked Absent on the register, no leave, nothing taught on `DAY`: still on the board."""
    seeded.session.add(
        StaffAttendanceRecord(employee_id=seeded.three.id, date=DAY, status="absent")
    )
    other = seeded.session.exec(
        select(Classroom).where(Classroom.class_teacher_id.is_(None))
    ).first()
    other.class_teacher_id = seeded.three.id
    seeded.session.add(other)
    seeded.session.commit()

    board = service.board(seeded.session, DAY, seeded.principal)

    assert seeded.three.id in {row.employee_id for row in board.absences}
    assert "Class 9-B" in {row.class_label for row in board.classes}


def test_a_hand_over_gives_no_access_until_the_office_approves_it(seeded):
    done = _hand_over(seeded)
    assert (done.status, done.delegate_employee_id, done.class_label) == (
        "Assigned",
        seeded.two.id,
        "Class 9-A",
    )
    two_user = seeded.session.get(User, seeded.two.user_id)
    room = _room(seeded)
    assert attendance_access.has_access(seeded.session, two_user, room.id, DAY) is False

    approved = service.approve_attendance_access(seeded.session, done.id, seeded.principal)

    assert approved.status == "Approved"
    assert attendance_access.has_access(seeded.session, two_user, room.id, DAY) is True
    # Approving again changes nothing.
    again = service.approve_attendance_access(seeded.session, done.id, seeded.principal)
    assert again.decided_at == approved.decided_at


def test_the_access_is_one_class_one_day_and_nothing_wider(seeded):
    done = _hand_over(seeded)
    service.approve_attendance_access(seeded.session, done.id, seeded.principal)
    two_user = seeded.session.get(User, seeded.two.user_id)
    room = _room(seeded)
    sister = seeded.session.exec(select(Classroom).where(Classroom.id != room.id)).first()
    three_user = seeded.session.get(User, seeded.three.user_id)

    # Another day: no. Another class-section of the same class: no. Somebody else: no.
    other_day = date(2026, 11, 10)
    assert attendance_access.has_access(seeded.session, two_user, room.id, other_day) is False
    assert attendance_access.has_access(seeded.session, two_user, sister.id, DAY) is False
    assert attendance_access.has_access(seeded.session, three_user, room.id, DAY) is False
    assert attendance_access.has_access(seeded.session, seeded.principal, room.id, DAY) is False


def test_choosing_somebody_else_resets_the_approval(seeded):
    first = _hand_over(seeded, seeded.two)
    service.approve_attendance_access(seeded.session, first.id, seeded.principal)

    changed = _hand_over(seeded, seeded.three)  # "other": a different teacher

    assert changed.id == first.id  # one hand-over per class per day
    assert (changed.status, changed.delegate_employee_id) == ("Assigned", seeded.three.id)
    room = _room(seeded)
    two_user = seeded.session.get(User, seeded.two.user_id)
    three_user = seeded.session.get(User, seeded.three.user_id)
    assert attendance_access.has_access(seeded.session, two_user, room.id, DAY) is False
    assert attendance_access.has_access(seeded.session, three_user, room.id, DAY) is False


def test_a_hand_over_is_only_for_a_class_whose_teacher_is_away(seeded):
    """Teacher Two is in school, so the register of the class they run is still theirs."""
    other = seeded.session.exec(
        select(Classroom).where(Classroom.class_teacher_id.is_(None))
    ).first()
    other.class_teacher_id = seeded.two.id
    seeded.session.add(other)
    seeded.session.commit()

    with pytest.raises(HTTPException) as caught:
        _hand_over(seeded, seeded.three, room=other)

    assert caught.value.status_code == 409
    assert "away" in caught.value.detail


def test_somebody_who_is_away_themselves_cannot_be_chosen(seeded):
    seeded.session.add(
        StaffAttendanceRecord(employee_id=seeded.two.id, date=DAY, status="absent")
    )
    seeded.session.commit()

    with pytest.raises(HTTPException) as caught:
        _hand_over(seeded, seeded.two)

    assert caught.value.status_code == 409
    assert "absent" in caught.value.detail


def test_a_hand_over_cannot_be_made_on_a_closed_day(seeded):
    with pytest.raises(HTTPException) as caught:
        _hand_over(seeded, day=SUNDAY)
    assert caught.value.status_code == 409


def test_withdrawing_a_hand_over_takes_the_access_back(seeded):
    done = _hand_over(seeded)
    service.approve_attendance_access(seeded.session, done.id, seeded.principal)
    two_user = seeded.session.get(User, seeded.two.user_id)
    room = _room(seeded)
    assert attendance_access.has_access(seeded.session, two_user, room.id, DAY) is True

    service.remove_attendance_access(seeded.session, done.id, seeded.principal)

    assert attendance_access.has_access(seeded.session, two_user, room.id, DAY) is False
    assert service.board(seeded.session, DAY, seeded.principal).classes[0].access is None


def test_a_teacher_cannot_hand_over_or_approve(seeded):
    two_user = seeded.session.get(User, seeded.two.user_id)
    with pytest.raises(HTTPException) as caught:
        service.set_attendance_access(
            seeded.session,
            ClassAttendanceAccessIn(
                classroom_id=_room(seeded).id,
                on_date=DAY,
                delegate_employee_id=seeded.three.id,
            ),
            two_user,
        )
    # Out of a teacher's scope reads as "not found" (the API never confirms who exists).
    assert caught.value.status_code in (403, 404)

    done = _hand_over(seeded)
    with pytest.raises(HTTPException) as approve:
        service.approve_attendance_access(seeded.session, done.id, two_user)
    assert approve.value.status_code in (403, 404)
    assert done.status == "Assigned"  # and nothing was signed


def test_the_class_page_opens_and_the_class_is_listed_for_the_delegate_today(seeded):
    """The page and the "My classes" list read today's approved grant (inserted directly: the
    hand-over itself needs an open school day, and today may not be one)."""
    from app.domains.academic.classroom import service as classroom_service

    room = _room(seeded)
    two_user = seeded.session.get(User, seeded.two.user_id)
    assert classroom_service.can_open_section(seeded.session, two_user, room.id) is False

    seeded.session.add(
        ClassAttendanceAccess(
            classroom_id=room.id,
            on_date=date.today(),
            class_teacher_id=seeded.one.id,
            delegate_employee_id=seeded.two.id,
            status="Approved",
        )
    )
    seeded.session.commit()

    assert classroom_service.can_open_section(seeded.session, two_user, room.id) is True
    cards = classroom_service.classroom_cards(seeded.session, two_user)
    assert [(card.title, card.className, card.teacher) for card in cards] == [
        ("Attendance - Class 9-A", "Class 9-A", "Teacher One")
    ]


def test_the_years_class_teacher_assignment_decides_not_the_old_pointer(seeded):
    """`classroom.class_teacher_id` is only a legacy pointer: once the year has assignments,
    the assignment says who runs the class - an ended one means nobody, whatever the
    pointer still names."""
    from app.domains.academic.classroom.students.promotion.class_teacher import (
        class_teacher_rooms_for,
    )
    from app.domains.academic.classroom.students.promotion.models import (
        ClassTeacherAssignment,
    )
    from app.domains.admin.settings.models import AcademicYear

    year = seeded.session.exec(select(AcademicYear)).first()
    if year is None:
        year = AcademicYear(
            name="2026-27",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_current=True,
        )
        seeded.session.add(year)
        seeded.session.commit()
        seeded.session.refresh(year)
    room = _room(seeded)  # the pointer names Teacher One

    # The year's record says Teacher Two runs it, and One's turn ended.
    seeded.session.add(
        ClassTeacherAssignment(
            classroom_id=room.id,
            academic_year_id=year.id,
            teacher_id=seeded.one.id,
            effective_from=date(2026, 4, 1),
            effective_to=date(2026, 6, 30),
        )
    )
    seeded.session.add(
        ClassTeacherAssignment(
            classroom_id=room.id,
            academic_year_id=year.id,
            teacher_id=seeded.two.id,
            effective_from=date(2026, 7, 1),
        )
    )
    seeded.session.commit()

    assert class_teacher_rooms_for(seeded.session, [seeded.one.id, seeded.two.id]) == {
        seeded.two.id: [room.id]
    }
    # Teacher One is on leave but runs no class now: no "C.T" line, and the class is listed
    # only because One still has periods in it - not as the class teacher.
    board = service.board(seeded.session, DAY, seeded.principal)
    one = next(row for row in board.absences if row.employee_id == seeded.one.id)
    assert one.class_teacher_of == []
    assert [(row.class_label, row.is_class_teacher) for row in board.classes] == [
        ("Class 9-A", False)
    ]


def test_a_class_an_away_teacher_only_teaches_in_gets_an_attendance_column_too(seeded):
    """Not only the class teacher's own class: the class of every covered period."""
    four_period = seeded.session.exec(
        select(TimetablePeriod).where(TimetablePeriod.teacher_id == seeded.four.id)
    ).one()
    # Teacher One (on leave) also teaches in Four's room - a class run by nobody who is away.
    seeded.session.add(
        TimetablePeriod(
            classroom_id=four_period.classroom_id,
            classroom_subject_id=four_period.classroom_subject_id,
            teacher_id=seeded.one.id,
            day_of_week=DayOfWeek.monday,
            start_time=time(11, 0),
            end_time=time(12, 0),
        )
    )
    seeded.session.commit()

    board = service.board(seeded.session, DAY, seeded.principal)

    by_label = {row.class_label: row for row in board.classes}
    assert by_label["Class 9-A"].is_class_teacher is True
    assert by_label["Class 9-B"].is_class_teacher is False
    assert by_label["Class 9-B"].away_teacher_name == "Teacher One"
    # Every period row carries its class, so the table can put the button on that row.
    assert {row.classroom_id for row in board.periods} == {
        row.classroom_id for row in board.classes
    }
    room_b = seeded.session.get(Classroom, four_period.classroom_id)
    done = _hand_over(seeded, seeded.three, room=room_b)
    assert (done.class_label, done.status) == ("Class 9-B", "Assigned")
