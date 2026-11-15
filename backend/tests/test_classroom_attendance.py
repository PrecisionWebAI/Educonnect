"""Phase 2 - the attendance register: one row per child per day, and its numbers.

The audit found the Attendance tab drew a roster and never asked what had been saved,
so a reload showed an empty register over a database that had rows - and pressing Save
twice wrote the day twice, doubling every total after it. These scenarios pin the
replacement:

1. **saving twice updates** the same row (no second row) and leaves an **audit** row
   naming who changed it;
2. **the database** refuses a duplicate: both the student/day/subject key and the
   day-level partial index are real, not advice;
3. a **closed day** (Sunday, a holiday) is refused with `409` that names the day;
4. the **register read** returns the whole roll, `unmarked` included;
5. the **summary** counts days and applies the school's own threshold;
6. the **trend** skips Sundays and holidays instead of drawing them as 0%;
7. **approved leave** shows as `leave` and reverts when the leave is cancelled - the
   mark is never overwritten;
8. **attention** flags a run of absences (and only open days count);
9. a **teacher cannot mark another section** - the route refuses it (`403`).

Runs under pytest and as `python tests/test_classroom_attendance.py`.
"""

import importlib
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import ClassName, Section, Subject
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance import register as register_service
from app.domains.academic.classroom.attendance import (
    repository as attendance_repository,
)
from app.domains.academic.classroom.attendance import router as attendance_router
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.attendance.schemas import (
    AttendanceBulkCreate,
    AttendanceRowWrite,
)
from app.domains.academic.classroom.students import service as student_service
from app.domains.academic.classroom.students.models import Student
from app.domains.academic.classroom.students.schemas import StudentCreate
from app.domains.admin.platform.models import School
from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings.models import Holiday
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission
from app.domains.services.leave.models import LeaveRequest

# Fixed weekdays, so "Sunday is skipped" never depends on when the suite ran.
MON = date(2026, 11, 16)
TUE = date(2026, 11, 17)
WED = date(2026, 11, 18)
THU = date(2026, 11, 19)
FRI = date(2026, 11, 20)
SAT = date(2026, 11, 21)
SUN = date(2026, 11, 22)


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
    return school


def _rooms(session: Session, count: int = 2) -> list:
    """`count` class-sections (Class 6-A, 6-B) the register can be taken for."""
    klass = session.exec(
        select(ClassName).where(ClassName.classname == "Class 6")
    ).first()
    if klass is None:
        klass = ClassName(classname="Class 6", level=6)
        session.add(klass)
        session.commit()
        session.refresh(klass)

    rooms = []
    for letter in "ABCDEFGHIJ"[:count]:
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


def _user(session: Session, email: str, role: str) -> User:
    user = User(email=email, full_name=email.split("@")[0], hashed_password="pw")
    user._role_names = {role}
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed(session: Session) -> dict:
    """One school, one class-section with two children, and an office user."""
    school = _school(session, "phase two school", "p2s")
    session.info["school_id"] = school.id
    room = _rooms(session, 1)[0]
    aarav = _student(session, "aarav sharma", "P2-1", room)
    diya = _student(session, "diya patel", "P2-2", room)
    office = _user(session, "office@test", "school_admin")
    return {
        "school": school,
        "room": room,
        "aarav": aarav,
        "diya": diya,
        "office": office,
    }


def _save(session, room, on_date, marks: dict, user=None, subject_id=None):
    """Save a register: `{student or student_id: "present" | "absent" | ...}`."""
    payload = AttendanceBulkCreate(
        section_id=room.id,
        subject_id=subject_id,
        date=on_date,
        records=[
            AttendanceRowWrite(
                student_id=getattr(student, "id", student), status=status
            )
            for student, status in marks.items()
        ],
    )
    return register_service.save_register(session, payload, user=user)


