from sqlmodel import Session

from app.core.security import create_access_token, verify_password

from . import repository


def authenticate_user(session: Session, username: str, password: str) -> str | None:
    user = repository.get_user_by_email(session, email=username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return create_access_token(subject=user.id)
