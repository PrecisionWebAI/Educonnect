"""M4 (`f4a5b6c7d8e9`): teachers' subjects become plain text; hiring stops pointing at one.

The data steps run here on an in-memory SQLite database in the **pre-M4 shape**
(`teachersubject` rows, `pipeline_hiring_table.subject_id`). Under test are the hard rules:
every teacher subject lands in `subject_tags`, nothing else moves (`classroomsubject`,
hiring and employee counts), a list that cannot fit aborts before anything is dropped,
and the suggestion list is seeded per school.
"""

import importlib.util
import json
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

REVISION = "f4a5b6c7d8e9"
PARENT = "f3e4a5b6c7d8"
PATH = Path("alembic/versions/f4a5b6c7d8e9_subject_people_cleanup.py")

sqlite3.register_adapter(UUID, lambda value: value.hex)

SCHEMA = """
CREATE TABLE subject (id TEXT PRIMARY KEY, school_id TEXT, name TEXT);
CREATE TABLE employee (id TEXT PRIMARY KEY, school_id TEXT, employee_code TEXT);
CREATE TABLE teachersubject (
    id TEXT PRIMARY KEY, school_id TEXT, teacher_id TEXT, subject_id TEXT
);
CREATE TABLE pipeline_hiring_table (
    id TEXT PRIMARY KEY, school_id TEXT, subject_id TEXT, subject_name TEXT
);
CREATE TABLE school_setting (
    id TEXT PRIMARY KEY, school_id TEXT, key TEXT, value TEXT, updated_at DATETIME
);
CREATE TABLE classroomsubject (id TEXT PRIMARY KEY, name TEXT);
"""


def _module():
    spec = importlib.util.spec_from_file_location("m4_migration", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _id() -> str:
    return uuid4().hex


def _insert(conn, table: str, **values) -> str:
    values.setdefault("id", _id())
    columns = ", ".join(values)
    marks = ", ".join(f":{key}" for key in values)
    conn.execute(sa.text(f"INSERT INTO {table} ({columns}) VALUES ({marks})"), values)
    return values["id"]


def _count(conn, sql: str) -> int:
    return int(conn.execute(sa.text(sql)).scalar_one())


@pytest.fixture
def world():
    engine = sa.create_engine("sqlite://")
    conn = engine.connect()
    for statement in SCHEMA.split(";"):
        if statement.strip():
            conn.execute(sa.text(statement))
    school, other = _id(), _id()
    english = _insert(conn, "subject", school_id=school, name="English")
    maths = _insert(conn, "subject", school_id=school, name="Maths")
    science = _insert(conn, "subject", school_id=other, name="Science")
    meera = _insert(conn, "employee", school_id=school, employee_code="E1")
    bose = _insert(conn, "employee", school_id=school, employee_code="E2")
    nobody = _insert(conn, "employee", school_id=school, employee_code="E3")
    for teacher, subject in ((meera, maths), (meera, english), (bose, english)):
        _insert(
            conn,
            "teachersubject",
            school_id=school,
            teacher_id=teacher,
            subject_id=subject,
        )
    _insert(conn, "classroomsubject", name="Maths")
    candidate = _insert(
        conn,
        "pipeline_hiring_table",
        school_id=school,
        subject_id=maths,
        subject_name=None,
    )
    typed = _insert(
        conn,
        "pipeline_hiring_table",
        school_id=school,
        subject_id=english,
        subject_name="English (typed)",
    )
    yield {
        "conn": conn,
        "school": school,
        "other": other,
        "meera": meera,
        "bose": bose,
        "nobody": nobody,
        "candidate": candidate,
        "typed": typed,
        "science": science,
    }
    conn.close()


def _upgrade(conn, module=None):
    module = module or _module()
    with Operations.context(MigrationContext.configure(conn)):
        module.upgrade()
    return module


def test_m4_is_the_single_head_with_the_expected_parent():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == [REVISION]
    assert script.get_revision(REVISION).down_revision == PARENT
    module = _module()
    assert callable(module.upgrade) and callable(module.downgrade)


def test_every_teacher_subject_reaches_the_text_alphabetically(world):
    conn = world["conn"]
    _upgrade(conn)
    tags = dict(conn.execute(sa.text("SELECT id, subject_tags FROM employee")).all())
    assert tags[world["meera"]] == "English, Maths"
    assert tags[world["bose"]] == "English"
    assert tags[world["nobody"]] is None, "a teacher with no subjects keeps no tags"


def test_nothing_else_moves_and_the_old_tables_are_gone(world):
    conn = world["conn"]
    subjects, hiring, employees = (
        _count(conn, "SELECT count(*) FROM classroomsubject"),
        _count(conn, "SELECT count(*) FROM pipeline_hiring_table"),
        _count(conn, "SELECT count(*) FROM employee"),
    )
    _upgrade(conn)
    assert _count(conn, "SELECT count(*) FROM classroomsubject") == subjects
    assert _count(conn, "SELECT count(*) FROM pipeline_hiring_table") == hiring
    assert _count(conn, "SELECT count(*) FROM employee") == employees
    inspector = sa.inspect(conn)
    assert "teachersubject" not in inspector.get_table_names()
    assert "subject_id" not in {
        c["name"] for c in inspector.get_columns("pipeline_hiring_table")
    }


def test_hiring_keeps_what_was_typed_and_fills_only_the_empty_name(world):
    conn = world["conn"]
    _upgrade(conn)
    names = dict(
        conn.execute(
            sa.text("SELECT id, subject_name FROM pipeline_hiring_table")
        ).all()
    )
    assert names[world["candidate"]] == "Maths", "filled from the subject it pointed at"
    assert names[world["typed"]] == "English (typed)", (
        "the typed snapshot is never overwritten"
    )


def test_each_school_gets_its_own_suggestion_list_once(world):
    conn = world["conn"]
    # A school that already chose its list is left alone.
    _insert(
        conn,
        "school_setting",
        school_id=world["other"],
        key="hiring.subject_suggestions",
        value=json.dumps(["Chosen"]),
        updated_at="2026-01-01 00:00:00",
    )
    _upgrade(conn)
    lists = {
        row[0]: json.loads(row[1])
        for row in conn.execute(
            sa.text(
                "SELECT school_id, value FROM school_setting WHERE key = 'hiring.subject_suggestions'"
            )
        ).all()
    }
    assert lists[world["school"]] == ["English", "Maths"]
    assert lists[world["other"]] == ["Chosen"]


def test_a_list_that_cannot_fit_aborts_before_anything_is_dropped(world):
    conn = world["conn"]
    for number in range(40):
        long_name = f"Subject number {number} with a rather long descriptive name"
        subject = _insert(conn, "subject", school_id=world["school"], name=long_name)
        _insert(
            conn,
            "teachersubject",
            school_id=world["school"],
            teacher_id=world["bose"],
            subject_id=subject,
        )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="500 characters"):
        _upgrade(conn, module)
    assert "teachersubject" in sa.inspect(conn).get_table_names(), "nothing was dropped"
