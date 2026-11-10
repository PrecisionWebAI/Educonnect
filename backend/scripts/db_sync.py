"""Put a database on the current schema and seed it - one command, two targets.

    python scripts/db_sync.py --target local
    python scripts/db_sync.py --target supabase
    python scripts/db_sync.py --target supabase --demo
    python scripts/db_sync.py --target supabase --verify-only
    python scripts/db_sync.py --target supabase --rebuild --yes    # DESTRUCTIVE

`make db-local` / `make db-supabase` are thin wrappers around this.

Stages, each in its own process so a fresh engine is built for the target:

1. **preflight** - where we are (host/db, never the password), which revision the
   database is on, whether the model tables exist.
2. **schema** - `init_schema.py` when the tables are missing (the models are the
   source of truth), otherwise `alembic upgrade head`. `--rebuild` drops the model
   tables first, which needs `--yes`.
3. **seed** - `app/core/bootstrap.py`, the same path a boot takes: role catalog,
   schools and their admins, the class catalog, the RBAC grants.
4. **demo** - `--demo` adds the demo roll (students, staff, register). Thousands
   of rows, so it is off by default on a managed database.
5. **verify** - `scripts/check_schema.py`, which fails the run on any drift.

The target's DSN comes from the environment: `--target local` uses `backend/.env`
as-is, `--target supabase` uses `SUPABASE_DB_URL` from that same file.
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PREFLIGHT = (
    "from app.core import schema as s;"
    "s.load_models();s.quiet();"
    "print('TARGET=' + s.target_label());"
    "print('CURRENT=' + (s.current_revision() or '-'));"
    "print('HEAD=' + s.head_revision());"
    "print('EXISTING=' + str(len(s.existing_model_tables())));"
    "print('EXPECTED=' + str(len(s.expected_tables())))"
)

BOOTSTRAP = "from app.core.bootstrap import bootstrap; bootstrap()"


def _env_for(target: str) -> dict[str, str]:
    """The child processes' environment: the target's DSN, nothing else changed."""
    env = dict(os.environ)
    if target == "local":
        # `backend/.env` already describes it; an override from the shell would
        # quietly win, so drop it.
        env.pop("DATABASE_URL_OVERRIDE", None)
        return env

    dsn = settings.SUPABASE_DB_URL
    if not dsn:
        raise SystemExit(
            "SUPABASE_DB_URL is empty. Put the Supabase connection string in\n"
            "backend/.env (see backend/.env-example) and run this again."
        )
    env["DATABASE_URL_OVERRIDE"] = dsn
    return env


def _run(label: str, args: list[str], env: dict[str, str]) -> int:
    """Run one stage, echoing its output, and report how long it took."""
    print(f"\n=== {label} " + "=" * max(0, 60 - len(label)))
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        check=False,
    )
    seconds = time.monotonic() - started
    state = "ok" if result.returncode == 0 else f"FAILED ({result.returncode})"
    print(f"--- {label}: {state} in {seconds:.1f}s")
    return result.returncode


def _preflight(env: dict[str, str]) -> dict[str, str]:
    """Ask the target what it looks like, before changing anything."""
    result = subprocess.run(
        [sys.executable, "-c", PREFLIGHT],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot reach the target:\n{result.stderr.strip()}")
    return dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("local", "supabase"), default="local")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="drop the model tables and recreate them (DESTRUCTIVE)",
    )
    parser.add_argument("--yes", action="store_true", help="confirm --rebuild")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="also run the demo roll (students, staff, register)",
    )
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    env = _env_for(args.target)

    if args.rebuild and not args.yes:
        raise SystemExit(
            "--rebuild drops every model table. Take a dump first, then add --yes."
        )

    info = _preflight(env)
    print(f"target           {info['TARGET']}")
    print(f"alembic          current={info['CURRENT']} head={info['HEAD']}")
    print(f"model tables     {info['EXISTING']} of {info['EXPECTED']} present")

    if args.verify_only:
        return _run("verify", ["scripts/check_schema.py"], env)

    existing = int(info["EXISTING"])
    expected = int(info["EXPECTED"])

    # 1. Schema: models for a database that is missing them, the chain otherwise.
    if args.rebuild or existing == 0:
        schema_args = ["scripts/init_schema.py"]
        if args.rebuild:
            schema_args.append("--force")
        stage = "schema (create from models)"
    elif existing < expected:
        schema_args = ["scripts/init_schema.py"]
        stage = "schema (add the missing tables)"
    else:
        schema_args = ["-m", "alembic", "upgrade", "head"]
        stage = "schema (alembic upgrade head)"
    if _run(stage, schema_args, env) != 0:
        return 1

    # 2. Seeds - the same bootstrap a boot runs.
    if not args.skip_seed and _run("seed (bootstrap)", ["-c", BOOTSTRAP], env) != 0:
        return 1

    # 3. Demo roll, on request only: it writes thousands of rows.
    demo_failed = args.demo and _run(
        "seed (demo roll)",
        ["scripts/auto_seeder_by_admission_form_and_teacher_form.py"],
        env,
    )
    if demo_failed:
        print("\nthe demo roll did not finish - re-run to continue (idempotent)")
        return 1

    # 4. Verify - the check that makes the whole run meaningful.
    return _run("verify", ["scripts/check_schema.py"], env)


if __name__ == "__main__":
    raise SystemExit(main())
