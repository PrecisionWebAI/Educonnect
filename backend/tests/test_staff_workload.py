"""The workload rules: the denominator, the duties, the week and the tiles.

Every test here is a number that is invisible in the browser when it is wrong:

* the utilisation percentage is a share of **the school's own week** when the
  school has stated one, and of what the timetable actually runs when it has not -
  a denominator nobody wrote is how "80% utilised" changed meaning overnight;
* a class teacher's section is listed even when they teach no subject in it (the
  one fact that defines the job, and it used to be missing);
* a duty is either weekly or a single date, never both, and the same duty is not
  filed twice;
* a teacher reads their own week and nobody else's (`404`, not `403`);
* duties are **counted**, never converted into periods - no weight was agreed;
* the analytics tiles are counted over the same rows as the matrix.

Runs on in-memory SQLite, like the rest of this module's suite.
"""

import importlib
from datetime import date, time, timedelta
from types import SimpleNamespace

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
    SubjectTeacher,
)
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels, service as teachers
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.people.teachers.workload import repository, service
from app.domains.people.teachers.workload.models import StaffWorkloadRule
from app.domains.people.teachers.workload.schemas import (
    StaffDutyCreate,
    WorkloadRuleWrite,
)


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
    school = School(
        name=name,
        code=code,
        email="office@test.school",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


@pytest.fixture()
def seeded():
    """One school with a class, a subject, four periods and four people.

    * **Teacher One** runs Class 9-A as class teacher and teaches two periods —
      but is *not* a `subjectteacher`, which is the row the matrix used to drop;
    * **Teacher Two** is the subject teacher and teaches the other two periods;
    * **Teacher Leaver** is off the roll (read-only);
    * **Hod One** holds the read right only.
    """
    session = session_for(engine())
    _roles(session)
    school = _school(session)
    session.info["school_id"] = school.id

    principal = _user(session, "Principal One", school.id, ("principal",))
    one_user, one = _person(session, school.id, "EMP-0001", name="Teacher One")
    two_user, two = _person(session, school.id, "EMP-0002", name="Teacher Two")
    leaver_user, leaver = _person(
        session,
        school.id,
        "EMP-0003",
        name="Teacher Leaver",
        left_on=date(2026, 1, 31),
    )
    hod_user, hod = _person(
        session, school.id, "EMP-0004", name="Hod One", roles=("hod",)
    )

    classname = ClassName(classname="Class 9", level=9)
    section = Section(section_name="A")
    session.add_all([classname, section])
    session.commit()
    session.refresh(classname)
    session.refresh(section)

    room = Classroom(
        class_id=classname.class_id,
        section_id=section.section_id,
        class_teacher_id=one.id,
    )
    physics = Subject(name="Physics", code="PHY")
    session.add_all([room, physics])
    session.commit()
    session.refresh(room)
    session.refresh(physics)

    session.add(
        SubjectTeacher(
            teacher_id=two.id, subject_id=physics.id, classroom_id=room.id
        )
    )
    for index, (day, start) in enumerate(
        (
            (DayOfWeek.monday, time(9, 0)),
            (DayOfWeek.monday, time(10, 0)),
            (DayOfWeek.tuesday, time(9, 0)),
            (DayOfWeek.tuesday, time(10, 0)),
        )
    ):
        session.add(
            TimetablePeriod(
                classroom_id=room.id,
                subject_id=physics.id,
                teacher_id=one.id if index < 2 else two.id,
                day_of_week=day,
                start_time=start,
                end_time=time(start.hour + 1, 0),
            )
        )
    session.commit()

    return SimpleNamespace(
        session=session,
        school=school,
        principal=principal,
        one_user=one_user,
        one=one,
        two_user=two_user,
        two=two,
        leaver_user=leaver_user,
        leaver=leaver,
        hod_user=hod_user,
        hod=hod,
        room=room,
        physics=physics,
    )


def _row(rows, employee_id):
    return next(row for row in rows if row.id == employee_id)


def _duty_input(**extra) -> StaffDutyCreate:
    payload = {
        "duty_type": "exam_duty",
        "title": "Half-Yearly Exam - Hall B",
        "day_of_week": "monday",
        "start_time": time(9, 0),
        "end_time": time(11, 0),
    }
    payload.update(extra)
    return StaffDutyCreate(**payload)


# --- the matrix and its denominator ----------------------------------------


def test_the_timetable_is_the_denominator_until_the_school_states_one(seeded):
    """Without a rule the capacity is what the week actually runs, and it says so."""
    rows = teachers.workload_matrix(seeded.session)
    one = _row(rows, seeded.one.id)

    assert one.periods == 2
    assert one.capacity == 4  # four distinct (day, start) slots in the timetable
    assert one.capacity_source == "timetable"
    assert one.week_slots == 4
    # 2 of 4 = 50%, which is under the 60% under-load line.
    assert one.utilisation == 50
    assert one.band == labels.LIGHT
    assert one.overloaded is False


def test_the_rule_becomes_the_denominator_and_the_week_is_still_reported(seeded):
    """A stated capacity wins; the timetable's own count is still told alongside."""
    service.set_rule(
        seeded.session,
        WorkloadRuleWrite(weekly_periods=8),
        seeded.principal,
    )
    rows = teachers.workload_matrix(seeded.session)
    one = _row(rows, seeded.one.id)

    assert one.capacity == 8
    assert one.capacity_source == "rule"
    # The week still runs four slots - the two numbers are different facts.
    assert one.week_slots == 4
    assert one.utilisation == 25
    assert one.free_periods == 6


def test_a_class_teacher_is_listed_without_teaching_the_subject(seeded):
    """The section they run is a class they hold, `subjectteacher` row or not."""
    rows = teachers.workload_matrix(seeded.session)
    one = _row(rows, seeded.one.id)
    two = _row(rows, seeded.two.id)

    assert one.classes == ["Class 9-A"]
    # Teacher Two teaches there but does not run the section - the assignment is
    # what lists a class for a subject teacher.
    assert two.classes == ["Class 9-A"]
    assert two.subject == "Physics"
    assert one.subject == ""


def test_overload_is_a_flag_because_the_bar_cannot_overflow(seeded):
    """`utilisation` caps at 100, so "over the line" needs its own field."""
    service.set_rule(
        seeded.session,
        WorkloadRuleWrite(weekly_periods=1, overload_percent=100),
        seeded.principal,
    )
    rows = teachers.workload_matrix(seeded.session)
    one = _row(rows, seeded.one.id)

    assert one.utilisation == 100
    assert one.overloaded is True
    assert one.band == labels.OVERLOADED
    assert one.free_periods == 0


def test_no_capacity_is_unassigned_not_a_division_by_zero():
    """A school with no timetable and no rule reports nothing, not `500`."""
    session = session_for(engine())
    _roles(session)
    school = _school(session)
    session.info["school_id"] = school.id
    principal = _user(session, "Principal One", school.id, ("principal",))
    _person(session, school.id, "EMP-0101", name="Teacher One")

    rows = teachers.workload_matrix(session)
    assert len(rows) == 1
    assert rows[0].capacity == 0
    assert rows[0].utilisation == 0
    assert rows[0].band == labels.UNASSIGNED
    assert rows[0].overloaded is False

    analytics = service.analytics(session)
    assert analytics.capacity == 0
    assert analytics.capacity_source == "timetable"
    assert analytics.average_utilisation == 0
    assert service.read_rule(session).is_set is False
    assert principal is not None


def test_duties_are_counted_and_not_converted_into_periods(seeded):
    """The matrix's `periods` never moves because of a duty - no weight exists."""
    before = _row(teachers.workload_matrix(seeded.session), seeded.one.id)

    service.add_duty(seeded.session, seeded.one, _duty_input(), seeded.principal)
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(duty_type="gate_duty", day_of_week="friday", start_time=time(7, 45)),
        seeded.principal,
    )

    after = _row(teachers.workload_matrix(seeded.session), seeded.one.id)
    assert after.duties == 2
    assert after.periods == before.periods == 2
    assert after.utilisation == before.utilisation


