"""
Repository for DB-driven permissions.
All queries go through here — keeps router/service clean.
"""

from sqlmodel import Session, select

from app.domains.auth.models import Permission, RolePermission

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


def get_permissions_for_role(session: Session, role: str) -> list[str]:
    """Return the list of permission codenames granted to *role*."""
    stmt = (
        select(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role == role.lower())
    )
    return list(session.exec(stmt).all())


def get_role_permission_map(session: Session) -> dict[str, list[str]]:
    """Return {role: [codename, ...]} for every role that has at least one permission."""
    stmt = (
        select(RolePermission.role, Permission.codename)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .order_by(RolePermission.role, Permission.codename)
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
    session: Session, role: str, permission_ids: list[int]
) -> None:
    """Replace a role's entire permission set with the given permission IDs."""
    role = role.lower()
    # Delete existing assignments for this role
    existing = session.exec(
        select(RolePermission).where(RolePermission.role == role)
    ).all()
    for rp in existing:
        session.delete(rp)
    session.flush()

    # Insert new assignments
    for pid in permission_ids:
        session.add(RolePermission(role=role, permission_id=pid))
    session.commit()


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

    # ── 3. Ensure every RolePermission row exists ────────────────────────────
    for role, codenames in ROLE_PERMISSIONS_MAP.items():
        for codename in codenames:
            pid = codename_to_id.get(codename)
            if pid is None:
                continue
            already = session.exec(
                select(RolePermission)
                .where(RolePermission.role == role)
                .where(RolePermission.permission_id == pid)
            ).first()
            if not already:
                session.add(RolePermission(role=role, permission_id=pid))

    session.commit()
    print("[permissions] Permission seed complete")
