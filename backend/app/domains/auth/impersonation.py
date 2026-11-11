"""Super-admin "switch account" (impersonation) and "switch school" (scope).

Everything here is reachable only by a session that holds `users.impersonate`,
which is granted to the platform-admin role alone. What it provides:

    roles_with_counts()   the role dropdown - each role and how many active
                          people hold it
    candidates()          the people dropdown - filter by role and/or search by
                          e-mail or name; active accounts only, one row per person
    schools_for_switcher() the school dropdown - every active school with its
                          student count
    start()               hand back a token for the target account
    stop()                hand the administrator their own token back
    set_scope()           hand back the administrator's own token, pinned to one
                          school (or back to all schools)

Two different switches, with two different meanings:

* **switch account** - the switched token keeps the *viewed* account in `sub` and
  records the administrator in an `act` claim. Every permission and scope check
  keeps working untouched, because they all resolve from `sub`; the UI can always
  tell, which is what shows the "Viewing as ... - Return" banner instead of
  silently becoming someone else. Each start/stop pair is written to
  `impersonationlog`: a token is not an audit trail - it lives in a browser and
  expires.

* **switch school** - the token still names the administrator in `sub` and only
  carries a `sch` claim (`security.school_scope_from_token`). Permissions stay the
  platform's own, the identity never changes, and the tenant binding alone moves -
  which is exactly "show me this school's numbers" without taking anybody's seat.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.security import create_access_token
from app.core.tenancy import SKIP_SCHOOL, may_cross_school
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User

from .models import ImpersonationLog, Role, UserRole, utcnow
from .roles import roles_of
from .service import build_session_user, load_user_unscoped

#: Accounts that may never be impersonated. Taking over another platform
#: administrator would hide the act behind the very role allowed to perform it,
#: so the guard is here and not only in the UI.
PROTECTED_ROLE_CODENAMES = ("system_admin",)


def roles_of_user(session: Session, user_id: UUID) -> list[str]:
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

    roles_by_user: dict[UUID, list[tuple[str, str]]] = {}
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


def schools_for_switcher(session: Session) -> list[dict]:
    """Every active school, with the number the picker shows next to it.

    Unscoped on purpose (`SKIP_SCHOOL`): the route is gated by `users.impersonate`,
    and picking a school is precisely the moment before a scope exists. The counts
    come from one grouped `count(*)` rather than one query per school, so the list
    stays one round trip however many schools are registered.
    """
    from app.domains.academic.classroom.students.models import Student

    rows = session.exec(
        select(School.id, School.code, School.name)
        .where(School.is_active)
        .order_by(School.name)
    ).all()
    counts = dict(
        session.exec(
            select(Student.school_id, func.count(Student.id)).group_by(
                Student.school_id
            ),
            execution_options={SKIP_SCHOOL: True},
        ).all()
    )
    return [
        {
            "id": school_id,
            "code": code,
            "name": name,
            "students": int(counts.get(school_id, 0)),
        }
        for school_id, code, name in rows
    ]


def set_scope(session: Session, actor: User, school_id: UUID | None) -> dict:
    """Pin this platform session to one school - or clear it with `None`.

    The token keeps `sub = actor.id`, so this is a **view**, not a takeover: the
    administrator keeps their own roles and permissions, and `impersonationlog`
    stays the record of actual account switches. Only the tenant binding moves
    (`sch` claim -> `_bind_school`), which is what makes every list, card and
    `count(*)` on the other side report that one school's numbers.

    `None` mints the same token a fresh login would: no `sch`, platform-wide view.
    """
    if not may_cross_school(roles_of(actor)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a platform account can switch school.",
        )

    if school_id is not None:
        # `school` is global (no tenant column), so this read is never filtered.
        school = session.get(School, school_id)
        if school is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
            )
        if not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That school is suspended.",
            )

    token = create_access_token(
        subject=actor.id,
        extra_claims={"sch": school_id} if school_id is not None else None,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": build_session_user(actor, session, scope_school_id=school_id),
    }


def start(
    session: Session, actor: User, target_id: UUID, reason: str | None = None
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

    # Unscoped on purpose: a session that is already scoped to one school must
    # still be able to switch into somebody from another (`load_user_unscoped`).
    target = load_user_unscoped(session, target_id)
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
    # Mint the token *before* the audit row is written: the token used to fail
    # (a UUID claim is not JSON), and doing it in this order means a failure can
    # no longer leave an open "still viewing" row behind. `log.id` is already set -
    # `UUIDMixin` mints it on construction.
    token = create_access_token(
        subject=target.id, extra_claims={"act": actor.id, "imp": log.id}
    )

    session.add(log)
    session.commit()
    session.refresh(log)

    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": build_session_user(target, session, actor_id=actor.id),
        "log_id": log.id,
    }


def stop(session: Session, actor_id: UUID) -> dict:
    """Close the open audit row(s) and hand the administrator their own token."""
    # Unscoped: this session is bound to the school of the account being viewed,
    # and the administrator is a platform account - `session.get` would miss it.
    actor = load_user_unscoped(session, actor_id)
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
