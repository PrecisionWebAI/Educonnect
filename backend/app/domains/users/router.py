from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker, get_current_active_user

from . import service
from .models import RoleEnum, User, UserCreate, UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get the currently authenticated user's profile.
    """
    return current_user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(RoleChecker([RoleEnum.admin])),
):
    """
    Create a new user (Admin only).
    """
    return service.create_user(session=session, user_create=user_in)


@router.get("", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(RoleChecker([RoleEnum.admin])),
):
    """
    List all users (Admin only).
    """
    return service.get_users(session=session, skip=skip, limit=limit)