def test_an_ended_duty_leaves_the_matrix_but_stays_on_the_file(seeded):
    """A duty whose window closed is history: counted nowhere, readable still."""
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(
            effective_from=date.today() - timedelta(days=90),
            effective_to=date.today() - timedelta(days=30),
        ),
        seeded.principal,
    )

    assert _row(teachers.workload_matrix(seeded.session), seeded.one.id).duties == 0
    assert len(service.duty_reads(seeded.session, seeded.one.id)) == 1


# --- one person's week -----------------------------------------------------


def test_the_week_lists_every_day_and_sorts_by_start_time(seeded):
    """A grid is chronology: Monday 08:00 before Monday 09:00, empty days kept."""
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(day_of_week="monday", start_time=time(8, 0), end_time=time(9, 0)),
        seeded.principal,
    )

    week = service.staff_week(seeded.session, seeded.one.id, seeded.principal)

    assert [day.day for day in week.days] == list(labels.WEEK_DAYS)
    assert week.days[0].day_label == "Monday"
    monday = week.days[0]
    # 08:00 duty, then 09:00 and 10:00 periods - sorted by the clock.
    assert [slot.start for slot in monday.slots] == [
        time(8, 0),
        time(9, 0),
        time(10, 0),
    ]
    assert [slot.kind for slot in monday.slots] == ["duty", "period", "period"]
    assert monday.periods == 2
    assert monday.duties == 1
    assert week.periods == 2
    assert week.duties == 1
    assert week.duty_hours == 1.0
    # Tuesday through Sunday are empty - only Monday holds anything.
    assert week.empty_days == 6
    assert week.name == "Teacher One"


