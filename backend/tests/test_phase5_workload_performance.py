"""Phase 5: the two derived figures - what a week taught, and what a score means.

Every test here fails for a rule the phase added:

* **"completed" is the log, not the timetable** - `classlog` rows inside the week are
  what actually happened; the timetable is the plan;
* **a substitute period counts only when it is approved** - a proposed cover is not
  load yet;
* **"no data" is `None`, not 0** - an unmarked register or an unplanned syllabus
  must not score a teacher at zero, and the overall score is `None` when nothing is
  known;
* **staff have no syllabus component at all** (0.9) - their job has no syllabus.

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.homework.models import ClassLog
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as people_labels
from app.domains.people.teachers.models import TeacherReview
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.substitution.models import SubstitutionAssignment
from app.domains.people.teachers.workload import repository as workload_repository


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


def _session(created) -> Session:
    return Session(created, expire_on_commit=False)


def _school(session: Session) -> School:
    for codename in ("teacher", "school_admin", "accountant"):
        if not session.exec(select(Role).where(Role.codename == codename)).first():
            session.add(Role(codename=codename, label=codename.title()))
    school = School(
        name="School P5",
        code="P5",
        email="office@p5.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


def _employee(session: Session, school: School, code: str, role: str = "teacher"):
    user = User(
        email=f"{code.lower()}@p5.test",
        full_name=f"Person {code}",
        hashed_password="x",
        school_id=school.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    grant_role(session, user, role)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2023, 6, 1),
        school_id=school.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


def test_completed_is_the_log_and_remaining_is_the_plan():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, teacher = _employee(session, school, "EMP-0001")
        today = date.today()
        week_from = today - timedelta(days=today.weekday())
        week_to = week_from + timedelta(days=6)

        for day in (week_from, week_from + timedelta(days=1)):
            session.add(
                ClassLog(
                    classroom_id=uuid4(),
                    teacher_id=teacher.id,
                    date=day,
                    note="Chapter 4",
                    school_id=school.id,
                )
            )
        session.commit()

        completed = workload_repository.completed_counts(
            session, [teacher.id], week_from, week_to
        )
        assert completed[teacher.id] == 2
        # A day outside the window does not count.
        outside = workload_repository.completed_counts(
            session,
            [teacher.id],
            week_from + timedelta(days=7),
            week_to + timedelta(days=7),
        )
        assert outside == {}


def test_a_substitute_period_counts_only_when_it_is_approved():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, absent = _employee(session, school, "EMP-0001")
        _, stand_in = _employee(session, school, "EMP-0002")
        today = date.today()
        week_from = today - timedelta(days=today.weekday())
        week_to = week_from + timedelta(days=6)

        from app.domains.people.teachers.substitution.models import (
            SubstitutionRequest,
        )

        absence = SubstitutionRequest(
            employee_id=absent.id,
            on_date=today,
            reason="Fever",
            school_id=school.id,
        )
        session.add(absence)
        session.commit()
        session.refresh(absence)

        session.add_all(
            [
                SubstitutionAssignment(
                    request_id=absence.id,
                    period_id=uuid4(),
                    on_date=today,
                    absent_employee_id=absent.id,
                    substitute_employee_id=stand_in.id,
                    status=people_labels.APPROVED,
                    school_id=school.id,
                ),
                SubstitutionAssignment(
                    request_id=absence.id,
                    period_id=uuid4(),
                    on_date=today,
                    absent_employee_id=absent.id,
                    substitute_employee_id=stand_in.id,
                    status="Assigned",
                    school_id=school.id,
                ),
            ]
        )
        session.commit()

        counts = workload_repository.substitute_counts(
            session, [stand_in.id], week_from, week_to
        )
        assert counts[stand_in.id] == 1




# --- performance components -------------------------------------------------


def test_no_data_is_none_and_a_known_component_still_scores():
    from app.domains.people.teachers.appraisal import performance as perf

    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, teacher = _employee(session, school, "EMP-0001")
        today = date.today()

        # A marked register: 3 present out of 3 -> 100%.
        for offset in range(3):
            session.add(
                StaffAttendanceRecord(
                    employee_id=teacher.id,
                    date=today - timedelta(days=offset),
                    status=people_labels.PRESENT,
                    school_id=school.id,
                )
            )
        # One review of 4/5 -> 80%.
        session.add(
            TeacherReview(
                teacher_id=teacher.id,
                rating=4,
                reviewer_role="Parent",
                school_id=school.id,
            )
        )
        session.commit()

        row = next(item for item in perf.performance(session) if item.id == teacher.id)
        by_key = {item.key: item for item in row.components}
        assert by_key["attendance"].value == 100
        assert by_key["reviews"].value == 80
        # No syllabus rows -> no data, not 0%.
        assert by_key["syllabus"].value is None
        assert by_key["syllabus"].display == "no data"
        # Score = weighted over the two available components.
        assert row.score == round((100 * 0.3 + 80 * 0.4) / 0.7)


def test_a_person_with_nothing_recorded_scores_none():
    from app.domains.people.teachers.appraisal import performance as perf

    created = engine()
    with _session(created) as session:
        school = _school(session)
        _, teacher = _employee(session, school, "EMP-0001")

        row = next(item for item in perf.performance(session) if item.id == teacher.id)
        assert row.score is None
        assert all(item.value is None for item in row.components)


def test_staff_have_no_syllabus_component():
    from app.domains.people.teachers.appraisal import performance as perf

    created = engine()
    with _session(created) as session:
        school = _school(session)
        _employee(session, school, "EMP-0001", role="teacher")
        _, accountant = _employee(session, school, "EMP-0002", role="accountant")

        rows = {item.id: item for item in perf.performance(session)}
        assert rows[accountant.id].kind == "staff"
        keys = {item.key for item in rows[accountant.id].components}
        assert "syllabus" not in keys
