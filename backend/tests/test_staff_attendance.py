"""The daily staff register: the day, the month, and the two writes.

Every test here is a number that is invisible in the browser when it is wrong:

* a day nobody marked reads **Not Marked**, not absent, and the percentage divides
  by the days somebody marked - an unfinished month must not look like an
  attendance problem;
* approved leave is **derived**, so `On Leave` needs no row and no copy, and marking
  somebody who is on leave is refused rather than stored twice;
* a re-sent register is not forty audit lines, and a changed one says what the day
  used to be;
* a leaver is off today's register but keeps their month - the record still has to
  explain itself to payroll;
* a department head reads their department's register and cannot mark it.

Runs on in-memory SQLite, like the rest of this module's suite.
"""

import importlib
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.people.teachers.staff_attendance import service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.staff_attendance.schemas import (
    AttendanceBulkIn,
    AttendanceRecordPatch,
)
from app.domains.services.leave.models import LeaveRequest


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
        ("vice_principal", "Vice Principal"),
        ("teacher", "Teacher"),
        ("hod", "Head of Department"),
        ("school_admin", "School Administrator"),
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


def _employee(session: Session, user: User, code: str, **extra) -> Employee:
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=extra.pop("department", "Science"),
        joining_date=extra.pop("joining_date", date(2023, 6, 1)),
        email=f"{code.lower()}@test",
        **extra,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _person(
    session: Session, school_id, code: str, *, name=None, roles=("teacher",), **extra
):
    user = _user(session, name or f"Staff {code}", school_id, roles)
    return user, _employee(session, user, code, **extra)


def _school(session: Session, name: str = "Test School", code: str = "TST-0001"):
    # The email carries the code: `school.email` is unique, and two fixtures in one
    # test (the school and "somewhere else") have to be two schools.
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


#: A day the tests mark. Fixed, so a run in 2030 asserts the same thing as today's.
DAY = date(2026, 11, 10)
MONTH = "2026-11"


