from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.tenancy import bound_to, may_cross_school
from app.domains.admin.users import repository as user_repository
from app.domains.admin.users.models import User
from app.domains.auth.roles import attach_roles, roles_of

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Define the exception globally so it can be raised in both branches
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _bind_school(session: Session, user: User, token: str | None = None) -> None:
    """Bind the request's session to the school this request may see - and refuse one it may not.

    Two accounts, two rules:

    * a **school-level** account is bound to its own `school_id`. An account with
      none is refused (`403`): binding `None` would switch the tenant filter off
      and hand that session **every** school's rows. The `sch` claim is not even
      read here, so a school account can never be scoped outside its school;
    * a **platform** account (`system_admin`/`owner`) may stay school-less - that
      is the platform-wide view the console and the seeds rely on - or carry a
      `sch` claim that pins it to one school. The claim is validated against the
      `school` table, so a deleted or suspended school is a `403` instead of a
      session that silently sees nothing.

    The platform case is what makes "switch school" work without becoming
    somebody else: `sub` stays the administrator, so permissions are unchanged,
    and only `session.info["school_id"]` moves.
    """
    if not may_cross_school(roles_of(user)):
        if user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "This account is not attached to a school, and it holds no "
                    "platform role that could work across schools."
                ),
            )
        bound_to(session, user.school_id)
        return

    bound_to(session, _scope_school(session, token))


def _scope_school(session: Session, token: str | None) -> UUID | None:
    """The school a platform token asked to work inside, verified - or None for all schools."""
    from app.core.security import school_scope_from_token

    scope = school_scope_from_token(token)
    if scope is None:
        return None

    from app.domains.admin.platform.models import School

    # `school` is a global table (no tenant column), so this read needs no scoping.
    school = session.get(School, scope)
    if school is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That school no longer exists.",
        )
    if not school.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That school is suspended.",
        )
    return scope


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

    user = user_repository.get_user_by_id(session, user_id=UUID(str(user_id)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Load the user's roles once for the whole request: permission checks, scope
    # validation and response building all read this set instead of querying.
    attach_roles(session, user)
    # Bind the request's session to the user's school. From here on every SELECT
    # is filtered and every INSERT is stamped with it (see app/core/db.py), which
    # is what keeps a principal/teacher/guardian inside their own school.
    _bind_school(session, user, token)
    return user


async def get_current_user_ws(
    token: str, session: Session = Depends(get_session)
) -> User:
    """The socket's half of `get_current_user` - with the same tenant binding.

    A WebSocket used to stop at "the token parses", so a chat query on it ran
    **unscoped** and could read another school's messages. It binds the school
    exactly like the HTTP path now; a school-less account is refused there too.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except jwt.PyJWTError, ValidationError:
        return None

    user = user_repository.get_user_by_id(session, user_id=UUID(str(user_id)))
    if not user or not user.is_active:
        return None
    attach_roles(session, user)
    try:
        _bind_school(session, user, token)
    except HTTPException:
        return None
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """A signed-in account that is still allowed in.

    Deactivation has to reach a session that is **already open**: an access token
    lives for a day, so checking only at login would leave a deactivated teacher
    working until it ran out. `401` (not `400`) because that is what the client
    reads as "the session is over" - it clears the session and sends the person
    back to the login page.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_actor_id(token: str = Depends(oauth2_scheme)) -> UUID | None:
    """The `act` claim of this request's token: who the session was switched from.

    None for a normal session, so a route can tell "impersonating" from "signed in"
    without decoding the token itself. A UUID, because `user.id` is one - the
    switch endpoints get theirs from `actor_id_from_token`.
    """
    from app.core.security import actor_id_from_token

    return actor_id_from_token(token)


def get_school_scope(token: str = Depends(oauth2_scheme)) -> UUID | None:
    """The `sch` claim of this request's token: the school a platform session picked.

    None for an ordinary session. `/auth/me` passes it to `build_session_user` so a
    reloaded page still knows which school it is scoped to and the header keeps
    showing that school instead of the platform name.
    """
    from app.core.security import school_scope_from_token

    return school_scope_from_token(token)


class RequirePermission:
    """
    FastAPI dependency to enforce base PBAC permissions on routes,
    and dynamically validate path/query scope parameters.
    """

    def __init__(self, permission: str):
        self.permission = permission

    def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session),
    ) -> User:
        from app.domains.auth.service import AuthorizationService

        # Extract scope parameters from URL
        kwargs = dict(request.path_params)
        kwargs.update(request.query_params)

        if not AuthorizationService.can(
            user, self.permission, session=session, **kwargs
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.permission} or invalid scope.",
            )
        return user
