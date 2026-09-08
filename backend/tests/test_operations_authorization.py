from app.domains.operations.router import (
    read_book_issues,
    read_palette_commands,
    read_report_cards,
    read_transport_routes,
)
from app.domains.users.models import RoleEnum, User


def create_mock_user(role: RoleEnum):
    return User(
        id=99,
        email=f"{role.value}@test.com",
        role=role,
        full_name="Mock User",
        is_active=True,
        hashed_password="pw",
    )


def test_library_rbac():
    student = create_mock_user(RoleEnum.student)
    parent = create_mock_user(RoleEnum.guardian)
    admin = create_mock_user(RoleEnum.admin)

    # Library books catalog (global, no student_id needed for filtering logic test)
    # The actual endpoints now return filtered mock lists.
    # We will test the mock logic in the router functions.

    # Admin sees all issues
    admin_issues = read_book_issues(student_id=None, session=None, current_user=admin)
    assert len(admin_issues) == 4

    # Student sees 1 issue if student_id is provided
    student_issues = read_book_issues(student_id=1, session=None, current_user=student)
    assert len(student_issues) == 1

    # Parent sees 1 issue if student_id is provided
    parent_issues = read_book_issues(student_id=1, session=None, current_user=parent)
    assert len(parent_issues) == 1

    # Student sees 0 issues if they don't provide student_id
    student_issues_empty = read_book_issues(
        student_id=None, session=None, current_user=student
    )
    assert len(student_issues_empty) == 0


def test_transport_rbac():
    student = create_mock_user(RoleEnum.student)
    teacher = create_mock_user(RoleEnum.teacher)

    student_routes = read_transport_routes(
        student_id=1, session=None, current_user=student
    )
    assert len(student_routes) == 1

    teacher_routes = read_transport_routes(
        student_id=None, session=None, current_user=teacher
    )
    assert len(teacher_routes) == 4


def test_reports_rbac():
    student = create_mock_user(RoleEnum.student)
    admin = create_mock_user(RoleEnum.admin)

    # Student sees filtered report cards
    student_cards = read_report_cards(student_id=1, session=None, current_user=student)
    assert len(student_cards) == 2
    assert "Fee Defaulter Rate" not in [c.title for c in student_cards]

    # Admin sees all cards
    admin_cards = read_report_cards(student_id=None, session=None, current_user=admin)
    assert len(admin_cards) == 4


def test_copilot_rbac():
    student = create_mock_user(RoleEnum.student)
    teacher = create_mock_user(RoleEnum.teacher)
    admin = create_mock_user(RoleEnum.admin)

    # Admin gets all commands
    admin_cmds = read_palette_commands(session=None, current_user=admin)
    assert len(admin_cmds) == 5

    # Teacher gets all EXCEPT Collect fee
    teacher_cmds = read_palette_commands(session=None, current_user=teacher)
    labels = [c.label for c in teacher_cmds]
    assert "Collect fee" not in labels
    assert "Mark attendance" in labels
    assert "Draft fee reminder" in labels  # AI feature they might use

    # Student doesn't get Mark attendance, Collect fee, or Draft fee reminder
    student_cmds = read_palette_commands(session=None, current_user=student)
    labels_student = [c.label for c in student_cmds]
    assert "Collect fee" not in labels_student
    assert "Mark attendance" not in labels_student
    assert "Draft fee reminder" not in labels_student
