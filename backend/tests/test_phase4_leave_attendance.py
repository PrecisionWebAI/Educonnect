"""Phase 4: own attendance, the leave tabs (0.10), and the decision trail.

Every test here fails for a rule the phase added:

* **you mark your own day** - `staff_attendance.self` takes the person from the
  token, so there is no employee id in the body to abuse;
* **one mark per day** - a second `POST /me/attendance` is `409`, and the office's
  audited correction is the only way to change a marked day;
* **the mark leaves a trail** - one `staffauditlog` line, written in the same
  transaction as the row;
* **a decision is one transaction** - approving writes the status, the decider and
  the audit line together, and cancelling an approved leave gives the days back
  because the balance is derived, not stored;
* **two leave tabs, one table** - `kind` filters staff vs student rows *inside* the
  caller's scope, and `visible_kinds` says which tabs to draw.

Runs on in-memory SQLite, built from the same models the migrations mirror.
"""

import importlib
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as people_labels
from app.domains.people.teachers.staff_attendance import service as attendance_service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.staff_attendance.schemas import AttendanceSelfIn
from app.domains.services.leave import service as leave_service
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


def _session(created) -> Session:
    return Session(created, expire_on_commit=False)


def _school(session: Session) -> School:
    for codename in ("teacher", "school_admin", "principal", "student", "guardian"):
        if not session.exec(select(Role).where(Role.codename == codename)).first():
            session.add(Role(codename=codename, label=codename.title()))
    school = School(
        name="School P4",
        code="P4",
        email="office@p4.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


def _employee(session: Session, school: School, *, code: str, role: str) -> User:
    user = User(
        email=f"{code.lower()}@p4.test",
        full_name=f"Person {code}",
        hashed_password="x",
        school_id=school.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    grant_role(session, user, role)
    session.add(
        Employee(
            user_id=user.id,
            employee_code=code,
            department="Science",
            joining_date=date(2023, 6, 1),
            school_id=school.id,
        )
    )
    session.commit()
    return user


# --- own attendance (staff_attendance.self) ---------------------------------


def test_a_person_marks_their_own_day_once():
    import pytest

    created = engine()
    with _session(created) as session:
        school = _school(session)
        user = _employee(session, school, code="EMP-0001", role="teacher")

        day = attendance_service.mark_self(
            session,
            AttendanceSelfIn(date=date(2026, 11, 10), status="present"),
            user,
        )
        assert day.status == "present"
        row = session.exec(select(StaffAttendanceRecord)).one()
        assert row.employee_id == session.exec(select(Employee)).one().id

        # The same day again is refused - the office corrects a marked day.
        with pytest.raises(Exception) as problem:
            attendance_service.mark_self(
                session,
                AttendanceSelfIn(date=date(2026, 11, 10), status="absent"),
                user,
            )
        assert getattr(problem.value, "status_code", None) == 409


def test_the_self_mark_is_in_the_audit_trail():
    from app.domains.people.teachers.models import StaffAuditLog

    created = engine()
    with _session(created) as session:
        school = _school(session)
        user = _employee(session, school, code="EMP-0001", role="teacher")
        attendance_service.mark_self(
            session,
            AttendanceSelfIn(date=date(2026, 11, 10), status="present"),
            user,
        )
        line = session.exec(
            select(StaffAuditLog).where(StaffAuditLog.section == "attendance")
        ).one()
        assert line.action == "created"
        assert "marked by the person" in line.summary


def test_a_login_without_a_staff_record_cannot_mark():
    import pytest

    created = engine()
    with _session(created) as session:
        school = _school(session)
        user = User(
            email="nobody@p4.test",
            full_name="No Staff Record",
            hashed_password="x",
            school_id=school.id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        with pytest.raises(Exception) as problem:
            attendance_service.mark_self(
                session,
                AttendanceSelfIn(date=date(2026, 11, 10), status="present"),
                user,
            )
        assert getattr(problem.value, "status_code", None) == 409
        assert session.exec(select(StaffAttendanceRecord)).all() == []


# --- the two leave tabs (0.10) ----------------------------------------------


def _staff_leave(session: Session, school: School, user: User, employee: Employee):
    row = LeaveRequest(
        employee_id=employee.id,
        requester_user_id=user.id,
        leave_type="Casual",
        from_date=date(2026, 11, 10),
        to_date=date(2026, 11, 11),
        days=2,
        status="Pending",
        school_id=school.id,
    )
    session.add(row)
    session.commit()
    return row


def _student_leave(session: Session, school: School, guardian: User):
    student = Student(full_name="Child One", school_id=school.id)
    session.add(student)
    session.commit()
    session.refresh(student)
    row = LeaveRequest(
        student_id=student.id,
        requester_user_id=guardian.id,
        leave_type="Medical",
        from_date=date(2026, 11, 12),
        to_date=date(2026, 11, 12),
        days=1,
        status="Approved",
        school_id=school.id,
    )
    session.add(row)
    session.commit()
    return row


def test_kind_is_a_filter_not_a_permission():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        teacher_user = _employee(session, school, code="EMP-0001", role="teacher")
        teacher = session.exec(
            select(Employee).where(Employee.user_id == teacher_user.id)
        ).one()
        guardian = User(
            email="guardian@p4.test",
            full_name="Guardian",
            hashed_password="x",
            school_id=school.id,
        )
        session.add(guardian)
        session.commit()
        session.refresh(guardian)
        grant_role(session, guardian, "guardian")

        _staff_leave(session, school, teacher_user, teacher)
        _student_leave(session, school, guardian)

        staff_rows = leave_service.tab_requests(
            session, kind="staff", user=teacher_user
        )
        student_rows = leave_service.tab_requests(
            session, kind="student", user=teacher_user
        )
        assert [row.kind for row in staff_rows] == ["staff"]
        # The teacher may not read a child's leave just by asking for that tab.
        assert student_rows == []

        guardian_rows = leave_service.tab_requests(
            session, kind="student", user=guardian
        )
        assert [row.kind for row in guardian_rows] == ["student"]
        assert guardian_rows[0].person == "Child One"


def test_visible_kinds_tells_the_screen_which_tabs_to_draw():
    created = engine()
    with _session(created) as session:
        school = _school(session)
        teacher = _employee(session, school, code="EMP-0001", role="teacher")
        office = _employee(session, school, code="EMP-0002", role="school_admin")

        assert leave_service.visible_kinds(session, teacher) == ["staff"]
        assert leave_service.visible_kinds(session, office) == ["staff", "student"]


# --- the decision is one transaction ----------------------------------------


def test_approving_cancelling_and_the_balance_agree():
    from app.domains.people.teachers.models import StaffAuditLog
    from app.domains.services.leave import workflow

    created = engine()
    with _session(created) as session:
        school = _school(session)
        owner = _employee(session, school, code="EMP-0001", role="teacher")
        office = _employee(session, school, code="EMP-0002", role="school_admin")
        employee = session.exec(
            select(Employee).where(Employee.user_id == owner.id)
        ).one()
        request = _staff_leave(session, school, owner, employee)

        approved = workflow.decide(
            session, request.id, action="approve", note="ok", user=office
        )
        assert approved.status == people_labels.APPROVED
        session.refresh(request)
        assert request.decided_by_user_id == office.id

        # One audit line per decision, written with the row it describes.
        actions = [
            line.action
            for line in session.exec(
                select(StaffAuditLog).where(StaffAuditLog.section == "leave")
            ).all()
        ]
        assert actions == ["updated"]

        # Cancelling an approved leave gives the days back: the balance is derived.
        used_before = leave_service.days_for(
            session, employee=employee, leave_type="Casual", year=2026
        )
        assert used_before[0] == 2

        workflow.decide(session, request.id, action="cancel", note=None, user=owner)
        used_after = leave_service.days_for(
            session, employee=employee, leave_type="Casual", year=2026
        )
        assert used_after[0] == 0
