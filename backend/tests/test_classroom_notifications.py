"""Phase 3 - the notification foundation: one writer, one message per event per person.

The bell existed but nothing said what a row was *about*, every service wrote its own
`Notification(...)`, and "one message per event" was a hope. These scenarios pin the
replacement:

1. **a guardian hears about an absence once** - saving the same register again writes
   nothing new (the dedupe key does the work, not an `if`);
2. **an unrelated parent hears nothing** - recipients come from
   `student_guardian_relationship`, not from a list the caller assembled;
3. **a run of absences reaches the office** - class teacher + principal, once per day;
4. **a failing notification does not fail the attendance save** (rule 9);
5. **the substitution flow uses the same writer** (no second `Notification(...)`);
6. **the scheduler runs a job, and survives one that raises**.

Runs under pytest and as `python tests/test_classroom_notifications.py`.
"""

import importlib
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance import register as register_service
from app.domains.academic.classroom.attendance.schemas import (
    AttendanceBulkCreate,
    AttendanceRowWrite,
)
from app.domains.academic.classroom.students import service as student_service
from app.domains.academic.classroom.students.models import (
    Guardian,
    Student,
    StudentGuardianRelationship,
)
from app.domains.academic.classroom.students.schemas import StudentCreate
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.main.notifications import events
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee

MON = date(2026, 11, 16)
TUE = date(2026, 11, 17)
WED = date(2026, 11, 18)
THU = date(2026, 11, 19)


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


def _room(session: Session) -> object:
    klass = session.exec(
        select(ClassName).where(ClassName.classname == "Class 6")
    ).first()
    if klass is None:
        klass = ClassName(classname="Class 6", level=6)
        session.add(klass)
        session.commit()
        session.refresh(klass)
    section = session.exec(select(Section).where(Section.section_name == "A")).first()
    if section is None:
        section = Section(section_name="A")
        session.add(section)
        session.commit()
        session.refresh(section)
    return ensure_room(session, klass.class_id, section.section_id)


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


def _guardian(session: Session, student: Student, parent: User, name: str) -> Guardian:
    guardian = session.exec(select(Guardian).where(Guardian.name == name)).first()
    if guardian is None:
        guardian = Guardian(name=name, phone=f"90000{len(name):05d}", user_id=parent.id)
        session.add(guardian)
        session.commit()
        session.refresh(guardian)
    session.add(
        StudentGuardianRelationship(
            student_id=student.id, guardian_id=guardian.id, is_primary=True
        )
    )
    session.commit()
    return guardian