def test_a_dated_duty_lands_on_that_dates_weekday(seeded):
    """An invigilation on a date belongs in that weekday's column, not nowhere."""
    on_date = date(2026, 12, 14)
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(day_of_week=None, on_date=on_date, start_time=time(9, 0)),
        seeded.principal,
    )

    week = service.staff_week(seeded.session, seeded.one.id, seeded.principal)
    column = next(day for day in week.days if day.day == labels.WEEK_DAYS[on_date.weekday()])
    duty = next(slot for slot in column.slots if slot.kind == "duty")
    assert duty.slot == "09:00-11:00"
    assert duty.subject == "Exam Duty"
    assert duty.title == "Half-Yearly Exam - Hall B"


def test_a_standing_duty_gets_its_own_column_and_is_not_a_free_day(seeded):
    """A responsibility with no slot is drawn after the week, not dropped."""
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(
            duty_type="library",
            day_of_week=None,
            start_time=None,
            end_time=None,
        ),
        seeded.principal,
    )

    week = service.staff_week(seeded.session, seeded.one.id, seeded.principal)
    assert week.days[-1].day == "standing"
    assert week.days[-1].day_label == "Standing"
    assert week.days[-1].duties == 1
    assert week.duty_hours == 0.0
    # Seven weekdays still reported, and Tuesday onwards is still free.
    assert week.empty_days == 6


def test_a_teacher_reads_their_own_week_and_nobody_elses(seeded):
    """Out of scope is `404`, never `403`: the API must not confirm an id exists."""
    own = service.staff_week(seeded.session, seeded.one.id, seeded.one_user)
    assert own.id == seeded.one.id

    with pytest.raises(HTTPException) as refused:
        service.staff_week(seeded.session, seeded.two.id, seeded.one_user)
    assert refused.value.status_code == 404


