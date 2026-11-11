"""Register the schools and the one account each of them runs on.

This is the **only** seed script. Everything else is an app-level seeder in
`app/domains/…` (roles, permissions, the class structure) because it is catalog
data the product needs; a school and its login are data a *deployment* brings, so
they live here.

Per entry in `SCHOOLS` it does exactly two things, idempotently:

  1. a `school` row - the school's registration record
  2. one `user` for it - the `school_admin`, linked through `user.school_id`

The admin is a **person**, so their name comes from `admin_name` and not from the
school: the header shows the school's name (from `school.name`) and the account chip
shows the person. An account whose name was copied from the school by an older seed
run is renamed to `admin_name` on the next run.

The login does not have to follow `admin@<code>`; it is spelled out per school
(`abc` uses `admin@abc`, `dps` uses `office@dps`).

Run it directly with:

    python scripts/seed.py
"""

import os

# Need to make sure app is in path
import sys

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.auth.roles import set_user_roles
from app.domains.schools.models import School
from app.domains.users.models import User

#: The schools this seed registers. `code` is the school's slug (and its key for
#: "already registered"); `contact` is the school's own address, `login` is the
#: address its admin signs in with, and `admin_name` is the person behind that
#: login (never the school's own name - the two are different things).
#:
#: Text is written the way the database stores it: lower-case (`app/core/text.py`).
#: The header renders it in Title Case, so "abc school" is shown as "ABC School".
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

#: Platform accounts: **no school**, so their permissions apply across all of them.
#: This is the account a deployment signs in with to switch between schools.
#:
#: The login and the password are *deployment credentials*, so they come from the
#: env (`SEED_PLATFORM_ADMIN_LOGIN`, `SEED_PLATFORM_ADMIN_PASSWORD`) and the code
#: carries neither.
PLATFORM_ADMINS: tuple[dict[str, str], ...] = (
    {
        "name": "system admin",
        "role": "system_admin",
    },
)


def _required(value: str, variable: str) -> str:
    """The password a seed mints, or a message that says how to set it.

    Only asked for when an account is about to be created: an existing account
    keeps its own password, so a database that has already been seeded needs no
    value here at all.
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
            "[seed] WARNING: role catalog is empty - the role seed must run "
            f"before this script (wanted {ADMIN_ROLE})"
        )
    else:
        print(f"[seed] {school.code}: {user.email} roles: {applied}")


def _seed_platform_admin(session: Session, entry: dict[str, str]) -> None:
    """Register one platform account: no school, so its permissions apply everywhere.

    This is the account a deployment uses to switch between schools; the login is
    `SEED_PLATFORM_ADMIN_LOGIN` verbatim (the app signs in by email, and "admin" is
    a valid one), the password is `SEED_PLATFORM_ADMIN_PASSWORD`.
    """
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
            "[seed] WARNING: role catalog is empty - the role seed must run "
            f"before this script (wanted {entry['role']})"
        )
    else:
        print(f"[seed] platform: {user.email} roles: {applied}")


def seed_data() -> None:
    """The platform accounts first, then one school + one admin per entry.

    The **system admin** is seeded before the schools on purpose: it is the account
    that can see every school, so it exists before any school does.
    """
    with Session(engine) as session:
        for entry in PLATFORM_ADMINS:
            _seed_platform_admin(session, entry)
        for entry in SCHOOLS:
            _seed_school(session, entry)


if __name__ == "__main__":
    seed_data()
