import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.domains.users import repository as user_repository
from app.domains.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Define the exception globally so it can be raised in both branches
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError, ValidationError:
        raise credentials_exception

    user = user_repository.get_user_by_id(session, user_id=int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_user_ws(
    token: str, session: Session = Depends(get_session)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except jwt.PyJWTError, ValidationError:
        return None

    user = user_repository.get_user_by_id(session, user_id=int(user_id))
    if not user or not user.is_active:
        return None
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return user
