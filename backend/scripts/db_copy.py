"""Copy rows from one database to another - only when they really differ.

    python scripts/db_copy.py --dry-run     # counts only, env -> supabase
    python scripts/db_copy.py --yes         # write for real

Rows only; the schema must already match (`check_schema.py`). Refuses when both
DSNs name the same host+database, which is the normal case now: `db-copy` is not
a Make target any more, it is kept for a branch/snapshot database.

The target's model tables are truncated and refilled in one transaction, in
parent-first order, so an interrupted run leaves the target untouched.
"""

import argparse
import os
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import MetaData, create_engine, text

from app.core.config import settings

BATCH = 1000


def _quote(name: str) -> str:
    """A table name, quoted, for the one statement that cannot be parameterised."""
    return '"' + name.replace('"', '""') + '"'


def _dsn(which: str) -> str:
    """The DSN for `env` (backend/.env) or `supabase` (`SUPABASE_DB_URL`)."""
    if which == "env":
        return settings.DATABASE_URL
    if not settings.SUPABASE_DB_URL:
        raise SystemExit(
            "SUPABASE_DB_URL is empty. Put the Supabase connection string in\n"
            "backend/.env (see backend/.env-example) and run this again."
        )
    return settings.SUPABASE_DB_URL


def _same_database(left: str, right: str) -> bool:
    """Do two DSNs name the same host and database? (Credentials ignored.)"""
    a, b = urlsplit(left), urlsplit(right)
    return (a.hostname, (a.path or "").rstrip("/")) == (
        b.hostname,
        (b.path or "").rstrip("/"),
    )


def _engine(dsn: str):
    """An engine with the same connection settings the app uses."""
    args: dict[str, object] = {"options": f"-csearch_path={settings.DB_SCHEMA},public"}
    if "sslmode=" in dsn:
        # Managed Postgres terminates TLS with its own CA; repeat the DSN's mode.
        mode = dsn.split("sslmode=")[1].split("&")[0]
        args["sslmode"] = settings.DB_SSLMODE or mode
    return create_engine(dsn, pool_pre_ping=True, connect_args=args)


def _counts(conn, tables) -> dict[str, int]:
    return {
        table.name: conn.execute(
            text(f"select count(*) from {_quote(table.name)}")
        ).scalar()
        for table in tables
    }

def _show(label: str, counts: dict[str, int], tables) -> None:
    print(f"{label}: {sum(counts.values())} rows in {len(tables)} tables")
    for table in tables:
        if counts[table.name]:
            print(f"  {table.name:34s}{counts[table.name]}")


def copy(src, dst, tables, batch: int = BATCH) -> dict[str, int]:
    """Truncate the target and refill it from the source, in one transaction."""
    copied: dict[str, int] = {}
    with src.connect() as source, dst.begin() as target:
        target.execute(
            text(
                "TRUNCATE "
                + ", ".join(_quote(table.name) for table in tables)
                + " RESTART IDENTITY CASCADE"
            )
        )
        for table in tables:
            rows = [dict(row._mapping) for row in source.execute(table.select())]
            for start in range(0, len(rows), batch):
                target.execute(table.insert(), rows[start : start + batch])
            copied[table.name] = len(rows)
            if rows:
                print(f"  {table.name:34s}{len(rows)}")
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=["env", "supabase"], default="env")
    ap.add_argument("--target", choices=["env", "supabase"], default="supabase")
    ap.add_argument(
        "--yes",
        action="store_true",
        help="write for real; without it the run stops after the counts",
    )
    ap.add_argument("--batch", type=int, default=BATCH, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.source == args.target:
        raise SystemExit("--source and --target must be different databases")

    source_dsn, target_dsn = _dsn(args.source), _dsn(args.target)
    if _same_database(source_dsn, target_dsn):
        # The normal case now: both names point at the one Supabase project.
        parts = urlsplit(source_dsn)
        raise SystemExit(
            f"--source and --target are the same database "
            f"({parts.hostname}{(parts.path or '').rstrip('/')}).\n"
            "There is nothing to copy, and truncating the target would delete the\n"
            "rows it was going to read. Nothing was changed."
        )

    from app.core import schema as schema_tools

    schema_tools.load_models()
    schema_tools.quiet()
    expected = schema_tools.expected_tables()

    src = _engine(source_dsn)
    dst = _engine(target_dsn)

    meta = MetaData()
    meta.reflect(bind=src)
    wanted = set(expected)
    tables = [table for table in meta.sorted_tables if table.name in wanted]
    missing = sorted(wanted - {table.name for table in tables})
    if missing:
        raise SystemExit(
            "The source is missing tables the models declare: "
            + ", ".join(missing)
            + "\nBring it up to head first (`make db-sync`)."
        )

    with src.connect() as conn:
        before = _counts(conn, tables)
    with dst.connect() as conn:
        current = _counts(conn, tables)
    _show(f"source {args.source}", before, tables)
    _show(f"target {args.target} (before)", current, tables)

    if not args.yes:
        print(
            "\ndry run - nothing written. "
            "Re-run with --yes to replace the target's rows with the source's."
        )
        return 0

    started = time.monotonic()
    copied = copy(src, dst, tables, args.batch)
    with dst.connect() as conn:
        after = _counts(conn, tables)

    elapsed = time.monotonic() - started
    print(f"\ncopied {sum(copied.values())} rows in {elapsed:.1f}s")

    problems = {
        table.name: (copied[table.name], after[table.name])
        for table in tables
        if copied[table.name] != after[table.name]
    }
    if problems:
        for name, (read, written) in problems.items():
            print(f"!! {name}: read {read}, wrote {written}")
        return 1
    if after != before:
        print("!! the target's counts differ from the source's")
        return 1
    print(f"target {args.target} now matches source {args.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
