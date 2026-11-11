"""02 - RBAC grants: role -> permission rows from the static map."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlmodel import Session

from app.core.db import engine
from app.domains.auth.permissions_repository import seed_permissions


def main() -> None:
    with Session(engine) as session:
        seed_permissions(session)
    print("[seed] 02_permissions_seed: done")


if __name__ == "__main__":
    main()
