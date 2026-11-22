"""M5 (`f5b6c7d8e9f0`): the school-wide subject and every legacy column go away.

The gate and the drops run here on an in-memory SQLite database in the **pre-M5 shape**.
Under test are the hard rules: nothing is dropped unless every operational row already
names its section subject / paper, the row counts do not move, and after a successful
run no legacy table or column is left.
"""

import importlib.util
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

REVISION = "f5b6c7d8e9f0"
PARENT = "f4a5b6c7d8e9"
PATH = Path("alembic/versions/f5b6c7d8e9f0_drop_global_subject.py")

sqlite3.register_adapter(UUID, lambda value: value.hex)

SCHEMA = """
CREATE TABLE subject (id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE chapterprogress (id TEXT PRIMARY KEY, chapter_id TEXT);
CREATE TABLE classroomsubject (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT, name TEXT
);
CREATE TABLE subjectteacher (
    id TEXT PRIMARY KEY, classroom_id TEXT, subject_id TEXT, classroom_subject_id TEXT,
    teacher_id TEXT, effective_to DATE
);
CREATE TABLE chapter (
    id TEXT PRIMARY KEY, class_id TEXT, subject_id TEXT, classroom_subject_id TEXT,
    status TEXT
);
CREATE TABLE timetableperiod (id TEXT PRIMARY KEY, subject_id TEXT, classroom_subject_id TEXT);
CREATE TABLE homeworkassignment (id TEXT PRIMARY KEY, subject_id TEXT, classroom_subject_id TEXT);
CREATE TABLE classlog (id TEXT PRIMARY KEY, subject_id TEXT, classroom_subject_id TEXT);
CREATE TABLE attendancerecord (
    id TEXT PRIMARY KEY, school_id TEXT, student_id TEXT, date DATE, subject_id TEXT,
    classroom_subject_id TEXT
);
CREATE TABLE exam_paper (
    id TEXT PRIMARY KEY, exam_id TEXT, class_id TEXT, subject_id TEXT, classroom_subject_id TEXT
);
CREATE TABLE marks (
    id TEXT PRIMARY KEY, exam_id TEXT, subject_id TEXT, exam_paper_id TEXT
);
CREATE TABLE paperdraft (
    id TEXT PRIMARY KEY, class_id TEXT, subject_id TEXT, section_id TEXT, classroom_subject_id TEXT
);
CREATE TABLE examsource (id TEXT PRIMARY KEY, class_id TEXT, subject_id TEXT);
"""

DROPPED_COLUMNS = {
    "classroomsubject": {"subject_id"},
    "subjectteacher": {"classroom_id", "subject_id"},
    "chapter": {"class_id", "subject_id"},
    "timetableperiod": {"subject_id"},
    "homeworkassignment": {"subject_id"},
    "classlog": {"subject_id"},
    "attendancerecord": {"subject_id"},
    "exam_paper": {"class_id", "subject_id"},
    "marks": {"exam_id", "subject_id"},
    "paperdraft": {"class_id", "subject_id", "section_id"},
    "examsource": {"class_id", "subject_id"},
}


def _module():
    spec = importlib.util.spec_from_file_location("m5_migration", PATH)
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

    school, room = _id(), _id()
    legacy = _insert(conn, "subject", name="Mathematics")
    cs = _insert(
        conn,
        "classroomsubject",
        school_id=school,
        classroom_id=room,
        subject_id=legacy,
        name="Mathematics",
    )
    _insert(conn, "chapterprogress", chapter_id=_id())
    _insert(
        conn,
        "subjectteacher",
        classroom_id=room,
        subject_id=legacy,
        classroom_subject_id=cs,
        teacher_id=_id(),
    )
    _insert(
        conn,
        "chapter",
        class_id=_id(),
        subject_id=legacy,
        classroom_subject_id=cs,
        status="Pending",
    )
    _insert(conn, "timetableperiod", subject_id=legacy, classroom_subject_id=cs)
    _insert(conn, "homeworkassignment", subject_id=legacy, classroom_subject_id=cs)
    _insert(conn, "classlog", subject_id=None, classroom_subject_id=cs)
    _insert(
        conn,
        "attendancerecord",
        school_id=school,
        student_id=_id(),
        date="2026-07-01",
        subject_id=None,
        classroom_subject_id=None,
    )
    exam = _id()
    paper = _insert(
        conn,
        "exam_paper",
        exam_id=exam,
        class_id=_id(),
        subject_id=legacy,
        classroom_subject_id=cs,
    )
    _insert(conn, "marks", exam_id=exam, subject_id=legacy, exam_paper_id=paper)
    _insert(
        conn,
        "paperdraft",
        class_id=_id(),
        subject_id=legacy,
        section_id=_id(),
        classroom_subject_id=cs,
    )
    _insert(conn, "examsource", class_id=_id(), subject_id=legacy)
    yield {
        "conn": conn,
        "room": room,
        "cs": cs,
        "legacy": legacy,
        "exam": exam,
        "paper": paper,
    }
    conn.close()


