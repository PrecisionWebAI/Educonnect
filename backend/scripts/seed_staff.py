"""Demo hires for the Staff Hiring ▸ Registration flow.

Registers a few people through the same service the API uses, so a fresh
database has staff on the Hired tab with real logins and employee codes (the
codes the salary register pays against). Skipped when `staffprofile` already has
rows, so it is safe to run on every start.

Run it directly with:
    python scripts/seed_staff.py
"""

import os
import sys
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session, select

from app.core.db import engine
from app.domains.staff import service as staff_service
from app.domains.staff.models import StaffProfile
from app.domains.staff.schemas import StaffRegistrationCreate

#: (name, role, department, qualification, experience) - one teaching post and
#: two non-teaching ones, so both login prefixes show up.
DEMO_HIRES: tuple[dict[str, Any], ...] = (
    {
        "full_name": "Meera Iyer",
        "role_codename": "teacher",
        "department": "Science",
        "qualification": "M.Sc, B.Ed",
        "experience_years": 6,
        "contact_email": "meera.iyer@example.com",
    },
    {
        "full_name": "Asha Pillai",
        "role_codename": "librarian",
        "department": "Library",
        "qualification": "M.Lib.Sc",
        "experience_years": 4,
        "contact_email": "asha.pillai@example.com",
    },
    {
        "full_name": "Otto Mann",
        "role_codename": "transport",
        "department": "Transport",
        "qualification": "HMV Licence",
        "experience_years": 11,
    },
)


def seed_staff() -> int:
    """Register the demo hires once. Returns how many were created."""
    with Session(engine) as session:
        if session.exec(select(StaffProfile)).first():
            print("[seed_staff] staffprofile already has rows - skipped")
            return 0

        created = 0
        for entry in DEMO_HIRES:
            registered = staff_service.create_registration(
                session, StaffRegistrationCreate(**entry)
            )
            created += 1
            print(
                f"[seed_staff] hired {registered.full_name} "
                f"({registered.role_codename}) - {registered.login_email}"
            )
        return created


if __name__ == "__main__":
    print(f"[seed_staff] {seed_staff()} hire(s) registered")
