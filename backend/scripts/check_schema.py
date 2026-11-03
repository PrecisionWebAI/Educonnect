"""Does the database still match the code? - a one-command schema audit.

Why this exists
---------------
The tables are created by Alembic, but the *code* reads them through SQLModel.
When the two drift - a migration that never ran, a migration that ran from a
branch that was later abandoned, a column renamed on one side only - there is no
clear error at startup. The symptom is a 500 on the first screen that touches the
table, which then renders as an empty list ("no applications yet").

This compares `SQLModel.metadata` (what the code expects) with
`information_schema` (what the database has) and prints the differences that
matter:

    missing tables / missing columns  -> the code will fail on a query
    extra columns                     -> the database is ahead of the code

Usage (inside the API container, or a `uv` shell):

    python scripts/check_schema.py        # exit 1 when the two disagree
"""

import importlib
import logging
import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import SQLModel  # noqa: E402

from app.core.db import engine  # noqa: E402

# Importing the app turns on SQLAlchemy's statement log; the audit's own lines are
# what matters here, so the engine's chatter is silenced.
def _quiet() -> None:
    """Silence SQLAlchemy's statement log.

    The engine is created with `echo=True`, and SQLAlchemy re-applies `INFO` to its
    logger on every statement, so the flag (not just the level) has to go.
    """
    engine.echo = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)


_quiet()

#: Every domain that owns tables - the same list `alembic/env.py` keeps. Importing
#: all of them matters: `SQLModel.metadata` only holds the tables whose module has
#: been imported.
MODEL_MODULES = (
    "academics",
    "admissions",
    "attendance",
    "auth",
    "chat",
    "exams",
    "finance",
    "hiring",
    "homework",
    "operations",
    "salary",
    "staff",
    "students",
    "teachers",
    "timetable",
    "users",
)


def _load_models() -> None:
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")


def _database_columns() -> dict[str, set[str]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )
        ).fetchall()
    columns: dict[str, set[str]] = {}
    for table, column in rows:
        columns.setdefault(table, set()).add(column)
    return columns


def _revisions() -> str:
    """`current=... head=...` - the other half of the same failure mode."""
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script = ScriptDirectory.from_config(Config(os.path.join(root, "alembic.ini")))
        # Alembic's Config re-applies the ini's logger levels, so the engine is
        # quietened again after it.
        _quiet()
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
        return f"current={current} head={','.join(script.get_heads())}"
    except Exception as error:  # a missing alembic.ini must not hide the audit
        return f"(not checked: {error})"


def main() -> int:
    _load_models()
    # Importing the domains creates the engine, which switches its logger back on.
    _quiet()
    expected = {
        table.name: {column.name for column in table.columns}
        for table in SQLModel.metadata.tables.values()
    }
    found = _database_columns()

    missing_tables = sorted(name for name in expected if name not in found)
    missing_columns = sorted(
        (table, column)
        for table, columns in expected.items()
        if table in found
        for column in columns - found[table]
    )
    extra_columns = sorted(
        (table, column)
        for table, columns in found.items()
        if table in expected
        for column in columns - expected[table]
    )

    print(f"alembic          {_revisions()}")
    print(f"tables           {len(expected)} expected, {len(found)} in the database")
    print(f"missing tables   {missing_tables or 'none'}")
    print(f"missing columns  {missing_columns or 'none'}")
    print(f"extra columns    {extra_columns or 'none'}")

    if missing_tables or missing_columns or extra_columns:
        print("\nDRIFT: code and database disagree - run `alembic upgrade head`.")
        return 1
    print("\nOK: the database matches the code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