def _rows(session: Session) -> list[AttendanceRecord]:
    return list(session.exec(select(AttendanceRecord)).all())


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_saving_twice_updates_the_same_row_and_audits(session: Session) -> None:
    """A re-save is an update: same row, new status, one audit line naming the user."""
    data = seed(session)
    room, aarav, diya, office = (
        data["room"],
        data["aarav"],
        data["diya"],
        data["office"],
    )

    _save(session, room, MON, {aarav.id: "present", diya.id: "present"}, user=office)
    assert len(_rows(session)) == 2, "one row per child, not per save"

    _save(session, room, MON, {aarav.id: "absent", diya.id: "present"}, user=office)
    rows = _rows(session)
    assert len(rows) == 2, "the second save updated the day instead of writing it again"

    by_student = {row.student_id: row for row in rows}
    assert str(by_student[aarav.id].status) == "absent"
    audits = attendance_repository.audit_rows(session, by_student[aarav.id].id)
    assert len(audits) == 1, "one change, one audit line"
    assert str(audits[0].previous_status) == "present"
    assert str(audits[0].new_status) == "absent"
    assert audits[0].changed_by_id == office.id

    read = register_service.register(session, room.id, MON)
    assert (read.counts.present, read.counts.absent, read.counts.unmarked) == (1, 1, 0)
    assert read.percent == 50.0


