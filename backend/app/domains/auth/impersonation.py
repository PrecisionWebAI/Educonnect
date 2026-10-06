"""Super-admin "switch account" (impersonation).

Everything here is reachable only by a session that holds `users.impersonate`,
which is granted to the platform-admin role alone. What it provides:

    roles_with_counts()   the role dropdown - each role and how many active
                          people hold it
    candidates()          the people dropdown - filter by role and/or search by
                          e-mail or name; active accounts only, one row per person
    start()               hand back a token for the target account
    stop()                hand the administrator their own token back

The switched token keeps the *viewed* account in `sub` and records the
administrator in an `act` claim. Two consequences, both deliberate:

* every permission and scope check keeps working untouched, because they all
  resolve from `sub` - nothing in the app has to know a session is impersonated;
* the UI can always tell, which is what shows the "Viewing as ... - Return"
  banner instead of silently becoming someone else.

Each start/stop pair is also written to `impersonationlog`: a token is not an
audit trail - it lives in a browser and expires.
"""

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.security import create_access_token
from app.domains.users.models import User

from .models import ImpersonationLog, Role, UserRole, utcnow
from .service import build_session_user

#: Accounts that may never be impersonated. Taking over another platform
#: administrator would hide the act behind the very role allowed to perform it,
#: so the guard is here and not only in the UI.
PROTECTED_ROLE_CODENAMES = ("system_admin", "owner")


def roles_of_user(session: Session, user_id: int) -> list[str]:
    """A person's role codenames, primary first (then alphabetical)."""
    return list(
        session.exec(
            select(Role.codename)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(UserRole.is_primary.desc(), Role.codename)
        ).all()
    )


def roles_with_counts(session: Session) -> list[dict]:
    """Every role with the number of **active** people holding it.

    One grouped query, so the dropdown arrives ready to render with its counts.
    """
    rows = session.exec(
        select(Role.codename, Role.label, func.count(UserRole.user_id))
        .join(UserRole, UserRole.role_id == Role.id)
        .join(User, User.id == UserRole.user_id)
        .where(User.is_active)
        .group_by(Role.codename, Role.label, Role.id)
        .order_by(Role.id)
    ).all()
    return [
        {"codename": codename, "label": label, "users": int(count)}
        for codename, label, count in rows
    ]


def candidates(
    session: Session,
    role: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """People the administrator may switch to, narrowed by role and/or text.

    `search` matches the **e-mail or the name** (case-insensitive substring), so
    "priya" and "priya@educonnect.com" both work. Protected accounts are filtered
    here as well as in the UI, and every candidate's roles come from one follow-up
    query instead of one query per row.
    """
    query = select(User).where(User.is_active)
    if role:
        query = (
            query.join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.codename == role.strip().lower())
        )
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(User.email).like(term) | func.lower(User.full_name).like(term)
        )
    query = query.order_by(User.full_name).limit(max(1, min(limit, 200)))
    users = list(session.exec(query).all())
    if not users:
        return []

    roles_by_user: dict[int, list[tuple[str, str]]] = {}
    for user_id, codename, label in session.exec(
        select(UserRole.user_id, Role.codename, Role.label)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id.in_([user.id for user in users]))
        .order_by(UserRole.user_id, UserRole.is_primary.desc(), Role.codename)
    ).all():
        roles_by_user.setdefault(user_id, []).append((codename, label))

    out: list[dict] = []
    for user in users:
        held = roles_by_user.get(user.id, [])
        codenames = [codename for codename, _ in held]
        if set(codenames) & set(PROTECTED_ROLE_CODENAMES):
            continue
        primary_codename, primary_label = held[0] if held else ("staff", "Staff")
        out.append(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": [codename.upper() for codename in codenames],
                "role": primary_codename.upper(),
                "role_label": primary_label,
            }
        )
    return out


def start(
    session: Session, actor: User, target_id: int, reason: str | None = None
) -> dict:
    """Switch the session to `target_id` and return the token payload.

    The response has the same keys as a normal login, so the frontend stores it
    through the code path it already has. `act` in the token names the actor; the
    audit row records the pair.
    """
    if target_id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already signed in as this account.",
        )

    target = session.get(User, target_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That account is deactivated.",
        )
    if set(roles_of_user(session, target.id)) & set(PROTECTED_ROLE_CODENAMES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Another platform administrator cannot be impersonated.",
        )

    log = ImpersonationLog(
        actor_user_id=actor.id, target_user_id=target.id, reason=reason
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    token = create_access_token(
        subject=target.id, extra_claims={"act": actor.id, "imp": log.id}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": build_session_user(target, session, actor_id=actor.id),
        "log_id": log.id,
    }


def stop(session: Session, actor_id: int) -> dict:
    """Close the open audit row(s) and hand the administrator their own token."""
    actor = session.get(User, actor_id)
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    open_rows = session.exec(
        select(ImpersonationLog)
        .where(ImpersonationLog.actor_user_id == actor_id)
        .where(ImpersonationLog.ended_at.is_(None))
    ).all()
    for row in open_rows:
        row.ended_at = utcnow()
        session.add(row)
    session.commit()

    token = create_access_token(subject=actor.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": build_session_user(actor, session),
        "closed_logs": len(open_rows),
    }
