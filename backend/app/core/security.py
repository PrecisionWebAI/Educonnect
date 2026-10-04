from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict | None = None,
) -> str:
    """Mint an access token for `subject` (a user id).

    `extra_claims` is how impersonation travels: the switched token keeps the
    account being viewed in `sub` and records the admin who started it in `act`.
    Every permission and scope check resolves from `sub`, so nothing else in the
    application has to know a session is impersonated.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode: dict = {"exp": expire, "sub": str(subject)}
    if extra_claims:
        to_encode.update(extra_claims)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def actor_id_from_token(token: str) -> int | None:
    """The `act` claim of a token: the admin it was switched from, if any.

    Returns None for a normal token (and for anything unreadable), so callers can
    treat "no actor" and "bad token" the same way - the token has already been
    validated by the auth dependency by the time this runs.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    actor = payload.get("act")
    try:
        return int(actor) if actor is not None else None
    except (TypeError, ValueError):
        return None