@pytest.fixture()
def seeded():
    """One school, four people on the roll, one leaver and a principal who marks.

    * **Teacher One** and **Teacher Two** are Science; **Teacher Three** is Maths,
      so the department filter has something to narrow;
    * **Hod One** is on the roll too - an HOD teaches, and `labels.TEACHING_ROLES`
      has said so since Phase 2 - with the read right only, which is the point of
      them;
    * **Teacher Leaver** is off the roll (`left_on`) - their month stays readable.

    So a day's register holds four lines for this school, and a `left_on` person is
    not one of them.
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
    leaver_user, leaver = _person(
        session,
        school.id,
        "EMP-0004",
        name="Teacher Leaver",
        left_on=date(2026, 1, 31),
    )
    hod_user, hod = _person(
        session, school.id, "EMP-0005", name="Hod One", roles=("hod",)
    )

    return SimpleNamespace(
        session=session,
        school=school,
        principal=principal,
        one_user=one_user,
        one=one,
        two_user=two_user,
        two=two,
        three_user=three_user,
        three=three,
        leaver_user=leaver_user,
        leaver=leaver,
        hod_user=hod_user,
        hod=hod,
    )


def _leave(
    session: Session,
    *,
    user: User,
    start: date = DAY,
    end: date = DAY,
    leave_type: str = "Medical",
    status: str = "Approved",
) -> LeaveRequest:
    """A staff leave row - `student_id` NULL is what makes it a staff one."""
    days = (end - start).days + 1
    request = LeaveRequest(
        requester_user_id=user.id,
        leave_type=leave_type,
        from_date=start,
        to_date=end,
        days=days,
        reason="Filed in a test",
        status=status,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def _bulk(seeded, records, on_date: date = DAY) -> AttendanceBulkIn:
    return AttendanceBulkIn(
        date=on_date,
        records=[
            {"employee_id": employee.id, "status": status}
            for employee, status in records
        ],
    )


def _row(register, employee):
    return next(row for row in register.rows if row.employee_id == employee.id)


def _audits(session: Session, section: str = "attendance") -> list[StaffAuditLog]:
    return list(
        session.exec(
            select(StaffAuditLog).where(StaffAuditLog.section == section)
        ).all()
    )


def _stranger(session: Session, code: str = "EMP-9001") -> Employee:
    """A person in *another* school, created outside this session's tenant scope.

    The tenant guard refuses a row for a second school on a scoped session - that is
    the protection itself, and a test cannot simply insert one. So the scope is
    lifted for the insert and put straight back: the caller then cannot see this
    person, which is exactly what the `404` tests assert.
    """
    scoped = session.info.pop("school_id", None)
    try:
        school = _school(session, name=f"Other School {code}", code=f"OTH-{code}")
        _, employee = _person(session, school.id, code, name=f"Stranger {code}")
        return employee
    finally:
        session.info["school_id"] = scoped


# --- the day's register ----------------------------------------------------


def test_a_day_nobody_marked_reads_not_marked(seeded):
    """The register is not a list of rows; it is a list of people."""
    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)

    assert register.date == DAY
    assert register.weekday == "Tuesday"
    assert register.total == 4  # the leaver is not on today's book
    assert register.marked == 0
    assert register.not_marked == 4
    assert register.percent == 0
    assert {row.status for row in register.rows} == {labels.NOT_MARKED}
    assert {row.status_label for row in register.rows} == {"Not Marked"}
    assert all(row.record_id is None for row in register.rows)
    assert all(row.is_marked is False for row in register.rows)


def test_marking_a_day_sets_the_statuses_and_the_counts(seeded):
    """Three people, three answers, and the header agrees with the rows."""
    service.mark_bulk(
        seeded.session,
        _bulk(
            seeded,
            [
                (seeded.one, "present"),
                (seeded.two, "half_day"),
                (seeded.three, "absent"),
            ],
        ),
        seeded.principal,
    )
    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)

    assert _row(register, seeded.one).status_label == "Present"
    assert _row(register, seeded.two).status_label == "Half Day"
    assert _row(register, seeded.three).status_label == "Absent"
    assert register.present == 1
    assert register.half_day == 1
    assert register.absent == 1
    # Hod One was not marked by this call: the register keeps saying so.
    assert register.not_marked == 1
    assert register.marked == 3
    # (present*2 + half) / marked*2 = 3 / 6 = 50%, so a half day is half a day.
    assert register.percent == 50


def test_the_write_answers_with_the_day_as_it_now_reads(seeded):
    """One call marks, and the screen gets the marked register back - no refetch."""
    register = service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )

    row = _row(register, seeded.one)
    assert row.status == labels.PRESENT
    assert row.is_marked is True
    assert row.record_id is not None
    assert row.marked_by == "Principal One"
    assert row.marked_at is not None


def test_a_second_bulk_updates_the_row_instead_of_adding_one(seeded):
    """One row per person per day, whatever the caller sends twice."""
    service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "absent")]), seeded.principal
    )

    rows = seeded.session.exec(
        select(StaffAttendanceRecord).where(
            StaffAttendanceRecord.employee_id == seeded.one.id
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].status == labels.ABSENT


def test_re_sending_the_same_register_writes_no_second_audit_line(seeded):
    """A double click is not an event; the trail is for changes."""
    payload = _bulk(seeded, [(seeded.one, "present"), (seeded.two, "present")])
    service.mark_bulk(seeded.session, payload, seeded.principal)
    service.mark_bulk(seeded.session, payload, seeded.principal)

    audits = _audits(seeded.session)
    assert len(audits) == 2  # one per person, on the first call only
    assert {audit.action for audit in audits} == {"created"}


def test_changing_a_status_is_audited_with_what_the_day_used_to_be(seeded):
    """The trail says `Present -> Absent`, in the words the screen prints."""
    service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "absent")]), seeded.principal
    )

    audits = _audits(seeded.session)
    assert len(audits) == 2
    assert audits[-1].action == "updated"
    assert audits[-1].summary == f"{DAY}: Present -> Absent"
    assert audits[-1].row_id is not None


def test_the_status_filter_narrows_the_rows_and_not_the_counts(seeded):
    """ "Absent 3" must not become "Absent 1 of 1" because somebody asked to see it."""
    service.mark_bulk(
        seeded.session,
        _bulk(
            seeded,
            [
                (seeded.one, "present"),
                (seeded.two, "present"),
                (seeded.three, "absent"),
            ],
        ),
        seeded.principal,
    )
    register = service.register(
        seeded.session, on_date=DAY, user=seeded.principal, status=labels.ABSENT
    )

    assert [row.employee_id for row in register.rows] == [seeded.three.id]
    assert register.present == 2
    assert register.absent == 1
    assert register.total == 4


def test_the_department_filter_narrows_the_roll_and_its_counts(seeded):
    """The counts describe the people in scope, so the split still adds up."""
    register = service.register(
        seeded.session, on_date=DAY, user=seeded.principal, department="maths"
    )

    assert register.total == 1
    assert register.rows[0].employee_id == seeded.three.id
    assert register.not_marked == 1


def test_an_unknown_status_filter_is_a_422_naming_the_vocabulary(seeded):
    with pytest.raises(HTTPException) as caught:
        service.register(
            seeded.session, on_date=DAY, user=seeded.principal, status="napping"
        )

    assert caught.value.status_code == 422
    assert "not_marked" in caught.value.detail


def test_a_leaver_is_not_on_todays_register(seeded):
    """The register is today's book; somebody who left in January is history."""
    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)

    assert seeded.leaver.id not in {row.employee_id for row in register.rows}