def seed(session: Session) -> dict:
    """One school: a section with a class teacher, a child + parent, a head, an outsider."""
    school = School(name="phase three school", code="p3s", email="p3s@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    room = _room(session)

    teacher_user = _user(session, "teacher@test")
    employee = Employee(
        user_id=teacher_user.id,
        employee_code="EMP-P3-1",
        department="Science",
        joining_date=date(2024, 6, 1),
        school_id=school.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    room.class_teacher_id = employee.id
    session.add(room)
    session.commit()

    head = _user(session, "principal@test")
    session.add(UserRole(user_id=head.id, role_id=_role(session, "principal").id))
    session.commit()

    aarav = _student(session, "aarav sharma", "P3-1", room)
    parent = _user(session, "parent@test")
    _guardian(session, aarav, parent, "meera singh")

    kabir = _student(session, "kabir singh", "P3-2", room)
    other_parent = _user(session, "other@test")
    _guardian(session, kabir, other_parent, "other parent")

    return {
        "school": school,
        "room": room,
        "aarav": aarav,
        "kabir": kabir,
        "parent": parent,
        "other_parent": other_parent,
        "teacher": teacher_user,
        "head": head,
    }


def _save(session, room, on_date, marks: dict):
    payload = AttendanceBulkCreate(
        section_id=room.id,
        date=on_date,
        records=[
            AttendanceRowWrite(student_id=student_id, status=status)
            for student_id, status in marks.items()
        ],
    )
    return register_service.save_register(session, payload)


def _messages(session: Session, user_id=None) -> list[Notification]:
    statement = select(Notification)
    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)
    return list(session.exec(statement).all())


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------


def check_a_guardian_hears_about_an_absence_once(session: Session) -> None:
    """One absence, one message - and saving the same day again says nothing new."""
    data = seed(session)
    room, aarav, kabir, parent = (
        data["room"],
        data["aarav"],
        data["kabir"],
        data["parent"],
    )

    _save(session, room, MON, {aarav.id: "absent", kabir.id: "present"})
    mine = _messages(session, parent.id)
    assert len(mine) == 1, "the guardian is told once"

    message = mine[0]
    assert message.event_type == events.EVENT_ATTENDANCE_ABSENT
    assert message.dedupe_key == f"attendance:{aarav.id}:{MON.isoformat()}:absent"
    assert message.kind == "Attendance"
    assert message.channel == "in_app"
    assert (message.entity_type, message.entity_id) == ("student", aarav.id)
    assert "aarav sharma" in message.body and MON.isoformat() in message.body

    _save(session, room, MON, {aarav.id: "absent", kabir.id: "present"})
    _save(session, room, MON, {aarav.id: "absent", kabir.id: "present"})
    assert len(_messages(session, parent.id)) == 1, "a re-save is not a new event"


def check_an_unrelated_parent_hears_nothing(session: Session) -> None:
    """Recipients come from the link table: another family's absence is not mine."""
    data = seed(session)
    _save(session, data["room"], MON, {data["aarav"].id: "absent"})

    assert _messages(session, data["other_parent"].id) == []
    assert len(_messages(session, data["parent"].id)) == 1


def check_a_run_of_absences_reaches_the_office(session: Session) -> None:
    """Three open days in a row: the class teacher and the head, once for that day."""
    data = seed(session)
    room, aarav, kabir = data["room"], data["aarav"], data["kabir"]

    for day in (MON, TUE, WED):
        _save(session, room, day, {aarav.id: "absent", kabir.id: "present"})

    for role in ("teacher", "head"):
        user_id = data[role].id
        consecutive = [
            message
            for message in _messages(session, user_id)
            if message.event_type == events.EVENT_ATTENDANCE_CONSECUTIVE
        ]
        assert len(consecutive) == 1, f"{role} hears about the run once"
        assert consecutive[0].dedupe_key == f"consecutive:{aarav.id}:{WED.isoformat()}"
        assert "3 open days in a row" in consecutive[0].body
        assert consecutive[0].kind == "Attendance"

    family = _messages(session, data["parent"].id)
    assert len(family) == 3, "one message per absent day, not one per save"


def check_a_failing_notification_does_not_fail_the_save(session: Session) -> None:
    """Rule 9: the register is the record; the bell is a courtesy."""
    data = seed(session)
    original = events._write

    def boom(_session: Session, _rows: list[Notification]) -> None:
        raise RuntimeError("the bell is broken")

    events._write = boom
    try:
        saved = _save(session, data["room"], MON, {data["aarav"].id: "absent"})
    finally:
        events._write = original

    assert len(saved) == 1, "the register was still saved"
    assert _messages(session) == [], "and nothing was half-written"


def check_only_one_module_writes_notifications(
    session: Session | None = None,
) -> None:
    """One writer: no service constructs a `Notification` behind the event service."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    writers: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for _match in re.finditer(r"(?<!class )Notification\(", text):
            writers.append(str(path.relative_to(root)).replace("\\", "/"))

    assert writers, "the notification writer must exist"
    assert set(writers) == {"domains/main/notifications/events.py"}, (
        f"only the notification service may build a row, found: {sorted(set(writers))}"
    )


def check_the_scheduler_survives_a_failing_job(session: Session | None = None) -> None:
    """The loop is a schedule, not a house of cards: one bad job does not stop it."""
    from app.core import scheduler as sched

    ran: list[str] = []

    def good(_session: Session) -> None:
        ran.append("good")

    def bad(_session: Session) -> None:
        raise RuntimeError("this job is broken")

    sched.JOBS.clear()
    try:
        sched.register_job("phase3-good", good)
        sched.register_job("phase3-bad", bad)
        sched.register_job("phase3-good", good)  # idempotent by name
        assert len(sched.JOBS) == 2, "a name is registered once"
        done = sched.run_once()
    finally:
        sched.JOBS.clear()

    assert ran == ["good"] and done == 1, "the good job ran, the bad one was logged"


# ---------------------------------------------------------------------------
# pytest wrappers + the no-pytest runner
# ---------------------------------------------------------------------------


def test_a_guardian_hears_about_an_absence_once():
    with memory_session() as session:
        check_a_guardian_hears_about_an_absence_once(session)


def test_an_unrelated_parent_hears_nothing():
    with memory_session() as session:
        check_an_unrelated_parent_hears_nothing(session)


def test_a_run_of_absences_reaches_the_office():
    with memory_session() as session:
        check_a_run_of_absences_reaches_the_office(session)


def test_a_failing_notification_does_not_fail_the_save():
    with memory_session() as session:
        check_a_failing_notification_does_not_fail_the_save(session)


def test_only_one_module_writes_notifications():
    check_only_one_module_writes_notifications()


def test_the_scheduler_survives_a_failing_job():
    check_the_scheduler_survives_a_failing_job()


SCENARIOS = (
    (
        "a guardian hears about an absence once",
        check_a_guardian_hears_about_an_absence_once,
    ),
    ("an unrelated parent hears nothing", check_an_unrelated_parent_hears_nothing),
    (
        "a run of absences reaches the office",
        check_a_run_of_absences_reaches_the_office,
    ),
    (
        "a failing notification does not fail the save",
        check_a_failing_notification_does_not_fail_the_save,
    ),
    (
        "only one module writes notifications",
        check_only_one_module_writes_notifications,
    ),
    (
        "the scheduler survives a failing job",
        check_the_scheduler_survives_a_failing_job,
    ),
)


if __name__ == "__main__":  # pragma: no cover - the no-pytest runner
    for label, scenario in SCENARIOS:
        with memory_session() as run_session:
            scenario(run_session)
        print(f"ok  {label}")
