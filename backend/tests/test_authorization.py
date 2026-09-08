from app.domains.auth.service import AuthorizationService
from app.domains.users.models import RoleEnum, User


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
