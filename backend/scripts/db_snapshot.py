"""Snapshot a database - row counts, no writes, one target at a time.

    python scripts/db_snapshot.py                  # the backend/.env database
    python scripts/db_snapshot.py --json
    python scripts/db_snapshot.py --compare env supabase   # only if they differ

Read-only by construction: it opens a connection, counts rows and exits. The
output is JSON, so two snapshots can be diffed - and `--compare` exits non-zero
when the targets disagree, which is what made it usable as a gate next to
`check_schema.py` when a laptop still had its own Postgres.

With one database there is nothing to compare: `env` and `supabase` both resolve
to the same Supabase project, so `--compare` refuses instead of printing a
meaningless "IDENTICAL". `make db-diff` was removed for the same reason; the
script stays for comparing against a branch / snapshot database later.

The counting happens in a **child process**: the target is chosen by
`DATABASE_URL_OVERRIDE`, and `app.core.db` builds its engine at import time, so
the parent has to hand the child a prepared environment (the same trick
`db_sync.py` uses for its stages).
"""

import argparse
import json
import os
import subprocess
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = os.path.abspath(__file__)


def _normalise(target: str) -> str:
    """`local` was the old name for "whatever backend/.env says" - keep it working."""
    return "env" if target == "local" else target


def _same_database(left: str, right: str) -> bool:
    """Do two DSNs name the same host and database? (Credentials ignored.)"""
    a, b = urlsplit(left), urlsplit(right)
    return (a.hostname, (a.path or "").rstrip("/")) == (
        b.hostname,
        (b.path or "").rstrip("/"),
    )

#: Columns that identify generated people. The demo roll put `.demo` in every
#: address it invented, so the marker is part of the data, not a flag.
DEMO_MARKERS = (
    ("user", "email"),
    ("student", "student_email"),
    ("guardian", "email"),
    ("employee", "email"),
)


def _snapshot() -> dict:
    """Count what is in the database this process is pointed at."""
    import warnings

    warnings.filterwarnings("ignore")

    from sqlalchemy import text

    from app.core import schema as s
    from app.core.config import settings
    from app.core.db import engine

    s.load_models()
    s.quiet()

    with engine.connect() as conn:
        revision = conn.execute(
            text("select version_num from alembic_version")
        ).scalar()

        tables: dict[str, int | None] = {}
        for name in sorted(s.expected_tables()):
            try:
                tables[name] = conn.execute(
                    text(f'select count(*) from "{name}"')
                ).scalar()
            except Exception:
                # Missing or unreadable: `None` keeps the table visible in the
                # report instead of silently dropping it.
                tables[name] = None

        demo: dict[str, int | None] = {}
        for table, column in DEMO_MARKERS:
            try:
                demo[f"{table}.{column}"] = conn.execute(
                    text(
                        f"select count(*) from \"{table}\" "
                        f"where \"{column}\" ilike '%demo%'"
                    )
                ).scalar()
            except Exception:
                demo[f"{table}.{column}"] = None

    dsn = settings.DATABASE_URL
    return {
        "managed": settings.is_managed_db,
        # Never the credentials: the host/database is enough to tell the two apart.
        "where": dsn.rsplit("@", 1)[-1],
        "revision": revision,
        "tables": tables,
        "demo": demo,
        "rows": sum(count for count in tables.values() if count),
    }



def _env_for(target: str) -> dict[str, str]:
    """The child process's environment: the target's DSN, nothing else changed."""
    from app.core.config import settings

    env = dict(os.environ)
    if target == "env":
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


def snapshot(target: str) -> dict:
    """Probe one target in its own process and return the parsed snapshot."""
    result = subprocess.run(
        [sys.executable, SELF, "--_probe"],
        cwd=ROOT,
        env=_env_for(target),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"Snapshot of {target} failed.")
    payload = [line for line in result.stdout.splitlines() if line.startswith("{")]
    if not payload:
        raise SystemExit(f"Snapshot of {target} printed no JSON:\n{result.stdout}")
    data = json.loads(payload[-1])
    data["target"] = target
    return data


def _cell(value) -> str:
    return "missing" if value is None else str(value)


def _print_one(data: dict) -> None:
    print(
        f"{data['target']}: {data['where']} "
        f"(revision {data['revision']}, {data['rows']} rows)"
    )
    for name, count in data["tables"].items():
        if count:
            print(f"  {name:34s}{count}")
    demo = ", ".join(f"{key}={_cell(value)}" for key, value in data["demo"].items())
    print(f"  demo: {demo}")


def compare(left: dict, right: dict, show_all: bool = False) -> int:
    """Print the differences and return how many tables disagree."""
    diffs = 0
    print(f"left : {left['target']} {left['where']} (revision {left['revision']})")
    print(f"right: {right['target']} {right['where']} (revision {right['revision']})")
    if left["revision"] != right["revision"]:
        print("!! different alembic revision")
        diffs += 1

    print(f"\n{'table':34s}{'left':>10s}{'right':>10s}{'delta':>10s}")
    for name in sorted(set(left["tables"]) | set(right["tables"])):
        a = left["tables"].get(name)
        b = right["tables"].get(name)
        if a == b and not show_all:
            continue
        delta = "" if a is None or b is None else f"{b - a:+d}"
        print(f"{name:34s}{_cell(a):>10s}{_cell(b):>10s}{delta:>10s}")
        if a != b:
            diffs += 1

    print(f"\n{'demo marker':34s}{'left':>10s}{'right':>10s}")
    for key in sorted(set(left["demo"]) | set(right["demo"])):
        print(
            f"{key:34s}{_cell(left['demo'].get(key)):>10s}"
            f"{_cell(right['demo'].get(key)):>10s}"
        )
    print(f"{'rows total':34s}{left['rows']:>10d}{right['rows']:>10d}")
    print("\nIDENTICAL" if not diffs else f"\n{diffs} difference(s)")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", choices=["env", "supabase", "local"])
    ap.add_argument(
        "--compare",
        nargs=2,
        metavar=("LEFT", "RIGHT"),
        choices=["env", "supabase", "local"],
        help="snapshot both targets and diff them (refused when they are one database)",
    )
    ap.add_argument("--all", action="store_true", help="list equal tables too")
    ap.add_argument("--json", dest="as_json", action="store_true", help="raw JSON")
    ap.add_argument("--_probe", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args._probe:
        print(json.dumps(_snapshot()))
        return 0
    if args.compare:
        left_target, right_target = (_normalise(target) for target in args.compare)
        if left_target == right_target:
            raise SystemExit("--compare needs two different targets")

        from app.core.config import settings

        left_dsn = (
            settings.DATABASE_URL if left_target == "env" else settings.SUPABASE_DB_URL
        )
        right_dsn = (
            settings.DATABASE_URL if right_target == "env" else settings.SUPABASE_DB_URL
        )
        if left_dsn and right_dsn and _same_database(left_dsn, right_dsn):
            parts = urlsplit(left_dsn)
            host = parts.hostname or "?"
            database = (parts.path or "").rstrip("/")
            raise SystemExit(
                f"both targets are the same database ({host}{database}): there is\n"
                "nothing to compare. Use --target for a plain snapshot instead."
            )

        left, right = (snapshot(target) for target in (left_target, right_target))
        if args.as_json:
            print(json.dumps({"left": left, "right": right}, indent=2))
            return 0
        return 1 if compare(left, right, args.all) else 0
    if not args.target:
        ap.error("give --target or --compare")

    data = snapshot(_normalise(args.target))
    if args.as_json:
        print(json.dumps(data, indent=2))
    else:
        _print_one(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
