import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.domains.auth.service import AuthorizationService
from app.domains.users.models import RoleEnum, User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_admin_can_manage_class(session: Session):
    user = User(
        id=1,
        email="admin@t.com",
        full_name="Admin",
        role=RoleEnum.admin,
        hashed_password="pw",
    )
    assert AuthorizationService.can_manage_class(user, session, 1) is True


def test_teacher_not_assigned_cannot_manage_class(session: Session):
    user = User(
        id=2,
        email="t@t.com",
        full_name="Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    # No profile, no assignment
    assert AuthorizationService.can_manage_class(user, session, 1) is False


# TODO: Add more integration tests for Class Teacher and Subject Teacher once factories are set up.
