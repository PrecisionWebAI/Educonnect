"""Put THE database on the current schema and seed it - one command, one target.

    python scripts/db_sync.py                       # backend/.env's database
    python scripts/db_sync.py --target supabase     # SUPABASE_DB_URL (same one)
    python scripts/db_sync.py --verify-only
    python scripts/db_sync.py --rebuild --yes --i-mean-production   # DESTRUCTIVE

`make db-sync` / `make db-supabase` are thin wrappers around this.

There is one database now: the Supabase project that both a laptop and the
deployed API use. The two target names are kept because a checkout may carry a
different `DATABASE_URL_OVERRIDE` than `SUPABASE_DB_URL`; when they name the same
host and database (the normal case) the run says so, instead of implying two.

Stages, each in its own process so a fresh engine is built for the target:

1. **preflight** - where we are (host/db, never the password), which revision the
   database is on, whether the model tables exist.
2. **schema** - `init_schema.py` when the tables are missing (the models are the
   source of truth), otherwise `alembic upgrade head`. `--rebuild` drops the model
   tables first, which needs `--yes` - and, on a managed database, also
   `--i-mean-production`, because that is somebody's live data.
3. **seed** - `app/core/bootstrap.py`, the same path a boot takes: role catalog,
   schools and their admins, the class catalog, the RBAC grants. No demo rows:
   `scripts/auto_seeder_by_admission_form_and_teacher_form.py` is manual only.
4. **verify** - `scripts/check_schema.py` (models vs database) and
   `scripts/check_logins.py` (do the seeded logins still open with the values in
   `backend/.env`). Either one fails the run on drift.
"""

import argparse
import os
import subprocess
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: `env` = whatever `backend/.env` says (the only database); `supabase` = the
#: same project named again by `SUPABASE_DB_URL`.
ENV_TARGET = "env"

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


def _normalise(target: str) -> str:
    """`local` was the old name for "whatever backend/.env says" - keep it working."""
    if target == "local":
        print("note: --target local is now --target env (backend/.env IS the database)")
        return ENV_TARGET
    return target


def _same_database(left: str, right: str) -> bool:
    """Do two DSNs name the same host and database? (Credentials ignored.)"""
    if not left or not right:
        return False
    a, b = urlsplit(left), urlsplit(right)
    return (a.hostname, (a.path or "").rstrip("/")) == (
        b.hostname,
        (b.path or "").rstrip("/"),
    )


def _env_for(target: str) -> dict[str, str]:
    """The child processes' environment: the target's DSN, nothing else changed."""
    env = dict(os.environ)
    if target == ENV_TARGET:
        # `backend/.env` already describes it; an override from the shell would
        # quietly win, so only a managed DSN is passed down explicitly.
        if settings.is_managed_db:
            env["DATABASE_URL_OVERRIDE"] = settings.DATABASE_URL
        else:
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


def _verify(env: dict[str, str]) -> int:
    """Both halves of "this database is right": the schema, then the logins.

    Both always run, even when the first one fails - the two reports together are
    what says whether a database can be signed in to, so stopping at the first
    would hide half the answer.
    """
    schema_code = _run("verify (schema)", ["scripts/check_schema.py"], env)
    login_code = _run("verify (logins)", ["scripts/check_logins.py"], env)
    return schema_code or login_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=(ENV_TARGET, "supabase", "local"),
        default=ENV_TARGET,
        help=(
            f"{ENV_TARGET} = the DSN in backend/.env (the database); "
            "supabase = SUPABASE_DB_URL, usually the same one; "
            "local = the old name for env"
        ),
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="drop the model tables and recreate them (DESTRUCTIVE)",
    )
    parser.add_argument("--yes", action="store_true", help="confirm --rebuild")
    parser.add_argument(
        "--i-mean-production",
        dest="i_mean_production",
        action="store_true",
        help="confirm --rebuild on a managed database (there is no local copy)",
    )
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    target = _normalise(args.target)
    env = _env_for(target)

    if args.rebuild and not args.yes:
        raise SystemExit(
            "--rebuild drops every model table. Take a dump first, then add --yes."
        )
    # There is no second database any more: a drop here is a drop of live data.
    managed = target == "supabase" or settings.is_managed_db
    if args.rebuild and managed and not args.i_mean_production:
        raise SystemExit(
            "--rebuild drops every model table in the MANAGED database named by\n"
            "backend/.env. There is no local copy to fall back on, so take a\n"
            "pg_dump first - then add --i-mean-production if that is really what\n"
            "you want."
        )
    if target == "supabase" and _same_database(
        settings.DATABASE_URL, settings.SUPABASE_DB_URL
    ):
        print("note: SUPABASE_DB_URL is the same database as backend/.env")

    info = _preflight(env)
    print(f"target           {info['TARGET']}")
    print(f"alembic          current={info['CURRENT']} head={info['HEAD']}")
    print(f"model tables     {info['EXISTING']} of {info['EXPECTED']} present")

    if args.verify_only:
        return _verify(env)

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

    # 3. Verify - the checks that make the whole run meaningful.
    return _verify(env)


if __name__ == "__main__":
    raise SystemExit(main())
