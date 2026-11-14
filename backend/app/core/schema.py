"""The schema, from the models - the one definition a database is built from.

Why this is not "just run the migrations": the chain cannot build a database any
more. Revision `f8d9e0f1a2b3_uuid_everywhere` rebuilds every table from
`SQLModel.metadata` - the models **as they are today** - while revisions 42-50
were written against the shape of 2026-11-02. Replaying the chain, from base or
from `d6f3e8b2c1a4`, stops at `f9e0f1a2b3c4_school_scoped_class_catalog` with
`column c.name does not exist`. (Both failures are one command away:
`alembic upgrade head` on an empty database.)

So the models are the source of truth, and this module is the single
implementation of "make a database match them":

* `create_missing()` - `create_all`, for a database that has none of the tables.
* `stamp_head()` - tell Alembic the schema is current, so later revisions apply
  normally instead of trying to replay history.
* `current_revision()` / `head_revision()` - the two numbers the parity checks
  compare.

`scripts/init_schema.py` (a CLI), `scripts/db_sync.py` (the one database) and the
CI drift job all go through this file, so there is exactly one behaviour to test.
"""

import importlib
import logging
from urllib.parse import urlsplit

from alembic.config import Config
from sqlalchemy import inspect
from sqlmodel import SQLModel

from alembic import command
from app.core.config import BASE_DIR, settings
from app.core.db import engine

#: Every domain that owns tables - the same list `alembic/env.py` and
#: `scripts/check_schema.py` keep. `SQLModel.metadata` only holds the tables whose
#: module has been imported, so all of them must be.
MODEL_MODULES = (
    "academic.classroom.academics",
    "academic.classroom.attendance",
    "academic.classroom.exams",
    "academic.classroom.homework",
    "academic.classroom.students",
    "academic.classroom.timetable",
    "admin.platform",
    "admin.settings",
    "admin.users",
    "auth",
    "finance.fees",
    "insights.reports",
    "main.chat",
    "main.copilot",
    "main.notifications",
    "operations.admission",
    "operations.fees_structure",
    "operations.salary",
    "operations.staff_hiring",
    "people.staff",
    "people.teachers",
    "people.teachers.profile",
    "people.teachers.staff_attendance",
    "people.teachers.workload",
    "services.leave",
    "services.library",
    "services.meetings",
    "services.tickets",
    "services.transport",
)


def load_models() -> None:
    """Import every model module so `SQLModel.metadata` is complete."""
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")


def quiet() -> None:
    """Importing the domains turns the statement log back on; turn it off."""
    engine.echo = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)


def expected_tables() -> set[str]:
    """Every table the models declare."""
    load_models()
    return set(SQLModel.metadata.tables)


def existing_model_tables() -> list[str]:
    """The model tables this database already has."""
    load_models()
    present = set(inspect(engine).get_table_names())
    return sorted(name for name in SQLModel.metadata.tables if name in present)


def table_count() -> int:
    """Tables in the configured schema, model tables or not."""
    return len(inspect(engine).get_table_names())


def add_missing_columns(bind=None) -> dict[str, list[str]]:
    """`ALTER TABLE … ADD COLUMN` for every model column this database lacks.

    The gap this closes: `create_missing()` builds missing **tables**, then
    `stamp_head()` marks the schema current - so a revision that only adds a *column*
    to an existing table never runs on a database built that way (the operational note
    in `backend/phase.md` records three phases tripping over it). Reading the models
    and adding what is absent fixes it for every past and future column at once.

    A column the model declares NOT NULL is added **nullable** unless the model also
    gives a constant default: `ALTER TABLE … ADD COLUMN x text NOT NULL` fails on any
    table that already has rows, and a boot that refuses to start is worse than a
    column that is looser than the model until the next migration tightens it. The
    returned `{table: [columns]}` is what the caller prints, so nothing is added
    silently.

    `bind` is injectable so this can be tested against a throwaway engine.
    """
    load_models()
    target = bind if bind is not None else engine
    inspector = inspect(target)
    present_tables = set(inspector.get_table_names())
    added: dict[str, list[str]] = {}

    for name, table in SQLModel.metadata.tables.items():
        if name not in present_tables:
            continue  # `create_all` owns a missing table
        present = {column["name"] for column in inspector.get_columns(name)}
        for column in table.columns:
            if column.name in present:
                continue
            with target.begin() as conn:
                conn.exec_driver_sql(_add_column_ddl(table.name, column, target))
            added.setdefault(name, []).append(column.name)

    if bind is None:
        quiet()
    return added


