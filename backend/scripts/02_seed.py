"""02 - platform admin, schools and their one admin each. Idempotent.

Passwords come from the env only (`SEED_PLATFORM_ADMIN_PASSWORD`,
`SEED_SCHOOL_ADMIN_PASSWORD`) and are used once, when the account is created.
"""

import os
import sys

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.auth.permissions_repository import seed_roles
from app.domains.auth.roles import set_user_roles
from app.domains.schools.models import School
from app.domains.users.models import User

#: Schools this seed registers. `code` is the slug/key, `login` is the admin's
#: address, `admin_name` is the person (not the school). Text stored lower-case.
SCHOOLS: tuple[dict[str, str], ...] = (
    {
        "name": "abc school",
        "code": "abc",
        "contact": "office@abc",
        "phone": "+91 90000 00001",
        "address": "sector 1, demo city",
        "login": "admin@abc",
        "admin_name": "abhay",
    },
    {
        "name": "delhi public school",
        "code": "dps",
        "contact": "office@dps",
        "phone": "+91 90000 00002",
        "address": "sector 9, demo city",
        "login": "office@dps",
        "admin_name": "vijay prathap sing",
    },
)

#: The role every school's first account holds.
ADMIN_ROLE = "school_admin"

#: Platform accounts hold no school, so their permissions apply everywhere.
#: Login + password are deployment secrets and come from the env.
PLATFORM_ADMINS: tuple[dict[str, str], ...] = (
    {
        "name": "system admin",
        "role": "system_admin",
    },
)


def _required(value: str, variable: str) -> str:
    """A password from the env, or a message saying which variable to set.

    Asked only when an account is created: an existing account keeps its password.
    """
    if not value:
        raise RuntimeError(
            f"{variable} is empty, so this login cannot be created. Set it in "
            "backend/.env (or the platform's env vars) and run the seed again."
        )
    return value


def _seed_school(session: Session, entry: dict[str, str]) -> None:
    """Register one school and reconcile its single admin account."""
    school = session.exec(select(School).where(School.code == entry["code"])).first()
    if school is None:
        school = School(
            name=entry["name"],
            code=entry["code"],
            email=entry["contact"],
            phone=entry.get("phone"),
            address=entry.get("address"),
            is_active=True,
        )
        session.add(school)
        session.commit()
        session.refresh(school)
        print(f"[seed] {school.code}: registered '{school.name}'")
    else:
        print(f"[seed] {school.code}: already registered")

    user = session.exec(select(User).where(User.email == entry["login"])).first()
    if user is None:
        user = User(
            email=entry["login"],
            full_name=entry["admin_name"],
            hashed_password=get_password_hash(
                _required(
                    settings.SEED_SCHOOL_ADMIN_PASSWORD,
                    "SEED_SCHOOL_ADMIN_PASSWORD",
                )
            ),
            is_active=True,
            school_id=school.id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"[seed] {school.code}: created {user.email}")
    else:
        # Re-apply the school link, so an account can never drift outside the
        # tenant it administers (e.g. after a partial restore).
        user.school_id = school.id
        # An older seed run copied the school's name into the admin's own name;
        # the admin is a person, so that is reconciled here (once).
        if user.full_name.strip().casefold() == school.name.strip().casefold():
            user.full_name = entry["admin_name"]
            print(f"[seed] {school.code}: renamed {user.email} to {entry['admin_name']}")
        session.add(user)
        session.commit()
        print(f"[seed] {school.code}: {user.email} already exists")

    # Re-applying the role every start also heals a database whose `user_role`
    # rows were lost: the account keeps working instead of silently holding zero
    # permissions.
    applied = set_user_roles(session, user, [ADMIN_ROLE])
    if not applied:
        print(
            f"[seed] WARNING: role catalog empty - {ADMIN_ROLE} not applied"
        )
    else:
        print(f"[seed] {school.code}: {user.email} roles: {applied}")


def _seed_platform_admin(session: Session, entry: dict[str, str]) -> None:
    """One platform account: no school. Password from the env, used once."""
    login = settings.SEED_PLATFORM_ADMIN_LOGIN
    user = session.exec(select(User).where(User.email == login)).first()
    if user is None:
        user = User(
            email=login,
            full_name=entry["name"],
            hashed_password=get_password_hash(
                _required(
                    settings.SEED_PLATFORM_ADMIN_PASSWORD,
                    "SEED_PLATFORM_ADMIN_PASSWORD",
                )
            ),
            is_active=True,
            school_id=None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"[seed] platform: created {user.email}")
    else:
        # A platform account belongs to no school - clear the link if one was set.
        user.school_id = None
        session.add(user)
        session.commit()
        print(f"[seed] platform: {user.email} already exists")

    applied = set_user_roles(session, user, [entry["role"]])
    if not applied:
        print(
            f"[seed] WARNING: role catalog empty - {entry['role']} not applied"
        )
    else:
        print(f"[seed] platform: {user.email} roles: {applied}")


def main() -> None:
    """Roles first (a user can only hold a role that exists), then the accounts."""
    with Session(engine) as session:
        seed_roles(session)
        for entry in PLATFORM_ADMINS:
            _seed_platform_admin(session, entry)
        for entry in SCHOOLS:
            _seed_school(session, entry)


if __name__ == "__main__":
    main()
