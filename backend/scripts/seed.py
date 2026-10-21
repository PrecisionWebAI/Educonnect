"""Register the demo school and the one account that runs it.

This seed does exactly two things:

  1. a `school` row - the school's registration record
  2. one `user` for it, whose login is built from the school's code:
     school `abc` -> `admin@abc`, holding the `school_admin` role and linked to
     that school through `user.school_id`

Everything else has its own seed or belongs to a product flow: the role catalog
and the RBAC grants come from `bootstrap.seed_roles()` / `seed_permissions()`, the
class structure from `scripts/seed_academics.py`, and students / staff from
admission and hiring.

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


#: The school this seed registers. `code` is the slug the logins are built from,
#: so changing it changes the admin's address too.
SCHOOL_NAME = "ABC School"
SCHOOL_CODE = "abc"
SCHOOL_EMAIL = "office@abc"
SCHOOL_PHONE = "+91 90000 00000"
SCHOOL_ADDRESS = "Sector 1, Demo City"

#: The one account the school gets, and its first password.
ADMIN_NAME = "School Admin"
ADMIN_PASSWORD = "admin123"
ADMIN_ROLE = "school_admin"


def seed_data():
    """Register the school (once) and reconcile its admin account."""
    with Session(engine) as session:
        school = session.exec(select(School).where(School.code == SCHOOL_CODE)).first()
        if school is None:
            school = School(
                name=SCHOOL_NAME,
                code=SCHOOL_CODE,
                email=SCHOOL_EMAIL,
                phone=SCHOOL_PHONE,
                address=SCHOOL_ADDRESS,
                is_active=True,
            )
            session.add(school)
            session.commit()
            session.refresh(school)
            print(f"[seed] school '{school.name}' registered (code: {school.code})")
        else:
            print(
                f"[seed] school '{school.name}' already registered "
                f"(code: {school.code})"
            )

        # The login comes from the school's code, so each registered school gets
        # its own admin address: code `abc` -> admin@abc.
        email = f"admin@{school.code}"
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(
                email=email,
                full_name=ADMIN_NAME,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_active=True,
                school_id=school.id,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"[seed] created {email}")
        else:
            # Re-apply the school link, so an account can never drift outside the
            # tenant it administers (e.g. after a partial restore).
            user.school_id = school.id
            session.add(user)
            session.commit()
            print(f"[seed] {email} already exists - school link re-applied")

        # Re-applying the role every start also heals a database whose `user_role`
        # rows were lost: the account keeps working instead of silently holding
        # zero permissions.
        applied = set_user_roles(session, user, [ADMIN_ROLE])
        if not applied:
            print(
                "[seed] WARNING: role catalog is empty - the role seed must run "
                f"before this script (wanted {ADMIN_ROLE})"
            )
        else:
            print(f"[seed] {email} roles: {applied}")

        print("School + its admin seeded!")


if __name__ == "__main__":
    seed_data()
