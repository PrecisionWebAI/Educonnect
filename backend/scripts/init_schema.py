"""Create the schema from the models in one step, and stamp Alembic at head.

    python scripts/init_schema.py --check   # report, change nothing
    python scripts/init_schema.py           # create what is missing, stamp head
    python scripts/init_schema.py --force   # drop the model tables first (DESTRUCTIVE)

Why this exists instead of `alembic upgrade head`: the revision chain can no
longer build a database (revision 41 rebuilds from the live models, revisions
42-50 expect the old shape), which makes `alembic upgrade head` fail on any
database that is not already correct. `app/core/schema.py` explains it in full
and holds the implementation; this file is only the command line.

A database created here is stamped at head, so the ordinary
`alembic upgrade head` that runs inside `app/core/bootstrap.py` on every boot
applies later revisions normally instead of replaying history.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core import schema as schema_tools


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would happen and change nothing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="drop the model tables first (DESTRUCTIVE - dump the database first)",
    )
    args = parser.parse_args()

    schema_tools.load_models()
    schema_tools.quiet()

    expected = schema_tools.expected_tables()
    existing = schema_tools.existing_model_tables()

    print(f"target           {schema_tools.target_label()}")
    print(f"models           {len(expected)} tables")
    print(f"existing         {len(existing)} model tables")

    if existing and not args.force:
        print(
            "\nThis database already has the model tables. Nothing to do.\n"
            "Bring it up to date with `alembic upgrade head` (or `make db-local`),\n"
            "or recreate the tables with --force (destructive)."
        )
        return 0

    if args.check:
        print(f"\nwould create {len(expected)} tables and stamp head")
        return 0

    if existing:
        dropped = schema_tools.drop_model_tables()
        print(f"dropped          {dropped} tables (--force)")

    print("creating         schema from the models ...")
    created = schema_tools.create_missing()

    missing = sorted(expected - set(created))
    print(f"created          {len(created)} tables")
    if missing:
        print(f"MISSING          {missing}")
        return 1

    stamped = schema_tools.stamp_head()
    print(f"stamped          {stamped} (no revision was replayed)")
    print("\nOK: the schema is the one the models declare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
