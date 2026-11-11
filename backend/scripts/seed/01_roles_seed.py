"""01 - the role catalog. Roles are rows, so nothing else would create them."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlmodel import Session

from app.core.db import engine
from app.domains.auth.permissions_repository import seed_roles


def main() -> None:
    with Session(engine) as session:
        created = seed_roles(session)
    print(f"[seed] 01_roles_seed: {created} created")


if __name__ == "__main__":
    main()
