"""Role helpers - the multi-role counterpart of the old `user.role`.

A person holds a *set* of roles (`user_role` rows), so every place that used to
ask "what is this user's role?" now asks one of these instead:

    role_codenames(session, user_id)   -> ["principal", "teacher"]
    attach_roles(session, user)        -> loads them once per request
    roles_of(user)                     -> the loaded set, no query
    set_user_roles(session, user, [...])  -> replaces the assignments

`attach_roles` runs once per request inside `get_current_user`, so permission
checks, scope validation and response builders all read the roles through
`roles_of(user)` without touching the database again.

The roles are stored on a private (`_`-prefixed) attribute because Pydantic v2
refuses to set an undeclared *field* on a model instance, while leading-underscore
names are explicitly allowed - the same trick `AuthorizationService` already used
for `_resolved_permissions`.
"""

from sqlmodel import Session, select

from app.domains.users.models import User

from .models import Role, UserRole


def role_codenames(session: Session, user_id: int) -> list[str]:
    """The role codenames a user holds: primary first, then alphabetical."""
    rows = session.exec(
        select(Role.codename)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(UserRole.is_primary.desc(), Role.codename)
    ).all()
    return list(rows)


def attach_roles(session: Session, user: User) -> set[str]:
    """Load a user's roles once and hang them on the object for this request."""
    codenames = set(role_codenames(session, user.id))
    user._role_names = codenames
    return codenames


def roles_of(user: User) -> set[str]:
    """The roles loaded by `attach_roles` (empty set when it was never called)."""
    return getattr(user, "_role_names", set())


def has_role(user: User, *codenames: str) -> bool:
    """True when the user holds at least one of `codenames`."""
    return bool(roles_of(user) & set(codenames))


def primary_role_name(session: Session, user_id: int) -> str | None:
    """The role whose dashboard opens at login: the `is_primary` one."""
    return next(iter(role_codenames(session, user_id)), None)


def primary_role_names(session: Session, user_ids: list[int]) -> dict[int, str]:
    """{user_id: primary role codename} for many users, in **one** query.

    Contact lists and message feeds need a role for every person on screen; doing
    that per user would be an N+1. This fetches all (user, role, is_primary) rows
    for the given users and keeps the primary - or the alphabetically first, when
    a person has no primary marked.
    """
    unique_ids = list(dict.fromkeys(user_ids))
    if not unique_ids:
        return {}

    rows = session.exec(
        select(UserRole.user_id, Role.codename, UserRole.is_primary)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id.in_(unique_ids))
    ).all()

    best: dict[int, tuple[bool, str]] = {}
    for user_id, codename, is_primary in rows:
        current = best.get(user_id)
        if (
            current is None
            or (is_primary and not current[0])
            or (is_primary == current[0] and codename < current[1])
        ):
            best[user_id] = (is_primary, codename)
    return {user_id: codename for user_id, (_, codename) in best.items()}


def set_user_roles(session: Session, user: User, codenames: list[str]) -> list[str]:
    """Replace a user's role assignments.

    The first codename in the list becomes the primary role - the caller decides
    which hat the person wears by default; unknown codenames are ignored rather
    than silently created. Returns the codenames actually applied.
    """
    wanted = list(dict.fromkeys(codenames))  # de-duplicate, keep order
    roles = session.exec(select(Role).where(Role.codename.in_(wanted))).all()
    if not roles:
        return []

    by_codename = {role.codename: role for role in roles}
    ordered = [by_codename[name] for name in wanted if name in by_codename]
    primary = ordered[0]

    existing = session.exec(select(UserRole).where(UserRole.user_id == user.id)).all()
    for row in existing:
        session.delete(row)
    session.flush()

    for role in ordered:
        session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                is_primary=role.id == primary.id,
            )
        )
    session.commit()
    session.refresh(user)
    return [role.codename for role in ordered]


def grant_role(session: Session, user: User, codename: str) -> bool:
    """Give a user one more role without disturbing the ones they hold."""
    role = session.exec(select(Role).where(Role.codename == codename)).first()
    if not role:
        return False
    if session.get(UserRole, (user.id, role.id)):
        return False
    session.add(UserRole(user_id=user.id, role_id=role.id, is_primary=False))
    session.commit()
    return True
