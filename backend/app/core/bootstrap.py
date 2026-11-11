"""Startup bootstrap: database -> schema -> migrations -> seeds.

The seeds are the numbered scripts in `scripts/seed/` (`01_roles_seed.py`,
`02_permissions_seed.py`, `03_school_seed.py`, `04_academics_seed.py`), run in
filename order by `scripts/seed/run_seeds.py`. A failing step is logged and
skipped, never fatal.
"""

import importlib.util
import logging
import sys
import time
import traceback
from pathlib import Path

import psycopg2
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parents[2]

logger = logging.getLogger("eduverse.bootstrap")


def target_label() -> str:
    """`host:port/db (managed|self-run)` - which database this process is on.

    The one implementation is `app.core.schema.target_label`; imported lazily
    because that module loads every model at import time, and the first boot step
    (creating a database) must not depend on the models being importable.
    """
    from app.core.schema import target_label as label

    return label()


def _ensure_stdout_utf8() -> None:
    """seed.py prints emoji; avoid UnicodeEncodeError on cp1252 consoles."""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def ensure_database() -> bool:
    """Create the configured database if it doesn't exist. Returns True if created."""
    if settings.is_managed_db:
        # A managed provider (Supabase) owns its databases: the app only ever
        # connects to the one its DSN names, never creates it.
        print("[bootstrap] Managed database (DATABASE_URL_OVERRIDE) - skipping create")
        return False
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
    if settings.is_managed_db:
        # Same reasoning as `ensure_database`: the provider owns the schema
        # (`public` on Supabase), and a custom one has to pre-exist.
        print("[bootstrap] Managed database - skipping schema create")
        return False
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


def _recorded_revision() -> str | None:
    """The revision already applied in this database (`alembic_version`), if any."""
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass(%s) IS NOT NULL",
                (f"{settings.DB_SCHEMA}.alembic_version",),
            )
            if not cur.fetchone()[0]:
                return None
            cur.execute(f'SELECT version_num FROM "{settings.DB_SCHEMA}".alembic_version')
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def check_connection() -> None:
    """Prove the DSN answers, and name the server that answered it.

    `/health` says the process is up; it never touches the database, so a boot
    that lost its connection still looks healthy. This is the line that does.
    """
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = (cur.fetchone() or ("?",))[0]
    finally:
        conn.close()
    server = version.split(" on ")[0]
    print(f"[bootstrap] database connected: {target_label()} - {server}")


def run_migrations() -> None:
    """Apply pending Alembic migrations (no-op when already at head).

    A database stamped with a revision that is **not** in this branch's history is
    left untouched instead of crashing the boot: that is what a schema built from
    another branch looks like, and replaying a history it was never on would
    damage it. The message is loud, so a real mismatch cannot pass unnoticed.
    """
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))

    script = ScriptDirectory.from_config(cfg)
    known = {rev.revision for rev in script.walk_revisions()}
    head = script.get_current_head()
    current = _recorded_revision()
    if current is not None and current not in known:
        print(
            f"[bootstrap] database revision '{current}' is not in this branch's "
            "migration history - skipping migrations (its schema is managed by "
            "the branch that created it)"
        )
        return
    if current == head:
        print(f"[bootstrap] migrations complete: already at head ({head})")
        return

    command.upgrade(cfg, "head")
    print(f"[bootstrap] migrations complete: {current or 'base'} -> {head}")


def run_seeds() -> None:
    """Run `scripts/seed/NN_*_seed.py` in filename order - the seeds are scripts."""
    seed_path = BASE_DIR / "scripts" / "seed" / "run_seeds.py"
    spec = importlib.util.spec_from_file_location("eduverse_run_seeds", seed_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.run() != 0:
        raise RuntimeError("one or more seed scripts failed (see above)")


def bootstrap() -> None:
    """Run every boot step, timing each, and say loudly what failed.

    Nothing here is fatal: the API still starts so `/health` can answer and the
    logs can be read. What must never happen again is a failed step passing
    silently (it did once - seeds failed, the API served 401s, boot looked fine).
    """
    _ensure_stdout_utf8()
    started = time.perf_counter()
    print(f"[bootstrap] environment: {settings.ENVIRONMENT}")
    steps = (
        ("database", ensure_database),
        ("schema", ensure_schema),
        ("connection", check_connection),
        ("migrations", run_migrations),
        ("seeds", run_seeds),
    )
    failed: list[str] = []
    for name, fn in steps:
        step_started = time.perf_counter()
        try:
            fn()
            print(f"[bootstrap] {name} ok in {time.perf_counter() - step_started:.1f}s")
        except Exception as exc:
            failed.append(name)
            print(f"[bootstrap] {name} step FAILED: {exc}")
            traceback.print_exc()
            logger.exception("[bootstrap] %s step failed: %s", name, exc)

    took = time.perf_counter() - started
    if failed:
        print(f"[bootstrap] finished in {took:.1f}s - failed step(s): {', '.join(failed)}")
    else:
        print(f"[bootstrap] ready in {took:.1f}s")