# --- approved leave is derived, never copied -------------------------------


def test_somebody_on_approved_leave_reads_on_leave_without_a_row(seeded):
    """The leave is the record; the register needs no copy of it."""
    _leave(seeded.session, user=seeded.one_user, leave_type="Medical")

    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)
    row = _row(register, seeded.one)

    assert row.status == labels.ATTENDANCE_ON_LEAVE
    assert row.status_label == "On Leave"
    assert row.leave_type == "Medical"
    assert row.is_marked is False
    assert register.on_leave == 1
    assert register.not_marked == 3
    # Leave is neither attendance nor absence: it is in neither side of the fraction.
    assert register.marked == 0
    assert register.percent == 0


def test_pending_leave_is_not_leave_yet(seeded):
    """Only an approved leave makes somebody away - a request is not a decision."""
    _leave(seeded.session, user=seeded.one_user, status="Pending")

    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)

    assert _row(register, seeded.one).status == labels.NOT_MARKED
    assert register.on_leave == 0


def test_a_leave_that_ends_before_the_day_does_not_colour_it(seeded):
    """A medical leave last week says nothing about today."""
    _leave(
        seeded.session,
        user=seeded.one_user,
        start=DAY - timedelta(days=6),
        end=DAY - timedelta(days=1),
    )

    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)

    assert _row(register, seeded.one).status == labels.NOT_MARKED


def test_leave_wins_over_a_row_marked_before_it_was_approved(seeded):
    """The row is kept, not deleted - cancel the leave and the day is back."""
    service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    leave = _leave(seeded.session, user=seeded.one_user)

    register = service.register(seeded.session, on_date=DAY, user=seeded.principal)
    row = _row(register, seeded.one)
    assert row.status == labels.ATTENDANCE_ON_LEAVE
    # The recorded day is still on file, which is why the leave can be undone.
    assert row.record_id is not None
    stored = seeded.session.exec(
        select(StaffAttendanceRecord).where(
            StaffAttendanceRecord.employee_id == seeded.one.id
        )
    ).all()
    assert [entry.status for entry in stored] == [labels.PRESENT]

    seeded.session.delete(leave)
    seeded.session.commit()
    again = service.register(seeded.session, on_date=DAY, user=seeded.principal)
    assert _row(again, seeded.one).status == labels.PRESENT


def test_marking_somebody_on_approved_leave_is_refused(seeded):
    """A mark and a leave are two records saying different things; refuse the second."""
    _leave(seeded.session, user=seeded.one_user, leave_type="Medical")

    with pytest.raises(HTTPException) as caught:
        service.mark_bulk(
            seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
        )

    assert caught.value.status_code == 409
    assert "Medical" in caught.value.detail
    assert _audits(seeded.session) == []


def test_a_refused_payload_writes_no_half_register(seeded):
    """Everything is checked before the first row, so a `409` leaves nothing behind."""
    _leave(seeded.session, user=seeded.two_user)

    with pytest.raises(HTTPException):
        service.mark_bulk(
            seeded.session,
            _bulk(seeded, [(seeded.one, "present"), (seeded.two, "present")]),
            seeded.principal,
        )

    assert seeded.session.exec(select(StaffAttendanceRecord)).all() == []


# --- amending one day ------------------------------------------------------


def test_amending_a_marked_day_changes_it_and_says_so(seeded):
    marked = service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    record_id = _row(marked, seeded.one).record_id

    day = service.amend(
        seeded.session,
        record_id,
        AttendanceRecordPatch(status="absent"),
        seeded.principal,
    )

    assert day.status == labels.ABSENT
    assert day.status_label == "Absent"
    assert _audits(seeded.session)[-1].summary == f"{DAY}: Present -> Absent"