def test_a_leaver_keeps_a_readable_week_but_cannot_be_given_a_duty(seeded):
    week = service.staff_week(seeded.session, seeded.leaver.id, seeded.principal)
    assert week.id == seeded.leaver.id

    with pytest.raises(HTTPException) as refused:
        service.add_duty(
            seeded.session, seeded.leaver, _duty_input(), seeded.principal
        )
    assert refused.value.status_code == 409
    assert "Reactivate" in refused.value.detail


# --- duties: the shape rules ----------------------------------------------


def test_a_duty_is_either_weekly_or_a_single_date():
    """Both at once is not a duty, it is two facts a reader cannot order."""
    with pytest.raises(ValidationError) as refused:
        _duty_input(on_date=date(2026, 12, 14))
    assert "weekly or a single date" in str(refused.value)


def test_a_duty_cannot_end_before_it_starts():
    with pytest.raises(ValidationError) as refused:
        _duty_input(start_time=time(11, 0), end_time=time(9, 0))
    assert "end time must be after" in str(refused.value)


def test_an_unknown_duty_type_lists_the_ones_that_exist():
    """The closed vocabulary lives in `labels`; a typo is a `422`, not a row."""
    with pytest.raises(ValidationError) as refused:
        _duty_input(duty_type="gate")
    assert "exam_duty" in str(refused.value)


def test_an_unknown_day_is_refused():
    with pytest.raises(ValidationError) as refused:
        _duty_input(day_of_week="funday")
    assert "monday" in str(refused.value)


def test_a_day_is_stored_lower_case_however_it_is_typed():
    """`Monday` from a form and `monday` from a select are the same day."""
    assert _duty_input(day_of_week="Monday").day_of_week == "monday"
    assert _duty_input(duty_type="Exam_Duty").duty_type == "exam_duty"


def test_the_same_duty_is_not_filed_twice(seeded):
    """The duplicate check lives in the service - NULLs defeat a unique key here."""
    first = service.add_duty(
        seeded.session, seeded.one, _duty_input(), seeded.principal
    )
    assert first.duty_type_label == "Exam Duty"

    with pytest.raises(HTTPException) as refused:
        service.add_duty(seeded.session, seeded.one, _duty_input(), seeded.principal)
    assert refused.value.status_code == 409
    assert "already on this person's file" in refused.value.detail


def test_a_second_duty_at_a_different_time_is_allowed(seeded):
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(start_time=time(9, 0), end_time=time(11, 0)),
        seeded.principal,
    )
    service.add_duty(
        seeded.session,
        seeded.one,
        _duty_input(start_time=time(14, 0), end_time=time(16, 0)),
        seeded.principal,
    )
    assert len(service.duty_reads(seeded.session, seeded.one.id)) == 2


def test_a_duty_id_from_another_employee_is_not_found(seeded):
    """The row is looked up **within** the employee in the path (`404`)."""
    mine = service.add_duty(
        seeded.session, seeded.one, _duty_input(), seeded.principal
    )

    with pytest.raises(HTTPException) as refused:
        service.remove_duty(seeded.session, seeded.two, mine.id, seeded.principal)
    assert refused.value.status_code == 404
    # It is still there - the refusal must not half-delete anything.
    assert len(service.duty_reads(seeded.session, seeded.one.id)) == 1


# --- who may change the week ----------------------------------------------


def test_only_the_office_sets_the_capacity(seeded):
    """A teacher and an HOD read the matrix; they do not reshape the week."""
    for user in (seeded.two_user, seeded.hod_user):
        with pytest.raises(HTTPException) as refused:
            service.set_rule(
                seeded.session, WorkloadRuleWrite(weekly_periods=24), user
            )
        assert refused.value.status_code == 403

    rule = service.set_rule(
        seeded.session, WorkloadRuleWrite(weekly_periods=24), seeded.principal
    )
    assert rule.weekly_periods == 24
    assert rule.is_set is True
    assert rule.updated_by == "Principal One"


