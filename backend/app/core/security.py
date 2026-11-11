import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

#: Alphabet for generated passwords: no 0/O, 1/l/I, so a password read out loud
#: or copied from a printout cannot be mistyped.
PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
PASSWORD_LENGTH = 10


def generate_temp_password(length: int = PASSWORD_LENGTH) -> str:
    """A random password for a login created by the server (first-time password).

    Shown to the office exactly once, right after an admission is registered;
    only its hash is ever stored.
    """
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _json_safe_claims(claims: dict) -> dict:
    """A claim set a JWT can actually carry.

    A JWT payload is JSON, so a claim value has to be a string, a number, a
    boolean, null, or a list/dict of those. The impersonation claims are the
    reason this exists: `act` and `imp` are UUIDs, and handing one straight to
    `jwt.encode` raised

        TypeError: Object of type UUID is not JSON serializable

    which made `POST /auth/impersonate` answer 500 and the UI report "Could not
    switch account". Ids travel as text, which is also how `sub` has always been
    written, so decoding gives back the same strings everywhere.
    """
    safe: dict = {}
    for key, value in claims.items():
        if value is None or isinstance(value, str | int | float | bool):
            safe[key] = value
        elif isinstance(value, list | tuple):
            safe[key] = [item if isinstance(item, str) else str(item) for item in value]
        else:
            safe[key] = str(value)
    return safe


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

    Claim values are made JSON-safe here rather than at each call site, so a
    caller may pass the UUID it already has (`act=actor.id`) and still get a
    token back instead of a `TypeError`.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode: dict = {"exp": expire, "sub": str(subject)}
    if extra_claims:
        to_encode.update(_json_safe_claims(extra_claims))
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _uuid_claim(token: str | None, key: str) -> UUID | None:
    """One id-valued claim, or None when it is absent, unreadable or not a UUID.

    Both `act` and `sch` are ids that a caller has to treat as "not there" far more
    often than as "wrong": a plain login has no `act`, a platform session that is
    not scoped to a school has no `sch`. Answering None for every unusable case
    keeps the two call sites below to one branch each.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    value = payload.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def actor_id_from_token(token: str | None) -> UUID | None:
    """The `act` claim of a token: the admin it was switched from, if any.

    Returns None for a normal token (and for anything unreadable), so callers can
    treat "no actor" and "bad token" the same way - the token has already been
    validated by the auth dependency by the time this runs.
    """
    return _uuid_claim(token, "act")


def school_scope_from_token(token: str | None) -> UUID | None:
    """The `sch` claim: the school a **platform** account asked to work inside.

    This is the "switch school" half of the console, not impersonation. The token
    still says `sub = <the administrator>`, so roles and permissions are the
    administrator's own; only the tenant binding changes
    (`app/domains/auth/dependencies.py::_bind_school`). Returning None means "no
    scope", i.e. the platform-wide view, which is what a normal login gets.

    The claim cannot widen anything: a school-level account never reads it - its
    own `school_id` wins - and an unknown or suspended school is refused at the
    door rather than bound.
    """
    return _uuid_claim(token, "sch")
