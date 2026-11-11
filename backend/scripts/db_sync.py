k"""Schema + seeds + verification for the database in backend/.env.

    python scripts/db_sync.py                        # full run
    python scripts/db_sync.py --target supabase      # same DB via SUPABASE_DB_URL
    python scripts/db_sync.py --verify-only
    python scripts/db_sync.py --rebuild --yes --i-mean-production   # DESTRUCTIVE
    python scripts/db_sync.py --wipe --backup rows.json --yes --i-mean-production

  1. preflight - host/db, alembic revision, which model tables exist
  2. schema    - init_schema.py when tables are missing, else alembic upgrade head
  3. seeds     - bootstrap(), i.e. scripts/seed/run_seeds.py (01_roles_seed .. 04_academics_seed)
  4. verify    - check_schema.py + check_logins.py

`--wipe` is the other direction: it deletes every row of every model table and
stops. The tables and the alembic revision stay, so the next run (or the next
boot) seeds it again instead of rebuilding it. `--backup PATH` writes the rows to
JSON first, because a managed database has no local copy to fall back on.

`env` and `supabase` normally name the same database; the run says so when they do.
`local` is kept as an alias for `env`.
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

#: Delete every row, keep every table - then say what it left behind.
WIPE = (
    "from app.core import schema as s;"
    "s.load_models();s.quiet();"
    "before=sum(s.row_counts().values());"
    "tables=s.truncate_model_tables();"
    "after=sum(s.row_counts().values());"
    "print(f'[wipe] {before} row(s) in {tables} table(s) -> {after} row(s) left')"
)


def _backup_snippet(path: str) -> str:
    """A one-liner that saves every row to `path` before they are deleted."""
    return (
        "from app.core import schema as s;"
        "s.load_models();s.quiet();"
        f"tables=s.backup_rows({path!r});"
        "print('[wipe] %d table(s) saved to %s' % (tables, " + repr(path) + "))"
    )


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
        "--wipe",
        action="store_true",
        help="delete every row of every model table, keep the schema (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--backup",
        metavar="PATH",
        help="save every row to PATH (JSON) before --wipe deletes them",
    )
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
    if args.wipe and not args.yes:
        raise SystemExit(
            "--wipe deletes every row in every model table. Add --yes once you\n"
            "mean it; --backup PATH first is cheap."
        )
    if args.wipe and not args.i_mean_production:
        raise SystemExit(
            "--wipe empties the database named by backend/.env, which the\n"
            "deployed app also serves. Save the rows first (--backup PATH, or a\n"
            "pg_dump), then add --i-mean-production if that is really what you\n"
            "want."
        )
    if target == "supabase" and _same_database(
        settings.DATABASE_URL, settings.SUPABASE_DB_URL
    ):
        print("note: SUPABASE_DB_URL is the same database as backend/.env")

    info = _preflight(env)
    print(f"target           {info['TARGET']}")
    print(f"alembic          current={info['CURRENT']} head={info['HEAD']}")
    print(f"model tables     {info['EXISTING']} of {info['EXPECTED']} present")

    if args.wipe:
        if args.backup is not None:
            backup_code = _run(
                "wipe (backup rows)", ["-c", _backup_snippet(args.backup)], env
            )
            if backup_code != 0:
                print("\n[wipe] nothing deleted - the backup failed.")
                return backup_code
        if _run("wipe (truncate)", ["-c", WIPE], env) != 0:
            return 1
        print(
            "\n[wipe] schema kept, alembic revision untouched. The next run - or\n"
            "[wipe] the next boot - seeds it again (bootstrap() -> scripts/seed/*)."
        )
        return 0

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
