"""`add_missing_columns` - the boot-stamp gap, closed and proved.

The gap: `create_missing()` builds missing **tables** and `stamp_head()` then marks the
schema current, so a revision that only adds a *column* to an existing table never runs
on a database created that way. Phases 3, 5 and 6 each recorded tripping over it; this
module is the fix and these tests are what keep it a fix.

Two claims: a missing column is added **without touching the rows already there**, and
running it twice is a no-op.
"""

from sqlalchemy import Column, String, create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.core import schema


def _engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_a_missing_column_is_added_and_the_rows_survive():
    """An older table shape gains the model's columns; its data is untouched."""
    engine = _engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            'CREATE TABLE "employee" (id TEXT PRIMARY KEY, employee_code TEXT)'
        )
        conn.exec_driver_sql(
            "INSERT INTO \"employee\" (id, employee_code) VALUES ('1', 'EMP-0001')"
        )

    added = schema.add_missing_columns(engine)

    names = {column["name"] for column in inspect(engine).get_columns("employee")}
    assert {"department", "user_id", "joining_date"} <= names
    assert added["employee"], "the caller is told what was added"
    with engine.connect() as conn:
        kept = conn.exec_driver_sql('SELECT employee_code FROM "employee"').scalar_one()
    assert kept == "EMP-0001"


def test_running_it_twice_adds_nothing_the_second_time():
    engine = _engine()
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE "employee" (id TEXT PRIMARY KEY)')

    assert schema.add_missing_columns(engine)["employee"]
    assert schema.add_missing_columns(engine) == {}


def test_a_table_the_database_does_not_have_is_left_to_create_all():
    """No table, no `ALTER`: `create_all` builds the whole thing, columns included."""
    engine = _engine()
    assert schema.add_missing_columns(engine) == {}


def test_a_constant_default_makes_a_not_null_column_addable():
    """`NOT NULL DEFAULT 'Pending'` is safe on a full table; a bare NOT NULL is not."""
    engine = _engine()
    column = Column("status", String, nullable=False, default="Pending")
    column.name = "status"  # unattached column: SQLAlchemy needs the name set
    statement = schema._add_column_ddl("leaverequest", column, engine)

    assert "NOT NULL DEFAULT 'Pending'" in statement


def test_a_callable_default_is_not_written_into_ddl():
    """`utcnow` is Python, not a server default - the column lands nullable instead."""
    engine = _engine()
    column = Column("created_at", String, nullable=False, default=lambda: "x")
    column.name = "created_at"

    statement = schema._add_column_ddl("employee", column, engine)
    assert "NOT NULL" not in statement
