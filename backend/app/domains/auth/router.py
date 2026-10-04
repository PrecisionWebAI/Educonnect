from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import (
    RequirePermission,
    get_actor_id,
    get_current_active_user,
)
from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import impersonation, schemas, service

router = APIRouter()


# ── Auth endpoints ──────────────────────────────────────────────────────────


@router.post("/login", response_model=schemas.TokenResponse)
@router.post("/token", response_model=schemas.TokenResponse)
async def login(
    request: Request,
    session: Session = Depends(get_session),
):
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username") or body.get("identifier") or ""
        password = body.get("password") or ""
    else:
        form = await request.form()
        username = form.get("username") or ""
        password = form.get("password") or ""

    # Try authenticate by email
    user = user_repository.get_user_by_email(session, email=username)
    # If not found by e-mail, try the local part ("principal" for
    # "principal@educonnect.com"). Role names are no longer a login shortcut:
    # several people share a role, so there is nothing unambiguous to match.
    if not user and "@" not in username:
        from sqlmodel import select

        wanted = username.lower()
        for candidate in session.exec(select(User)).all():
            if candidate.email.split("@")[0].lower() == wanted:
                user = candidate
                username = candidate.email
                break

    token = service.authenticate_user(
        session=session, username=username, password=password
    )

    if not token or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": service.build_session_user(user, session),
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
    actor_id: int | None = Depends(get_actor_id),
):
    """The signed-in identity. `impersonatedBy` is set when the session is a switch."""
    return service.build_session_user(current_user, session, actor_id=actor_id)


@router.post("/logout")
def logout():
    return {"status": "ok", "detail": "Logged out successfully"}


# ── Switch account (impersonation) — platform admin only ────────────────────


@router.get("/impersonate/roles", response_model=schemas.ImpersonationRoles)
def impersonation_roles(
    session: Session = Depends(get_session),
    _: User = Depends(RequirePermission("users.impersonate")),
):
    """The role dropdown: every role with the number of active people holding it."""
    return {"roles": impersonation.roles_with_counts(session)}


@router.get("/impersonate/users", response_model=schemas.ImpersonationTargets)
def impersonation_users(
    role: str | None = None,
    search: str | None = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    _: User = Depends(RequirePermission("users.impersonate")),
):
    """The people dropdown: active accounts, narrowed by role and/or e-mail/name.

    `search` is why the e-mail box works without picking a role first.
    """
    return {
        "users": impersonation.candidates(
            session, role=role, search=search, limit=limit
        )
    }


@router.post("/impersonate", response_model=schemas.TokenResponse)
def start_impersonation(
    body: schemas.ImpersonationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.impersonate")),
):
    """Switch this session to another account; the payload is login-shaped."""
    return impersonation.start(
        session, actor=current_user, target_id=body.user_id, reason=body.reason
    )


@router.post("/impersonate/stop", response_model=schemas.TokenResponse)
def stop_impersonation(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    actor_id: int | None = Depends(get_actor_id),
):
    """Return to the administrator's own account - no second sign-in needed."""
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not impersonating anybody.",
        )
    return impersonation.stop(session, actor_id=actor_id)


# ── Permissions management endpoints ────────────────────────────────────────


@router.get("/permissions")
def list_permissions(
    _: User = Depends(RequirePermission("permissions.manage")),
    session: Session = Depends(get_session),
):
    """
    Returns the full permission catalog grouped by category.
    Used by the RBAC admin UI to render the permission checkbox matrix.
    """
    from app.domains.auth.permissions_repository import get_all_permissions

    perms = get_all_permissions(session)
    # Group by category
    grouped: dict[str, list[dict]] = {}
    for p in perms:
        grouped.setdefault(p.category, []).append(
            {
                "id": p.id,
                "codename": p.codename,
                "label": p.label,
            }
        )
    return {"permissions": grouped}


@router.get("/permissions/roles")
def get_role_permissions(
    _: User = Depends(RequirePermission("permissions.manage")),
    session: Session = Depends(get_session),
):
    """
    Returns the full role → [permission codenames] map.
    Used by the RBAC admin UI to pre-populate which permissions each role has.
    """
    from app.domains.auth.permissions_repository import get_role_permission_map

    return {"role_permissions": get_role_permission_map(session)}


@router.put("/permissions/roles/{role}")
def update_role_permissions(
    role: str,
    body: dict,
    _: User = Depends(RequirePermission("permissions.manage")),
    session: Session = Depends(get_session),
):
    """
    Replace all permissions for *role* with the given list of permission IDs.
    Body: { "permission_ids": [1, 2, 3, ...] }
    """
    from app.domains.auth.permissions_repository import (
        get_role_by_codename,
        set_role_permissions,
    )

    if get_role_by_codename(session, role) is None:
        raise HTTPException(status_code=404, detail=f"Unknown role: {role}")

    permission_ids: list[int] = body.get("permission_ids", [])
    updated = set_role_permissions(session, role, permission_ids)
    return {"status": "ok", "role": role.lower(), "updated_count": updated}