def _constant_default(column) -> str | None:
    """The SQL literal for a column's default, when it has a simple constant one.

    A callable default (`utcnow`, `uuid4`) cannot be written into DDL - it is Python,
    not a server default - so those columns get no default and land nullable.
    """
    default = column.default
    if default is None or getattr(default, "is_callable", False):
        return None
    value = getattr(default, "arg", None)
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _add_column_ddl(table_name: str, column, target) -> str:
    """`ALTER TABLE … ADD COLUMN …` for one model column, in the target's dialect."""
    type_sql = column.type.compile(dialect=target.dialect)
    literal = _constant_default(column)
    statement = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {type_sql}'
    if not column.nullable and literal is not None:
        statement += f" NOT NULL DEFAULT {literal}"
    return statement


def create_missing() -> list[str]:
    """`create_all` - only the tables that are missing, never a drop.

    Followed by `add_missing_columns()`, so a database that already had the tables
    still ends up with the columns the models declare (the boot-stamp gap).
    """
    load_models()
    SQLModel.metadata.create_all(engine)
    add_missing_columns(engine)
    quiet()
    return existing_model_tables()


def drop_model_tables() -> int:
    """Drop every model table (destructive). Returns how many existed first."""
    names = existing_model_tables()
    if names:
        with engine.begin() as conn:
            quoted = ", ".join(f'"{name}"' for name in names)
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {quoted} CASCADE")
    return len(names)


def row_counts() -> dict[str, int]:
    """`{table: rows}` for every model table present - how a wipe proves itself."""
    counts: dict[str, int] = {}
    names = existing_model_tables()
    if not names:
        return counts
    with engine.connect() as conn:
        for name in names:
            rows = conn.exec_driver_sql(f'SELECT count(*) FROM "{name}"').scalar_one()
            counts[name] = int(rows)
    return counts


def truncate_model_tables() -> int:
    """Delete every row, keep every table (destructive). Returns tables cleared.

    One `TRUNCATE ... CASCADE`, so foreign keys never decide the order and no
    self-reference can block it. The tables and `alembic_version` stay: the schema
    is still "current", so the next boot only has to re-seed instead of rebuilding.
    """
    names = existing_model_tables()
    if names:
        quoted = ", ".join(f'"{name}"' for name in names)
        with engine.begin() as conn:
            conn.exec_driver_sql(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
    quiet()
    return len(names)


def backup_rows(path: str) -> int:
    """Write every row of every model table to `path` as JSON; returns tables saved.

    Plain JSON rather than `pg_dump` (the image ships no postgres client): enough
    to put a demo roll back, and readable when it is the only copy left. Values
    that JSON has no type for (UUID, date, Decimal) go out as their string form.
    """
    import json

    payload: dict[str, list[dict]] = {}
    names = existing_model_tables()
    with engine.connect() as conn:
        for name in names:
            rows = conn.exec_driver_sql(f'SELECT * FROM "{name}"').mappings().all()
            payload[name] = [dict(row) for row in rows]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, default=str, indent=1)
    quiet()
    return len(names)


def _alembic_config() -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "alembic"))
    return config


def head_revision() -> str:
    """The newest revision in the chain."""
    from alembic.script import ScriptDirectory

    heads = ScriptDirectory.from_config(_alembic_config()).get_heads()
    return heads[0] if heads else ""


def current_revision() -> str | None:
    """What this database's `alembic_version` says, or None when it has none."""
    from alembic.runtime.migration import MigrationContext

    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def stamp_head() -> str:
    """Mark the schema as current without replaying a single revision."""
    command.stamp(_alembic_config(), "head")
    quiet()
    return head_revision()


def target_label() -> str:
    """`host:port/db` of what we are connected to - **never** the password.

    The DSN decides the answer, not the configured `DB_NAME`: one laptop, the
    container and the deployment can all be pointed somewhere by
    `DATABASE_URL_OVERRIDE`, so every tool prints where it actually is.
    """
    parts = urlsplit(settings.DATABASE_URL)
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    database = (parts.path or "/?").lstrip("/") or "?"
    kind = "managed" if settings.is_managed_db else "self-run"
    return f"{host}{port}/{database} ({kind})"
