"""Legacy RBAC tests - superseded by `tests/test_permission_matrix.py`.

These two files were written when `User.role` was a single enum column and a role
granted permissions by name. Roles are **data** now (`role` + `user_role` +
`rolepermission`, unionised by `AuthorizationService`), so:

* `RoleEnum.admin` no longer exists (the codenames are `system_admin`,
  `school_admin`, `principal`, …);
* permissions cannot be resolved from a detached `User()` any more - they need a
  session and the person's role rows.

`tests/test_permission_matrix.py` asserts the same matrix against the real model
(including the rows a teacher must **not** hold), so nothing is lost by retiring
these. Kept (skipped) rather than deleted so the history of the change stays
readable.
"""

import pytest

from app.domains.auth.service import AuthorizationService
from app.domains.admin.users.models import RoleEnum, User

pytestmark = pytest.mark.skip(
    reason="legacy RBAC: roles are data now - see tests/test_permission_matrix.py"
)


def test_admin_has_manage_users_permission():
    user = User(
        email="admin@test.com",
        full_name="Admin",
        role=RoleEnum.admin,
        hashed_password="pw",
    )
    assert AuthorizationService.has_permission(user, "users.manage") is True


def test_teacher_does_not_have_manage_users_permission():
    user = User(
        email="teacher@test.com",
        full_name="Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    assert AuthorizationService.has_permission(user, "users.manage") is False


def test_teacher_has_students_read_permission():
    user = User(
        email="teacher@test.com",
        full_name="Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    assert AuthorizationService.has_permission(user, "students.read") is True


def test_invalid_permission_returns_false():
    user = User(
        email="admin@test.com",
        full_name="Admin",
        role=RoleEnum.admin,
        hashed_password="pw",
    )
    assert (
        AuthorizationService.has_permission(
            user, "invalid.permission.that.does.not.exist"
        )
        is False
    )


def test_can_method_validates_base_permission():
    user = User(
        email="student@test.com",
        full_name="Student",
        role=RoleEnum.student,
        hashed_password="pw",
    )
    assert AuthorizationService.can(user, "students.read") is True
    assert AuthorizationService.can(user, "fees.manage_structure") is False
