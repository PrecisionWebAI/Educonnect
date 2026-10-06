from fastapi import HTTPException, status
from sqlmodel import Session

from app.domains.auth.roles import set_user_roles

from . import repository
from .models import User, UserCreate


def get_user(session: Session, user_id: int) -> User:
    user = repository.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_users(session: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return repository.get_users(session, skip=skip, limit=limit)


def create_user(session: Session, user_create: UserCreate) -> User:
    existing = repository.get_user_by_email(session, email=user_create.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = repository.create_user(session, user_create=user_create)
    # A login with no role can do nothing, so the roles are granted here, in the
    # same request. The first codename becomes the primary role.
    granted = set_user_roles(session, user, [role.value for role in user_create.roles])
    if not granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid roles supplied",
        )
    return user
