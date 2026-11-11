"""Snapshot a database - the same numbers from local and from Supabase.

    python scripts/db_snapshot.py --target local
    python scripts/db_snapshot.py --target supabase
    python scripts/db_snapshot.py --compare local supabase        # differences only
    python scripts/db_snapshot.py --compare local supabase --all  # every table

Read-only by construction: it opens a connection, counts rows and exits. The
output is JSON, so two snapshots can be diffed - and `--compare` exits non-zero
when the targets disagree, which is what makes it usable as a gate next to
`check_schema.py`.

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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = os.path.abspath(__file__)

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
    ap.add_argument("--target", choices=["local", "supabase"])
    ap.add_argument(
        "--compare",
        nargs=2,
        metavar=("LEFT", "RIGHT"),
        choices=["local", "supabase"],
        help="snapshot both targets and diff them",
    )
    ap.add_argument("--all", action="store_true", help="list equal tables too")
    ap.add_argument("--json", dest="as_json", action="store_true", help="raw JSON")
    ap.add_argument("--_probe", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args._probe:
        print(json.dumps(_snapshot()))
        return 0
    if args.compare:
        left, right = (snapshot(target) for target in args.compare)
        if args.as_json:
            print(json.dumps({"left": left, "right": right}, indent=2))
            return 0
        return 1 if compare(left, right, args.all) else 0
    if not args.target:
        ap.error("give --target or --compare")

    data = snapshot(args.target)
    if args.as_json:
        print(json.dumps(data, indent=2))
    else:
        _print_one(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