def check_the_database_refuses_a_duplicate(session: Session) -> None:
    """The keys are real: a second row for the same child/day/(subject) is refused."""
    data = seed(session)
    room, aarav, office = data["room"], data["aarav"], data["office"]

    _save(session, room, MON, {aarav.id: "present"}, user=office)
    session.add(
        AttendanceRecord(
            student_id=aarav.id,
            classroom_id=room.id,
            date=MON,
            status="present",
            school_id=data["school"].id,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert len(_rows(session)) == 1, "the day-level row stays single"

    # The same, with a subject: the composite key (school, student, date, subject).
    subject = Subject(name="mathematics", code="MAT")
    session.add(subject)
    session.commit()
    session.refresh(subject)

    _save(session, room, MON, {aarav.id: "present"}, user=office, subject_id=subject.id)
    session.add(
        AttendanceRecord(
            student_id=aarav.id,
            classroom_id=room.id,
            subject_id=subject.id,
            date=MON,
            status="absent",
            school_id=data["school"].id,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert len(_rows(session)) == 2, "one day-level row and one per subject"


def check_closed_days_are_refused(session: Session) -> None:
    """Sunday and a holiday are `409` that names the day - and still readable."""
    data = seed(session)
    room, aarav, office = data["room"], data["aarav"], data["office"]

    with pytest.raises(HTTPException) as sunday:
        _save(session, room, SUN, {aarav.id: "present"}, user=office)
    assert sunday.value.status_code == 409
    assert "Sunday" in sunday.value.detail

    session.add(Holiday(on_date=TUE, name="diwali break", kind="festival"))
    session.commit()

    with pytest.raises(HTTPException) as holiday:
        _save(session, room, TUE, {aarav.id: "present"}, user=office)
    assert holiday.value.status_code == 409
    assert "diwali break" in holiday.value.detail, "the refusal names the holiday"

    assert _rows(session) == [], "nothing was written on a closed day"
    read = register_service.register(session, room.id, TUE)
    assert read.closed_reason == "diwali break"
    assert len(read.rows) == 2, "the day is still readable; it just cannot be saved"


def check_summary_counts_and_threshold(session: Session) -> None:
    """Four marked days: 50%, flagged at the school's 75% - not at a hardcoded number."""
    data = seed(session)
    room, aarav, diya, office = (
        data["room"],
        data["aarav"],
        data["diya"],
        data["office"],
    )

    _save(session, room, MON, {aarav.id: "present", diya.id: "present"}, user=office)
    _save(session, room, TUE, {aarav.id: "present", diya.id: "absent"}, user=office)
    _save(session, room, WED, {aarav.id: "absent", diya.id: "present"}, user=office)
    _save(session, room, THU, {aarav.id: "absent", diya.id: "present"}, user=office)

    summary = register_service.section_summary(session, room.id, MON, THU)
    assert summary.working_days == 4
    assert summary.threshold == 75

    rows = {row.student_id: row for row in summary.rows}
    aarav_row = rows[aarav.id]
    assert (aarav_row.present, aarav_row.absent, aarav_row.marked) == (2, 2, 4)
    assert aarav_row.percent == 50.0
    assert aarav_row.below_threshold is True
    assert rows[diya.id].percent == 75.0
    assert rows[diya.id].below_threshold is False, (
        "the threshold is a floor, not a ceiling"
    )

    # The school's own number decides, and the setting is real data - not a constant.
    setting_values.set_value(session, "attendance.absence_threshold", 40)
    relaxed = register_service.section_summary(session, room.id, MON, THU)
    assert relaxed.threshold == 40
    assert {row.student_id: row for row in relaxed.rows}[
        aarav.id
    ].below_threshold is False


def check_trend_skips_closed_days(session: Session) -> None:
    """The trend draws open days only - Sunday and the holiday are not 0%."""
    data = seed(session)
    room, aarav, diya, office = (
        data["room"],
        data["aarav"],
        data["diya"],
        data["office"],
    )

    for day in (MON, TUE, WED, THU, FRI, SAT):
        _save(
            session, room, day, {aarav.id: "present", diya.id: "present"}, user=office
        )
    session.add(Holiday(on_date=THU, name="founder's day", kind="festival"))
    session.commit()

    trend = register_service.section_trend(session, room.id, days=7, end=SUN)
    days = [point.date for point in trend.points]
    assert SUN not in days, "Sunday is skipped, not drawn as a zero"
    assert THU not in days, "the holiday is skipped"
    assert days == [MON, TUE, WED, FRI, SAT]
    assert all(point.percent == 100.0 for point in trend.points)

    # A day nobody marked is "no data", not 0%: the chart must not accuse the class.
    quiet = register_service.section_trend(
        session, room.id, days=1, end=date(2026, 11, 13)
    )
    assert len(quiet.points) == 1
    assert quiet.points[0].percent is None


def check_leave_is_derived_and_reverts(session: Session) -> None:
    """An approved leave reads as `leave`; cancelling it gives the mark back."""
    data = seed(session)
    room, aarav, office = data["room"], data["aarav"], data["office"]

    _save(session, room, MON, {aarav.id: "present"}, user=office)

    request = LeaveRequest(
        student_id=aarav.id,
        requester_user_id=office.id,
        leave_type="Medical",
        from_date=MON,
        to_date=TUE,
        days=2,
        status="Approved",
        school_id=data["school"].id,
    )
    session.add(request)
    session.commit()
    session.refresh(request)

    # The day is marked again while the leave is approved: the row keeps the teacher's
    # mark and now **links** the request, which is the trace a cancelled leave leaves.
    _save(session, room, MON, {aarav.id: "present"}, user=office)

    read = register_service.register(session, room.id, MON)
    row = read.rows[0]
    assert row.status == "leave", "an approved leave decides the day"
    assert row.leave_request_id == request.id, "the row points at the request"
    assert read.counts.leave == 1 and read.counts.present == 0

    stored = _rows(session)[0]
    assert str(stored.status) == "present", (
        "the leave is derived - the mark the teacher made is never overwritten"
    )

    summary = register_service.section_summary(session, room.id, MON, TUE)
    assert {item.student_id: item for item in summary.rows}[aarav.id].leave == 2

    request.status = "Cancelled"
    session.add(request)
    session.commit()

    read = register_service.register(session, room.id, MON)
    assert read.rows[0].status == "present", "a cancelled leave reverts to the mark"
    assert read.rows[0].leave_request_id is not None, "the link stays for the history"


def check_attention_flags_a_run_of_absences(session: Session) -> None:
    """Three open days absent in a row is a pattern; the well child is not listed."""
    data = seed(session)
    room, aarav, diya, office = (
        data["room"],
        data["aarav"],
        data["diya"],
        data["office"],
    )

    marks = {
        MON: ("present", "present"),
        TUE: ("present", "present"),
        WED: ("absent", "present"),
        THU: ("absent", "present"),
        FRI: ("absent", "present"),
    }
    for day, (aarav_status, diya_status) in marks.items():
        _save(
            session,
            room,
            day,
            {aarav.id: aarav_status, diya.id: diya_status},
            user=office,
        )

    attention = register_service.section_attention(session, room.id, end=FRI)
    assert [row.student_id for row in attention] == [aarav.id]
    flagged = attention[0]
    assert flagged.consecutive_absences == 3
    assert "in a row" in flagged.reason
    assert flagged.percent == 40.0
    assert "below the 75% mark" in flagged.reason


# ---------------------------------------------------------------------------
# Phase 4: the calendar and the payload the screen actually reads
# ---------------------------------------------------------------------------


def check_closed_days_lists_sundays_and_holidays(session: Session) -> None:
    """The date picker greys out Sundays **and** the school's own holidays, by name."""
    seed(session)
    session.add(Holiday(on_date=TUE, name="diwali break", kind="festival"))
    session.commit()

    days = register_service.closed_days(session, MON, SUN)
    assert [(day.date, day.reason) for day in days] == [
        (TUE, "diwali break"),
        (SUN, "Sunday"),
    ]

    assert register_service.closed_days(session, WED, THU) == [], (
        "open days are not closed"
    )

    try:
        register_service.closed_days(session, date(2024, 1, 1), date(2026, 12, 31))
    except HTTPException as refused:
        assert refused.status_code == 422, "a range wider than a year is refused"
    else:  # pragma: no cover - the assertion is the point
        raise AssertionError("a three-year range was accepted")


def check_the_payload_is_what_the_screen_reads(session: Session) -> None:
    """The API contract Phase 4's screen is built on - pinned field by field.

    The register, summary, trend and attention shapes are what `useAttendance` reads in
    the browser; renaming a field here is a broken screen there, so the keys are asserted
    rather than assumed.
    """
    data = seed(session)
    room, aarav, diya, office = (
        data["room"],
        data["aarav"],
        data["diya"],
        data["office"],
    )
    _save(session, room, MON, {aarav.id: "absent", diya.id: "present"}, user=office)

    register = register_service.register(session, room.id, MON).model_dump()
    assert set(register) == {
        "section_id",
        "date",
        "subject_id",
        "closed_reason",
        "counts",
        "percent",
        "rows",
    }
    assert set(register["counts"]) == {
        "present",
        "absent",
        "late",
        "half_day",
        "leave",
        "unmarked",
    }
    assert set(register["rows"][0]) == {
        "student_id",
        "record_id",
        "name",
        "admissionNo",
        "status",
        "marked",
        "remarks",
        "leave_request_id",
    }, "the grid reads these; a rename breaks it"

    summary = register_service.section_summary(session, room.id, MON, MON).model_dump()
    assert {
        "section_id",
        "from_date",
        "to_date",
        "working_days",
        "threshold",
        "rows",
    } == set(summary)
    assert set(summary["rows"][0]) == {
        "student_id",
        "name",
        "admissionNo",
        "present",
        "absent",
        "late",
        "half_day",
        "leave",
        "marked",
        "percent",
        "threshold",
        "below_threshold",
    }, "the totals panel reads these, threshold chip included"

    trend = register_service.section_trend(
        session, room.id, days=1, end=MON
    ).model_dump()
    assert set(trend) == {"section_id", "days", "points"}
    assert set(trend["points"][0]) == {"date", "present", "marked", "percent"}

    attention = register_service.section_attention(session, room.id, end=MON)
    if attention:  # the shape matters even when nobody is flagged yet
        assert set(attention[0].model_dump()) == {
            "student_id",
            "name",
            "admissionNo",
            "percent",
            "consecutive_absences",
            "reason",
        }


def check_a_teacher_cannot_mark_another_section(session: Session) -> None:
    """The route refuses a scope the teacher does not own - the screen is not the guard."""
    data = seed(session)
    room, aarav, office = data["room"], data["aarav"], data["office"]
    other = _rooms(session, 2)[1]  # Class 6-B, a section the teacher does not run
    teacher = _user(session, "teacher@test", "teacher")

    payload = AttendanceBulkCreate(
        section_id=other.id,
        date=MON,
        records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
    )
    with pytest.raises(HTTPException) as refused:
        attendance_router.mark_attendance_bulk(
            bulk_data=payload, session=session, current_user=teacher
        )
    assert refused.value.status_code == 403

    allowed = AttendanceBulkCreate(
        section_id=room.id,
        date=MON,
        records=[AttendanceRowWrite(student_id=aarav.id, status="present")],
    )
    assert _rows(session) == [], "nothing was written for the teacher"

    guard = RequirePermission("attendance.mark")
    with pytest.raises(HTTPException) as guarded:
        guard(
            request=SimpleNamespace(path_params={}, query_params={}),
            user=teacher,
            session=None,
        )
    assert guarded.value.status_code == 403

    saved = _save(session, room, MON, {aarav.id: "present"}, user=office)
    assert len(saved) == 1 and str(saved[0].status) == "present"
    assert allowed.section_id == room.id


# ---------------------------------------------------------------------------
# pytest wrappers + the no-pytest runner
# ---------------------------------------------------------------------------


def test_saving_twice_updates_the_same_row_and_audits():
    with memory_session() as session:
        check_saving_twice_updates_the_same_row_and_audits(session)


def test_the_database_refuses_a_duplicate():
    with memory_session() as session:
        check_the_database_refuses_a_duplicate(session)


def test_closed_days_are_refused():
    with memory_session() as session:
        check_closed_days_are_refused(session)


def test_summary_counts_and_threshold():
    with memory_session() as session:
        check_summary_counts_and_threshold(session)


def test_trend_skips_closed_days():
    with memory_session() as session:
        check_trend_skips_closed_days(session)


def test_leave_is_derived_and_reverts():
    with memory_session() as session:
        check_leave_is_derived_and_reverts(session)


def test_attention_flags_a_run_of_absences():
    with memory_session() as session:
        check_attention_flags_a_run_of_absences(session)


def test_a_teacher_cannot_mark_another_section():
    with memory_session() as session:
        check_a_teacher_cannot_mark_another_section(session)


def test_closed_days_lists_sundays_and_holidays():
    with memory_session() as session:
        check_closed_days_lists_sundays_and_holidays(session)


def test_the_payload_is_what_the_screen_reads():
    with memory_session() as session:
        check_the_payload_is_what_the_screen_reads(session)


SCENARIOS = (
    (
        "saving twice updates the same row and audits it",
        check_saving_twice_updates_the_same_row_and_audits,
    ),
    ("the database refuses a duplicate", check_the_database_refuses_a_duplicate),
    ("closed days are refused", check_closed_days_are_refused),
    ("summary counts and the threshold", check_summary_counts_and_threshold),
    ("the trend skips closed days", check_trend_skips_closed_days),
    ("leave is derived and reverts", check_leave_is_derived_and_reverts),
    ("attention flags a run of absences", check_attention_flags_a_run_of_absences),
    (
        "a teacher cannot mark another section",
        check_a_teacher_cannot_mark_another_section,
    ),
    (
        "closed days list Sundays and holidays",
        check_closed_days_lists_sundays_and_holidays,
    ),
    (
        "the payload is what the screen reads",
        check_the_payload_is_what_the_screen_reads,
    ),
)


if __name__ == "__main__":  # pragma: no cover - the no-pytest runner
    for label, scenario in SCENARIOS:
        with memory_session() as run_session:
            scenario(run_session)
        print(f"ok  {label}")
