"""Register the schools and the one account each of them runs on.

This is the **only** seed script. Everything else is an app-level seeder in
`app/domains/…` (roles, permissions, the class structure) because it is catalog
data the product needs; a school and its login are data a *deployment* brings, so
they live here.

Per entry in `SCHOOLS` it does exactly two things, idempotently:

  1. a `school` row - the school's registration record
  2. one `user` for it - the `school_admin`, linked through `user.school_id`

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

from app.core.db import engine
from app.core.security import get_password_hash
from app.domains.auth.roles import set_user_roles
from app.domains.schools.models import School
from app.domains.users.models import User

#: The schools this seed registers. `code` is the school's slug (and its key for
#: "already registered"); `contact` is the school's own address, `login` is the
#: address its admin signs in with.
SCHOOLS: tuple[dict[str, str], ...] = (
    {
        "name": "ABC School",
        "code": "abc",
        "contact": "office@abc",
        "phone": "+91 90000 00001",
        "address": "Sector 1, Demo City",
        "login": "admin@abc",
        "password": "adminabc123",
    },
    {
        "name": "Delhi Public School",
        "code": "dps",
        "contact": "office@dps",
        "phone": "+91 90000 00002",
        "address": "Sector 9, Demo City",
        "login": "office@dps",
        "password": "admindps123",
    },
)

#: The role every school's first account holds.
ADMIN_ROLE = "school_admin"


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
            full_name=entry["name"],
            hashed_password=get_password_hash(entry["password"]),
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


def seed_data() -> None:
    """One school + one admin per entry in `SCHOOLS`."""
    with Session(engine) as session:
        for entry in SCHOOLS:
            _seed_school(session, entry)


if __name__ == "__main__":
    seed_data()