def test_an_hod_may_not_assign_a_duty(seeded):
    with pytest.raises(HTTPException) as refused:
        service.add_duty(seeded.session, seeded.one, _duty_input(), seeded.hod_user)
    assert refused.value.status_code == 403
    assert service.duty_reads(seeded.session, seeded.one.id) == []


def test_the_rule_is_upserted_never_duplicated(seeded):
    """One policy per school: a second PUT updates the row, it does not add one."""
    service.set_rule(
        seeded.session, WorkloadRuleWrite(weekly_periods=24), seeded.principal
    )
    service.set_rule(
        seeded.session,
        WorkloadRuleWrite(weekly_periods=26, overload_percent=110),
        seeded.principal,
    )

    assert len(seeded.session.exec(select(StaffWorkloadRule)).all()) == 1
    rule = service.read_rule(seeded.session)
    assert rule.weekly_periods == 26
    assert rule.overload_percent == 110


def test_underload_must_stay_below_overload():
    """Overlapping thresholds would make every teacher both full and light."""
    with pytest.raises(ValidationError) as refused:
        WorkloadRuleWrite(weekly_periods=24, overload_percent=80, underload_percent=90)
    assert "under-load threshold" in str(refused.value)


# --- the audit trail -------------------------------------------------------


def test_adding_and_removing_a_duty_is_written_down(seeded):
    """Duties are audited; the rule is not - it carries its own `updated_by`.

    The audit table is keyed on an employee, and a capacity rule is a school-level
    policy: there is no person to file it against.
    """
    duty = service.add_duty(
        seeded.session, seeded.one, _duty_input(), seeded.principal
    )
    service.remove_duty(seeded.session, seeded.one, duty.id, seeded.principal)

    lines = seeded.session.exec(
        select(StaffAuditLog).where(StaffAuditLog.employee_id == seeded.one.id)
    ).all()
    assert [line.action for line in lines] == ["created", "deleted"]
    assert {line.section for line in lines} == {"duty"}
    assert lines[0].summary == (
        "Added Exam Duty: Half-Yearly Exam - Hall B (Monday 09:00-11:00)"
    )
    assert lines[1].summary.startswith("Removed Exam Duty")
    assert lines[0].changed_by_user_id == seeded.principal.id


# --- analytics -------------------------------------------------------------


def test_the_tiles_count_the_same_rows_the_matrix_shows(seeded):
    analytics = service.analytics(seeded.session)
    rows = teachers.workload_matrix(seeded.session)

    # Teacher One, Teacher Two, Teacher Leaver and Hod One - an HOD is a teaching
    # post, so the roll is four and the leaver is still on it.
    assert analytics.staff == len(rows) == 4
    assert analytics.total_periods == sum(row.periods for row in rows) == 4
    assert analytics.average_periods == 1.0
    assert analytics.unassigned == 2  # the leaver and the HOD teach nothing yet
    assert analytics.overloaded == 0
    assert analytics.weekly_periods_rule is None
    assert analytics.capacity == analytics.week_slots == 4
    assert [row.department for row in analytics.by_department] == ["Science"]
    science = analytics.by_department[0]
    assert (science.staff, science.periods, science.overloaded) == (4, 4, 0)
    # 4 periods over 4 teachers x 4 slots = 25%: one division, not a mean of
    # percentages.
    assert science.utilisation == 25
    assert analytics.average_utilisation == 25


def test_the_department_split_is_ascending_and_adds_up(seeded):
    service.add_duty(seeded.session, seeded.two, _duty_input(), seeded.principal)
    seeded.two.department = "Arts"
    seeded.session.add(seeded.two)
    seeded.session.commit()

    analytics = service.analytics(seeded.session)
    assert [row.department for row in analytics.by_department] == ["Arts", "Science"]
    assert sum(row.staff for row in analytics.by_department) == analytics.staff
    assert (
        sum(row.periods for row in analytics.by_department) == analytics.total_periods
    )
    assert analytics.duties == 1