def _upgrade(conn, module=None):
    module = module or _module()
    with Operations.context(MigrationContext.configure(conn)):
        module.upgrade()
    return module


def _nothing_dropped(conn) -> bool:
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    return {"subject", "chapterprogress"} <= tables and "subject_id" in {
        column["name"] for column in inspector.get_columns("timetableperiod")
    }


def test_m5_is_the_single_head_with_the_expected_parent():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == [REVISION]
    assert script.get_revision(REVISION).down_revision == PARENT


def test_the_downgrade_says_it_cannot_be_reversed():
    with pytest.raises(RuntimeError, match="cannot be reversed"):
        _module().downgrade()


def test_a_clean_database_loses_every_legacy_table_and_column_and_no_rows(world):
    conn = world["conn"]
    counts = {
        table: _count(conn, f"SELECT count(*) FROM {table}")
        for table in (
            "classroomsubject",
            "chapter",
            "exam_paper",
            "marks",
            "paperdraft",
        )
    }
    _upgrade(conn)

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    assert "subject" not in tables and "chapterprogress" not in tables
    for table, columns in DROPPED_COLUMNS.items():
        present = {column["name"] for column in inspector.get_columns(table)}
        assert not columns & present, f"{table} still has {columns & present}"
        assert "classroom_subject_id" in present or table in (
            "marks",
            "examsource",
            "classroomsubject",
        )
    for table, count in counts.items():
        assert _count(conn, f"SELECT count(*) FROM {table}") == count
    assert "exam_paper_id" in {c["name"] for c in inspector.get_columns("marks")}


def test_the_day_level_attendance_index_no_longer_mentions_the_subject(world):
    conn = world["conn"]
    _upgrade(conn)
    sql = conn.execute(
        sa.text(
            "SELECT sql FROM sqlite_master WHERE name = 'uq_attendancerecord_school_student_date_day'"
        )
    ).scalar_one()
    assert "classroom_subject_id IS NULL" in sql and "subject_id IS NULL AND" not in sql
    # Two day-level rows for one child and day are still refused.
    student = _id()
    _insert(
        conn,
        "attendancerecord",
        school_id=_id(),
        student_id=student,
        date="2026-08-01",
        classroom_subject_id=None,
    )
    school = conn.execute(
        sa.text("SELECT school_id FROM attendancerecord WHERE student_id = :s"),
        {"s": student},
    ).scalar_one()
    with pytest.raises(sa.exc.IntegrityError):
        _insert(
            conn,
            "attendancerecord",
            school_id=school,
            student_id=student,
            date="2026-08-01",
            classroom_subject_id=None,
        )


@pytest.mark.parametrize(
    ("table", "values", "message"),
    [
        (
            "timetableperiod",
            {"subject_id": None, "classroom_subject_id": None},
            "timetableperiod row",
        ),
        (
            "homeworkassignment",
            {"subject_id": None, "classroom_subject_id": None},
            "homeworkassignment row",
        ),
        (
            "attendancerecord",
            {
                "school_id": "s",
                "student_id": "x",
                "date": "2026-09-01",
                "subject_id": "legacy",
                "classroom_subject_id": None,
            },
            "attendancerecord row",
        ),
        (
            "classlog",
            {"subject_id": "legacy", "classroom_subject_id": None},
            "classlog row",
        ),
        (
            "chapter",
            {
                "class_id": "c",
                "subject_id": "s",
                "classroom_subject_id": "cs",
                "status": None,
            },
            "chapter row",
        ),
        (
            "exam_paper",
            {"exam_id": "e", "classroom_subject_id": None},
            "exam_paper row",
        ),
        (
            "marks",
            {"exam_id": "e", "exam_paper_id": None},
            "with no paper",
        ),
        (
            "subjectteacher",
            {"classroom_id": "r", "classroom_subject_id": None, "teacher_id": "t"},
            "no section subject",
        ),
        (
            "paperdraft",
            {"subject_id": "s", "section_id": "x", "classroom_subject_id": None},
            "paperdraft row",
        ),
    ],
)
def test_a_row_that_would_lose_information_aborts_before_anything_is_dropped(
    world, table, values, message
):
    conn = world["conn"]
    values = {k: (world["legacy"] if v == "legacy" else v) for k, v in values.items()}
    if values.get("classroom_subject_id") == "cs":
        values["classroom_subject_id"] = world["cs"]
    _insert(conn, table, **values)
    module = _module()
    with pytest.raises(module.MigrationAbort, match=message):
        _upgrade(conn, module)
    assert _nothing_dropped(conn)


def test_a_mark_whose_exam_differs_from_its_paper_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "marks",
        exam_id=_id(),
        subject_id=world["legacy"],
        exam_paper_id=world["paper"],
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="exam differs"):
        _upgrade(conn, module)
    assert _nothing_dropped(conn)


def test_an_assignment_in_another_section_than_its_subject_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "subjectteacher",
        classroom_id=_id(),
        subject_id=world["legacy"],
        classroom_subject_id=world["cs"],
        teacher_id=_id(),
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="section differs"):
        _upgrade(conn, module)
    assert _nothing_dropped(conn)
