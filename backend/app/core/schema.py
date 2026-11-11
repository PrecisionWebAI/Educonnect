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


def create_missing() -> list[str]:
    """`create_all` - only the tables that are missing, never a drop."""
    load_models()
    SQLModel.metadata.create_all(engine)
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