def test_amending_with_the_same_status_writes_nothing(seeded):
    """A form that sends its whole state on save is not a trail of no-ops."""
    marked = service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    record_id = _row(marked, seeded.one).record_id
    before = len(_audits(seeded.session))

    service.amend(
        seeded.session,
        record_id,
        AttendanceRecordPatch(status="present"),
        seeded.principal,
    )

    assert len(_audits(seeded.session)) == before


def test_amending_a_remarks_only_change_is_audited_as_a_remark(seeded):
    marked = service.mark_bulk(
        seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.principal
    )
    record_id = _row(marked, seeded.one).record_id

    day = service.amend(
        seeded.session,
        record_id,
        AttendanceRecordPatch(remarks="Arrived after the assembly"),
        seeded.principal,
    )

    assert day.remarks == "Arrived after the assembly"
    assert day.status == labels.PRESENT
    assert "remarks" in _audits(seeded.session)[-1].summary


def test_amending_a_day_nobody_marked_is_a_404(seeded):
    with pytest.raises(HTTPException) as caught:
        service.amend(
            seeded.session,
            seeded.one.id,  # an employee id is not a record id
            AttendanceRecordPatch(status="present"),
            seeded.principal,
        )

    assert caught.value.status_code == 404


def test_amending_a_leavers_day_is_refused(seeded):
    """Their month stays readable, but a day on it may not be changed."""
    row = StaffAttendanceRecord(
        employee_id=seeded.leaver.id, date=DAY, status=labels.PRESENT
    )
    seeded.session.add(row)
    seeded.session.commit()
    seeded.session.refresh(row)

    with pytest.raises(HTTPException) as caught:
        service.amend(
            seeded.session,
            row.id,
            AttendanceRecordPatch(status="absent"),
            seeded.principal,
        )

    assert caught.value.status_code == 409
    assert "Reactivate" in caught.value.detail


# --- one person's month ----------------------------------------------------


def test_a_month_nobody_marked_is_a_grid_of_not_marked(seeded):
    """November has thirty days; all thirty are in the answer, none are absent."""
    month = service.month(seeded.session, seeded.one.id, MONTH, seeded.principal)

    assert len(month.days) == 30
    assert month.days[0].date == date(2026, 11, 1)
    assert month.days[-1].date == date(2026, 11, 30)
    assert month.month_label == "November 2026"
    assert month.not_marked == 30
    assert month.marked == 0
    assert month.percent == 0
    assert month.name == "Teacher One"


def test_the_month_percentage_divides_by_marked_days_not_the_calendar(seeded):
    """18 present, 1 half day, 1 absent: 92% of the twenty days somebody marked."""
    for day in range(1, 19):
        seeded.session.add(
            StaffAttendanceRecord(
                employee_id=seeded.one.id,
                date=date(2026, 11, day),
                status=labels.PRESENT,
            )
        )
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.one.id, date=date(2026, 11, 19), status=labels.HALF_DAY
        )
    )
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.one.id, date=date(2026, 11, 20), status=labels.ABSENT
        )
    )
    seeded.session.commit()

    month = service.month(seeded.session, seeded.one.id, MONTH, seeded.principal)

    assert month.present == 18
    assert month.half_day == 1
    assert month.absent == 1
    assert month.marked == 20
    assert month.not_marked == 10
    # (18*2 + 1) / (20*2) = 37/40 = 92.5%, floored - not 61% of a thirty-day month.
    assert month.percent == 92


def test_leave_days_are_on_leave_in_the_month_and_out_of_the_fraction(seeded):
    """A week of approved leave is not a week of absences."""
    _leave(
        seeded.session,
        user=seeded.one_user,
        start=date(2026, 11, 2),
        end=date(2026, 11, 6),
        leave_type="Casual",
    )
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.one.id, date=date(2026, 11, 9), status=labels.PRESENT
        )
    )
    seeded.session.commit()

    month = service.month(seeded.session, seeded.one.id, MONTH, seeded.principal)

    assert month.on_leave == 5
    assert [day.status for day in month.days[1:6]] == [labels.ATTENDANCE_ON_LEAVE] * 5
    assert month.days[1].leave_type == "Casual"
    assert month.marked == 1
    assert month.percent == 100


