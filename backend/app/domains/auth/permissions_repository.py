"""
Repository for DB-driven permissions.
All queries go through here — keeps router/service clean.

Roles are rows now (`role`, keyed by `codename`) and a grant points at `role_id`.
Every function here therefore resolves a role *codename* to its id: callers keep
speaking in codenames (`"teacher"`), the database stores a small integer.
"""

from sqlmodel import Session, select

from app.domains.auth.models import Permission, Role, RolePermission

# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def get_all_permissions(session: Session) -> list[Permission]:
    """Return every permission in the catalog, ordered by category then codename."""
    return list(
        session.exec(
            select(Permission).order_by(Permission.category, Permission.codename)
        ).all()
    )


def get_role_by_codename(session: Session, codename: str) -> Role | None:
    return session.exec(select(Role).where(Role.codename == codename.lower())).first()


def get_permissions_for_role(session: Session, codename: str) -> list[str]:
    """Return the permission codenames granted to one role."""
    stmt = (
        select(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.codename == codename.lower())
    )
    return list(session.exec(stmt).all())


def get_permissions_for_roles(
    session: Session, codenames: set[str] | list[str]
) -> set[str]:
    """Union of the permissions granted to **any** of the given roles.

    This is the multi-role heart of the model: a principal who also teaches gets
    the principal permissions *plus* the teacher ones, in a single query.
    """
    names = [codename.lower() for codename in codenames]
    if not names:
        return set()
    stmt = (
        select(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.codename.in_(names))
    )
    return set(session.exec(stmt).all())


def get_role_permission_map(session: Session) -> dict[str, list[str]]:
    """Return {role codename: [permission codename, ...]} for every granted role."""
    stmt = (
        select(Role.codename, Permission.codename)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .order_by(Role.codename, Permission.codename)
    )
    result: dict[str, list[str]] = {}
    for role, codename in session.exec(stmt).all():
        result.setdefault(role, []).append(codename)
    return result


def get_permission_by_codename(session: Session, codename: str) -> Permission | None:
    return session.exec(
        select(Permission).where(Permission.codename == codename)
    ).first()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def set_role_permissions(
    session: Session, codename: str, permission_ids: list[int]
) -> int:
    """Replace a role's entire permission set with the given permission IDs.

    Returns how many grants the role ended up with, or 0 when the role codename
    is unknown (so the caller can answer 404 instead of pretending it worked).
    """
    role = get_role_by_codename(session, codename)
    if role is None:
        return 0

    existing = session.exec(
        select(RolePermission).where(RolePermission.role_id == role.id)
    ).all()
    for row in existing:
        session.delete(row)
    session.flush()

    for pid in dict.fromkeys(permission_ids):  # de-duplicate, keep order
        session.add(RolePermission(role_id=role.id, permission_id=pid))
    session.commit()
    return len(set(permission_ids))


# ---------------------------------------------------------------------------
# Seed helper — called once on startup from bootstrap/seed
# ---------------------------------------------------------------------------


def seed_permissions(session: Session) -> None:
    """
    Idempotently seeds the Permission and RolePermission tables from the
    static definitions in permissions.py.  Skips rows that already exist.
    """
    from app.domains.auth.permissions import ROLE_PERMISSIONS_MAP, PermissionEnum

    # ── 1. Build a label / category from the codename ───────────────────────
    def _label(codename: str) -> tuple[str, str]:
        """Convert 'students.read' → category='Students', label='Read'."""
        parts = codename.split(".")
        category = parts[0].replace("_", " ").title()
        action = " ".join(parts[1:]).replace("_", " ").title()
        return category, action

    # ── 2. Ensure every Permission row exists ────────────────────────────────
    codename_to_id: dict[str, int] = {}
    for perm in PermissionEnum:
        codename = perm.value
        existing = get_permission_by_codename(session, codename)
        if existing:
            codename_to_id[codename] = existing.id
        else:
            category, label = _label(codename)
            p = Permission(codename=codename, category=category, label=label)
            session.add(p)
            session.flush()  # get the auto-generated id
            codename_to_id[codename] = p.id

    session.commit()

    # ── 2. Ensure every RolePermission row exists ────────────────────────────
    added = 0
    unknown: set[str] = set()
    for codename, granted in ROLE_PERMISSIONS_MAP.items():
        role = get_role_by_codename(session, codename)
        if role is None:
            unknown.add(codename)
            continue
        for permission_codename in granted:
            pid = codename_to_id.get(permission_codename)
            if pid is None:
                continue
            if not session.get(RolePermission, (role.id, pid)):
                session.add(RolePermission(role_id=role.id, permission_id=pid))
                added += 1

    session.commit()
    if unknown:
        print(f"[permissions] skipped unknown roles: {sorted(unknown)}")
    print(f"[permissions] Permission seed complete ({added} new grants)")
