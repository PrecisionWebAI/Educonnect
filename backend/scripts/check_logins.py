"""Can the seeded logins still sign in? - the drift a schema check cannot see.

Why this exists
---------------
`scripts/seed.py` mints an account's password **once**, when it creates the row,
and never touches it again: an existing account keeps its own password (see
`_required` there). That is deliberate - re-running a seed must never re-key a
live deployment - but it has a consequence worth checking. The value in
`backend/.env` and the hash in the database can disagree, and nothing reports it.
The symptom is a login that "suddenly" stops working: after `SEED_*_PASSWORD` was
edited, or on one database but not the other (Supabase was rebuilt from the
models, local was not).

So this compares what the seed *would* write with what each seeded account
actually holds. It reads; it never writes unless asked:

    OK       the env value verifies against the stored hash
    DRIFT    it does not - the account keeps the password it was created with
    MISSING  the account is not in this database - the seed has not run here

There are two more ways to be useless without being unable to sign in, so both
count as DRIFT as well: an inactive account (the login is refused) and an account
holding no role (it signs in and sees nothing).

Usage:

    python scripts/check_logins.py

The database is whatever the environment describes, exactly like
`scripts/check_schema.py`: `backend/.env` normally, `DATABASE_URL_OVERRIDE` for
anything else. `db_sync.py` sets that for `--target supabase`, and CI sets it from
the `SUPABASE_DB_URL` secret, so both targets are covered by the same command.

`--repair` is the only way this file writes, and it exists for one situation: a
database was seeded before the value in `backend/.env` changed, so the two will
never agree on their own - that is what "seeded only" means. It re-hashes those
accounts to the env value and prints every one it touches. Nothing calls it: not a
boot, not `db_sync.py`, not CI.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session, select  # noqa: E402

from app.core import schema  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import engine  # noqa: E402
from app.core.security import get_password_hash, verify_password  # noqa: E402
from app.domains.auth.roles import role_codenames  # noqa: E402
from app.domains.users.models import User  # noqa: E402

# Importing the seed gives this file the accounts and roles it checks, so an
# account added there is checked here without anyone remembering to add it twice.
from scripts.seed import ADMIN_ROLE, PLATFORM_ADMINS, SCHOOLS  # noqa: E402



def _expected() -> list[tuple[str, str, str]]:
    """`(login, password, role)` for every account `seed.py` creates.

    The password is the value from the environment - the one the seed would use
    for a database it had not seeded yet. For an account that already exists that
    is precisely the value which may no longer apply.
    """
    platform = [
        (
            settings.SEED_PLATFORM_ADMIN_LOGIN,
            settings.SEED_PLATFORM_ADMIN_PASSWORD,
            entry["role"],
        )
        for entry in PLATFORM_ADMINS
    ]
    schools = [
        (entry["login"], settings.SEED_SCHOOL_ADMIN_PASSWORD, ADMIN_ROLE)
        for entry in SCHOOLS
    ]
    return platform + schools


def _find(session: Session, login: str) -> User | None:
    return session.exec(select(User).where(User.email == login)).first()


def _repair(session: Session) -> int:
    """Re-hash the accounts the env value no longer opens. Returns how many.

    Only the hash is written. An account that is inactive or holds no role is left
    alone - that is not a password problem, and the audit below still reports it.
    """
    changed = 0
    for login, password, _role in _expected():
        if not password:
            continue
        user = _find(session, login)
        if user is None or verify_password(password, user.hashed_password):
            continue
        user.hashed_password = get_password_hash(password)
        session.add(user)
        changed += 1
        print(f"  re-hashed {login} to the value in the environment")
    if changed:
        session.commit()
    return changed


def _problems(session: Session, login: str, password: str, role: str) -> list[str]:
    """Everything that would stop this account from being usable."""
    user = _find(session, login)
    if user is None:
        return ["not in this database - the seed has not run here"]

    found: list[str] = []
    if not password:
        found.append("no password in the environment (SEED_*_PASSWORD is empty)")
    elif not verify_password(password, user.hashed_password):
        found.append("keeps the password it was created with")
    if not user.is_active:
        found.append("inactive - the login is refused")
    if role not in role_codenames(session, user.id):
        found.append(f"holds no {role} role - it would sign in and see nothing")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repair",
        action="store_true",
        help="re-hash accounts whose stored password the environment no longer "
        "opens (opt-in; prints every account it touches)",
    )
    args = parser.parse_args()

    # Importing the domains switches SQLAlchemy's statement log back on; the
    # report's own lines are what matters here.
    schema.quiet()

    print(f"target           {schema.target_label()}")

    with Session(engine) as session:
        if args.repair:
            changed = _repair(session)
            print(f"repair           {changed or 'nothing to do'}")

        drift = 0
        for login, password, role in _expected():
            found = _problems(session, login, password, role)
            drift += 1 if found else 0
            state = "DRIFT" if found else "OK"
            line = f"  {login:<14} {role:<13} {state}"
            print(f"{line} - {'; '.join(found)}" if found else line)

    total = len(_expected())
    print(f"logins           {total - drift} of {total} usable")

    if drift:
        print(
            "\nDRIFT: the seed never re-keys an existing account - that is what "
            "'seeded only' means -\nso a value changed in backend/.env applies to "
            "new databases only. Either put the old\nvalue back, or run "
            "`python scripts/check_logins.py --repair` deliberately."
        )
        return 1
    print("\nOK: every seeded login opens with the value in the environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
