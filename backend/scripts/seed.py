"""Seed the single platform admin.

Everything else the product needs is created by the product itself: a school is
created by registering it (and owns its `school_admin`), students come from
admission, and staff from hiring. This file therefore creates exactly **one**
account - the platform administrator - plus its chat threads.

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
from app.domains.users.models import User


#: The one account this seed creates: the platform administrator.
ADMIN_EMAIL = "admin@educonnect.com"
ADMIN_NAME = "System Admin"
ADMIN_PASSWORD = "admin123"
ADMIN_ROLES = ["system_admin"]


def seed_data():
    with Session(engine) as session:
        # No "users already exist, skip everything" guard: this seed owns exactly
        # one account, and re-running it must be able to repair that account. A
        # blanket skip is what let an emptied `user_role` table go unnoticed.
        print("Seeding the platform admin...")
        user = session.exec(select(User).where(User.email == ADMIN_EMAIL)).first()
        if user is None:
            user = User(
                email=ADMIN_EMAIL,
                full_name=ADMIN_NAME,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_active=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"[seed] created {ADMIN_EMAIL}")
        else:
            print(f"[seed] {ADMIN_EMAIL} already exists - re-applying its role")

        # Nobody else is seeded: principal, teachers, students, guardians and
        # staff are created by product flows (school registration, admission,
        # hiring), so a seed must not invent them.
        #
        # Re-applying the role on every start is what heals a database whose
        # `user_role` rows were lost: the account keeps working instead of
        # silently holding zero permissions.
        applied = set_user_roles(session, user, ADMIN_ROLES)
        if not applied:
            print(
                "[seed] WARNING: role catalog is empty - the role seed must run "
                f"before this script (wanted {ADMIN_ROLES})"
            )
        else:
            print(f"[seed] roles: {applied}")

        # The class structure is seeded by scripts/seed_academics.py, not here.
        from app.domains.chat.service import ensure_default_threads

        ensure_default_threads(session, user.id)

        print("✅ Database successfully seeded!")


if __name__ == "__main__":
    seed_data()
