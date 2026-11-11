"""Fees and payroll: who may read what.

The rules today are **permission** rules (`auth/permissions.py`, applied by the
route guards), plus one family rule the dues route applies itself
(`may_read_student_dues` in `finance/router.py`):

    * `/finance/students/{id}/dues` needs `fees.read` - the office holds it, and so
      do a student and a guardian, who may then read **their own child** only;
    * `/finance/payroll` needs `payroll.read`, which a teacher does not hold (they
      hold `payroll.view_payslip`: their own payslip).

The scenarios call those two rules directly - no HTTP client - so this module runs
in the API image (which carries no dev dependencies) as well as under pytest.

The older version of this file asserted a per-student/parent/teacher ownership check
on the routes themselves. Those checks were replaced by the permission guards, so
what is worth asserting now is the permission each role holds and the family scope
the dues route keeps.
"""

from sqlmodel import Session
from tests.test_contacts import (  # noqa: F401  (memory_session is the runner's)
    _school,
    _student,
    _user,
    memory_session,
)

from app.domains.auth.models import Role
from app.domains.auth.roles import attach_roles
from app.domains.auth.service import AuthorizationService
from app.domains.finance.router import may_read_student_dues
from app.domains.students.models import Guardian, StudentGuardianRelationship
from app.domains.users.models import User


def _login(session: Session, email: str, name: str, role: str) -> User:
    """A person with their role row and the roles a request attaches."""
    user = _user(session, email, name, [role])
    attach_roles(session, user)
    return user


def check_a_student_reads_only_their_own_dues(session: Session) -> None:
    _school(session)
    child = _login(session, "child@test.com", "Child", "student")
    other = _login(session, "other@test.com", "Other child", "student")
    mine = _student(session, user_id=child.id, full_name="Child")
    theirs = _student(
        session, user_id=other.id, full_name="Other child", admission_number="CT-2"
    )

    assert AuthorizationService.has_permission(child, "fees.read") is True
    assert may_read_student_dues(session, child, mine.id) is True
    assert may_read_student_dues(session, child, theirs.id) is False


def check_a_guardian_reads_only_their_own_children(session: Session) -> None:
    _school(session)
    parent = _login(session, "parent@test.com", "Parent", "guardian")
    stranger = _login(session, "stranger@test.com", "Stranger", "guardian")
    child = _student(session, full_name="Child", admission_number="CT-3")

    mine = Guardian(
        name="Parent", phone="9000000001", email="parent@test.com", user_id=parent.id
    )
    theirs = Guardian(
        name="Stranger",
        phone="9000000002",
        email="stranger@test.com",
        user_id=stranger.id,
    )
    session.add_all([mine, theirs])
    session.commit()
    session.add(
        StudentGuardianRelationship(
            student_id=child.id, guardian_id=mine.id, is_primary=True
        )
    )
    session.commit()

    assert AuthorizationService.has_permission(parent, "fees.read") is True
    assert may_read_student_dues(session, parent, child.id) is True
    assert may_read_student_dues(session, stranger, child.id) is False


def check_the_office_is_not_scoped_to_a_family(session: Session) -> None:
    """Anybody who is neither a student nor a guardian passes the family rule.

    The gate for them is the route's `fees.read` permission, not a row check - a
    teacher holds no `fees.read`, so the route refuses them at the door.
    """
    _school(session)
    teacher = _login(session, "teacher@test.com", "Teacher", "teacher")
    child = _student(session, full_name="Child", admission_number="CT-4")

    assert may_read_student_dues(session, teacher, child.id) is True
    assert AuthorizationService.has_permission(teacher, "fees.read") is False


def check_the_payroll_register_needs_its_permission(session: Session) -> None:
    """A teacher sees their own payslip, not the school's payroll register."""
    _school(session)
    teacher = _login(session, "teacher@test.com", "Teacher", "teacher")
    # _school seeds the three roles the contact scenarios use; this one also
    # needs a school admin, who is the payroll register holder below.
    session.add(Role(codename="school_admin", label="School Admin"))
    session.commit()
    admin = _login(session, "admin@test.com", "Admin", "school_admin")

    assert AuthorizationService.has_permission(teacher, "payroll.read") is False
    assert AuthorizationService.has_permission(teacher, "payroll.view_payslip") is True
    # A school admin runs the school, payroll included.
    assert AuthorizationService.has_permission(admin, "payroll.read") is True


def check_a_family_may_not_manage_fee_structures(session: Session) -> None:
    _school(session)
    student = _login(session, "child@test.com", "Child", "student")
    guardian = _login(session, "parent@test.com", "Parent", "guardian")

    assert AuthorizationService.has_permission(student, "fees.manage_structure") is False
    assert (
        AuthorizationService.has_permission(guardian, "fees.manage_structure") is False
    )


SCENARIOS = (
    (
        "finance: a student reads only their own dues",
        check_a_student_reads_only_their_own_dues,
    ),
    (
        "finance: a guardian reads only their own children",
        check_a_guardian_reads_only_their_own_children,
    ),
    (
        "finance: the office is not scoped to a family",
        check_the_office_is_not_scoped_to_a_family,
    ),
    (
        "finance: the payroll register needs its permission",
        check_the_payroll_register_needs_its_permission,
    ),
    (
        "finance: a family may not manage fee structures",
        check_a_family_may_not_manage_fee_structures,
    ),
)