def test_a_leavers_month_is_still_readable(seeded):
    """Payroll may still have to explain a month that has already been closed."""
    seeded.session.add(
        StaffAttendanceRecord(
            employee_id=seeded.leaver.id, date=date(2026, 1, 9), status=labels.ABSENT
        )
    )
    seeded.session.commit()

    month = service.month(seeded.session, seeded.leaver.id, "2026-01", seeded.principal)

    assert month.absent == 1
    assert month.name == "Teacher Leaver"


@pytest.mark.parametrize("bad", ["2026-13", "2026", "November", "2026-1x", "2026-00"])
def test_a_month_key_it_cannot_read_is_a_422(seeded, bad):
    with pytest.raises(HTTPException) as caught:
        service.month(seeded.session, seeded.one.id, bad, seeded.principal)

    assert caught.value.status_code == 422


def test_a_month_for_somebody_out_of_scope_is_a_404(seeded):
    stranger = _stranger(seeded.session, "EMP-9001")
    # Out of the identity map, so the lookup has to reach the database and pass the
    # tenant filter - a cached object would answer from memory and prove nothing.
    seeded.session.expunge(stranger)

    with pytest.raises(HTTPException) as caught:
        service.month(seeded.session, stranger.id, MONTH, seeded.principal)

    assert caught.value.status_code == 404


# --- who may read and who may write ---------------------------------------


def test_a_department_head_reads_the_register_but_cannot_mark_it(seeded):
    """`staff_attendance.read` without `.mark` - the reason the two exist."""
    register = service.register(seeded.session, on_date=DAY, user=seeded.hod)
    assert register.total == 4

    with pytest.raises(HTTPException) as caught:
        service.mark_bulk(
            seeded.session, _bulk(seeded, [(seeded.one, "present")]), seeded.hod
        )

    assert caught.value.status_code == 403
    assert seeded.session.exec(select(StaffAttendanceRecord)).all() == []


def test_a_teacher_reads_only_their_own_line(seeded):
    """The scope rule still applies if a school ever grants the read to teachers."""
    register = service.register(seeded.session, on_date=DAY, user=seeded.two_user)

    assert [row.employee_id for row in register.rows] == [seeded.two.id]
    assert register.total == 1


def test_marking_a_stranger_writes_nothing(seeded):
    """An employee id from another school is a `404`, not a cross-tenant row."""
    stranger = _stranger(seeded.session, "EMP-9002")

    with pytest.raises(HTTPException) as caught:
        service.mark_bulk(
            seeded.session, _bulk(seeded, [(stranger, "present")]), seeded.principal
        )

    assert caught.value.status_code == 404
    assert seeded.session.exec(select(StaffAttendanceRecord)).all() == []


# --- the payloads refuse what cannot be true -------------------------------


def test_the_same_person_twice_in_one_payload_is_refused(seeded):
    """Two statuses for one person would make the answer depend on list order."""
    with pytest.raises(ValidationError):
        AttendanceBulkIn(
            date=DAY,
            records=[
                {"employee_id": seeded.one.id, "status": "present"},
                {"employee_id": seeded.one.id, "status": "absent"},
            ],
        )


def test_on_leave_is_not_a_status_a_caller_may_write(seeded):
    """It is derived from the leave table; storing it is how it goes stale."""
    with pytest.raises(ValidationError):
        AttendanceBulkIn(
            date=DAY, records=[{"employee_id": seeded.one.id, "status": "on_leave"}]
        )


def test_a_register_for_next_year_is_refused(seeded):
    with pytest.raises(ValidationError):
        AttendanceBulkIn(
            date=date.today() + timedelta(days=200),
            records=[{"employee_id": seeded.one.id, "status": "present"}],
        )


def test_an_amend_with_nothing_to_change_is_refused():
    with pytest.raises(ValidationError):
        AttendanceRecordPatch()


def test_the_percentage_is_integer_maths_so_two_machines_agree():
    """No float, no rounding mode: 37/40 is 92%, not 92.5 rounded twice."""
    assert labels.attendance_percent(present=18, half_day=1, marked=20) == 92
    assert labels.attendance_percent(present=0, half_day=0, marked=0) == 0
    assert labels.attendance_percent(present=5, half_day=0, marked=5) == 100
    assert labels.attendance_percent(present=0, half_day=1, marked=4) == 12
