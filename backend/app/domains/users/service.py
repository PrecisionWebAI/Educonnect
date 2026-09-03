from fastapi import HTTPException, status
from sqlmodel import Session

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
    db_user = repository.get_user_by_email(session, email=user_create.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return repository.create_user(session, user_create=user_create)
