"""Startup bootstrap.

On every application start this ensures, in order:
1. The configured database exists (created if missing).
2. The configured schema (e.g. demo_school) exists (created if missing).
3. Alembic migrations are applied (no-op if already up to date).
4. Demo seed data is loaded (skipped if users already exist).

Failure of any step is logged but never prevents the API from starting.
"""

import importlib.util
import logging
import sys
import traceback
from pathlib import Path

import psycopg2
from alembic.config import Config

from alembic import command
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parents[2]

logger = logging.getLogger("eduverse.bootstrap")


def _ensure_stdout_utf8() -> None:
    """seed.py prints emoji; avoid UnicodeEncodeError on cp1252 consoles."""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def ensure_database() -> bool:
    """Create the configured database if it doesn't exist. Returns True if created."""
    admin_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.DB_NAME,))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
        print(f"[bootstrap] Created database '{settings.DB_NAME}'")
    else:
        print(f"[bootstrap] Database '{settings.DB_NAME}' exists")
    cur.close()
    conn.close()
    return not exists


def ensure_schema() -> bool:
    """Create the configured schema if it doesn't exist. Returns True if created."""
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
        (settings.DB_SCHEMA,),
    )
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(f'CREATE SCHEMA "{settings.DB_SCHEMA}"')
        print(f"[bootstrap] Created schema '{settings.DB_SCHEMA}'")
    else:
        print(f"[bootstrap] Schema '{settings.DB_SCHEMA}' exists")
    cur.close()
    conn.close()
    return not exists


def run_migrations() -> None:
    """Apply pending Alembic migrations (no-op when already at head)."""
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    command.upgrade(cfg, "head")
    print("[bootstrap] Migrations up to date")


def run_seed() -> None:
    """Load demo data (scripts/seed.py skips itself if data already exists)."""
    seed_path = BASE_DIR / "scripts" / "seed.py"
    spec = importlib.util.spec_from_file_location("eduverse_seed", seed_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed_data()


def seed_permissions() -> None:
    """Idempotently seed the Permission and RolePermission tables from the static map."""
    # Import models so SQLModel is aware of the new tables
    from sqlmodel import Session

    import app.domains.auth.models  # noqa: F401
    from app.core.db import engine
    from app.domains.auth.permissions_repository import seed_permissions as _seed

    with Session(engine) as session:
        _seed(session)


def bootstrap() -> None:
    _ensure_stdout_utf8()
    steps = (
        ("database", lambda: ensure_database()),
        ("schema", lambda: ensure_schema()),
        ("migrations", run_migrations),
        ("seed", run_seed),
        ("permissions_seed", seed_permissions),
    )
    for name, fn in steps:
        try:
            fn()
        except Exception as exc:
            # Failures here used to be hidden (single print line), which allowed
            # e.g. seed failures to go unnoticed while the API kept serving 401s.
            # Surface the full traceback prominently so this can't happen silently again.
            print(f"[bootstrap] {name} step FAILED: {exc}")
            traceback.print_exc()
            logger.exception("[bootstrap] %s step failed: %s", name, exc)
