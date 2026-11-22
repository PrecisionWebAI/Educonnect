"""M2 (`f2d3e4a5b6c7`): chapters and class operations move onto classroom subjects.

The migration's data steps run here for real, on an in-memory SQLite database built in
the **pre-M2 shape** (class-level chapters, `chapterprogress`, operational rows that only
name the school-wide subject). PostgreSQL-only DDL (NOT NULL, FKs, unique constraints)
is skipped on SQLite by the migration itself.

The rules under test are the plan's hard rules: no `classroomsubject` row is created,
an unmappable row aborts the migration, and the before/after counts must add up.
"""

import importlib.util
import sqlite3
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

REVISION = "f2d3e4a5b6c7"
PARENT = "f1c2d3e4a5b6"
PATH = Path("alembic/versions/f2d3e4a5b6c7_subject_curriculum_repoint.py")

# The migration binds uuid4() values; SQLite stores `sa.Uuid` as 32-char hex.
sqlite3.register_adapter(UUID, lambda value: value.hex)


def _module():
    spec = importlib.util.spec_from_file_location("m2_migration", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _id() -> str:
    return uuid4().hex


PRE_M2_SCHEMA = """
CREATE TABLE academic_year (id TEXT PRIMARY KEY, school_id TEXT, is_current BOOLEAN);
CREATE TABLE classroom (id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, section_id TEXT);
CREATE TABLE classroomsubject (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT,
    academic_year_id TEXT, name TEXT NOT NULL, status TEXT
);
CREATE TABLE subjectteacher (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT,
    classroom_subject_id TEXT, academic_year_id TEXT, teacher_id TEXT,
    effective_from DATE, effective_to DATE
);
CREATE TABLE chapter (
    id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, subject_id TEXT,
    academic_year_id TEXT, sequence INTEGER, name TEXT, planned_date DATE
);
CREATE TABLE chapterprogress (
    id TEXT PRIMARY KEY, school_id TEXT, chapter_id TEXT, classroom_id TEXT,
    status TEXT, completed_on DATE, completed_by_employee_id TEXT, updated_at DATETIME
);
CREATE TABLE timetableperiod (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT,
    academic_year_id TEXT
);
CREATE TABLE homeworkassignment (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT
);
CREATE TABLE attendancerecord (
    id TEXT PRIMARY KEY, school_id TEXT, student_id TEXT, date DATE,
    classroom_id TEXT, subject_id TEXT
);
CREATE UNIQUE INDEX uq_attendancerecord_school_student_date_day
    ON attendancerecord (school_id, student_id, date) WHERE subject_id IS NULL;
CREATE TABLE classlog (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT
);
"""


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
    """Two schools. School A: Class 9 with sections A, B (Maths) and C (no Maths)."""
    engine = sa.create_engine("sqlite://")
    conn = engine.connect()
    for statement in PRE_M2_SCHEMA.split(";"):
        if statement.strip():
            conn.execute(sa.text(statement))

    school, other_school = _id(), _id()
    year = _insert(conn, "academic_year", school_id=school, is_current=True)
    other_year = _insert(conn, "academic_year", school_id=other_school, is_current=True)
    class_9, maths, english = _id(), _id(), _id()
    room_a = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="a"
    )
    room_b = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="b"
    )
    room_c = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="c"
    )
    other_room = _insert(
        conn, "classroom", school_id=other_school, class_id=class_9, section_id="a"
    )

    def subject(room, subject_id, name, school_id=school, year_id=year):
        return _insert(
            conn,
            "classroomsubject",
            school_id=school_id,
            classroom_id=room,
            subject_id=subject_id,
            academic_year_id=year_id,
            name=name,
            status="Active",
        )

    maths_a = subject(room_a, maths, "Mathematics")
    maths_b = subject(room_b, maths, "Mathematics")
    english_c = subject(room_c, english, "English")
    # Another school with the same class and subject ids must never be a target.
    other_maths = subject(other_room, maths, "Mathematics", other_school, other_year)

    ch1 = _insert(
        conn,
        "chapter",
        school_id=school,
        class_id=class_9,
        subject_id=maths,
        academic_year_id=year,
        sequence=1,
        name="Number Systems",
        planned_date=date(2026, 5, 1),
    )
    ch2 = _insert(
        conn,
        "chapter",
        school_id=school,
        class_id=class_9,
        subject_id=maths,
        academic_year_id=year,
        sequence=2,
        name="Polynomials",
        planned_date=None,
    )
    employee = _id()
    _insert(
        conn,
        "chapterprogress",
        school_id=school,
        chapter_id=ch1,
        classroom_id=room_a,
        status="Completed",
        completed_on=date(2026, 5, 2),
        completed_by_employee_id=employee,
        updated_at="2026-05-02 00:00:00",
    )
    _insert(
        conn,
        "chapterprogress",
        school_id=school,
        chapter_id=ch2,
        classroom_id=room_b,
        status="In progress",
        completed_on=None,
        completed_by_employee_id=None,
        updated_at="2026-05-02 00:00:00",
    )
    _insert(
        conn,
        "subjectteacher",
        school_id=school,
        classroom_id=room_a,
        subject_id=maths,
        classroom_subject_id=None,
        academic_year_id=None,
        teacher_id=employee,
        effective_from=date(2026, 6, 1),
    )
    _insert(
        conn,
        "timetableperiod",
        school_id=school,
        classroom_id=room_b,
        subject_id=maths,
        academic_year_id=year,
    )
    _insert(
        conn,
        "homeworkassignment",
        school_id=school,
        classroom_id=room_a,
        subject_id=maths,
    )
    _insert(
        conn,
        "attendancerecord",
        school_id=school,
        student_id=_id(),
        date=date(2026, 7, 1),
        classroom_id=room_a,
        subject_id=maths,
    )
    _insert(
        conn,
        "attendancerecord",
        school_id=school,
        student_id=_id(),
        date=date(2026, 7, 1),
        classroom_id=room_a,
        subject_id=None,
    )
    _insert(conn, "classlog", school_id=school, classroom_id=room_b, subject_id=maths)
    _insert(conn, "classlog", school_id=school, classroom_id=room_b, subject_id=None)

    yield {
        "conn": conn,
        "school": school,
        "year": year,
        "class_9": class_9,
        "maths": maths,
        "english": english,
        "rooms": {"a": room_a, "b": room_b, "c": room_c},
        "maths_a": maths_a,
        "maths_b": maths_b,
        "english_c": english_c,
        "other_maths": other_maths,
        "ch1": ch1,
        "ch2": ch2,
        "employee": employee,
    }
    conn.close()


def _upgrade(conn, module=None):
    module = module or _module()
    with Operations.context(MigrationContext.configure(conn)):
        module.upgrade()
    return module


def test_m2_is_the_single_head_with_the_expected_parent():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    # M3 is the head now and descends from M2, so the chain is still one line.
    assert script.get_heads() == ["f5b6c7d8e9f0"]
    assert script.get_revision("f3e4a5b6c7d8").down_revision == REVISION
    assert script.get_revision(REVISION).down_revision == PARENT
    module = _module()
    assert callable(module.upgrade) and callable(module.downgrade)


def test_chapters_become_section_owned_and_keep_their_progress(world):
    conn = world["conn"]
    subjects_before = _count(conn, "SELECT count(*) FROM classroomsubject")
    _upgrade(conn)

    # No classroom subject is ever created.
    assert _count(conn, "SELECT count(*) FROM classroomsubject") == subjects_before

    rows = conn.execute(
        sa.text(
            "SELECT id, classroom_subject_id, sequence, name, status, completed_on, "
            "completed_by_employee_id FROM chapter ORDER BY classroom_subject_id, sequence"
        )
    ).all()
    by_section: dict[str, list] = {}
    for row in rows:
        by_section.setdefault(row[1], []).append(row)

    # 2 old chapters x 2 eligible sections; section C (no Maths) gets none.
    assert len(rows) == 4
    assert set(by_section) == {world["maths_a"], world["maths_b"]}
    assert world["other_maths"] not in by_section

    a_rows = by_section[world["maths_a"]]
    b_rows = by_section[world["maths_b"]]
    assert [(row[2], row[3]) for row in a_rows] == [
        (1, "Number Systems"),
        (2, "Polynomials"),
    ]
    assert [(row[2], row[3]) for row in b_rows] == [
        (1, "Number Systems"),
        (2, "Polynomials"),
    ]

    # The canonical rows keep their ids (exam_paper_chapter links survive).
    assert {row[0] for row in a_rows} == {world["ch1"], world["ch2"]}

    # Progress went to the copy that belongs to its own section, nowhere else.
    assert a_rows[0][4] == "Completed"
    assert a_rows[0][6] == world["employee"]
    assert a_rows[1][4] == "Pending"
    assert b_rows[0][4] == "Pending"
    assert b_rows[1][4] == "In progress"


def test_operational_rows_point_at_their_section_subject(world):
    conn = world["conn"]
    before = {
        table: _count(conn, f"SELECT count(*) FROM {table}")
        for table in (
            "timetableperiod",
            "homeworkassignment",
            "attendancerecord",
            "classlog",
        )
    }
    _upgrade(conn)

    for table, count in before.items():
        assert _count(conn, f"SELECT count(*) FROM {table}") == count
    assert (
        conn.execute(
            sa.text("SELECT classroom_subject_id FROM timetableperiod")
        ).scalar_one()
        == world["maths_b"]
    )
    assert (
        conn.execute(
            sa.text("SELECT classroom_subject_id FROM homeworkassignment")
        ).scalar_one()
        == world["maths_a"]
    )
    # Subject rows map; the day-level attendance row and the day-level log stay NULL.
    attendance = {
        row[0]: row[1]
        for row in conn.execute(
            sa.text("SELECT subject_id, classroom_subject_id FROM attendancerecord")
        ).all()
    }
    assert attendance == {world["maths"]: world["maths_a"], None: None}
    logs = sorted(
        conn.execute(sa.text("SELECT classroom_subject_id FROM classlog"))
        .scalars()
        .all(),
        key=str,
    )
    assert logs == sorted([world["maths_b"], None], key=str)

    # A teacher row without a year resolves through the current year's section subject.
    assert (
        conn.execute(
            sa.text("SELECT classroom_subject_id FROM subjectteacher")
        ).scalar_one()
        == world["maths_a"]
    )


def test_the_count_report_adds_up(world):
    module = _module()
    conn = world["conn"]
    with Operations.context(MigrationContext.configure(conn)):
        module._add_columns(conn)
        report = module.run_data_steps(conn)
    assert report["copies"] == 2
    assert report["counts"]["chapter"] == {
        "before": 2,
        "expected_after": 4,
        "actual_after": 4,
        "delta": 0,
    }
    assert report["counts"]["classroomsubject"]["delta"] == 0
    assert report["counts"]["chapterprogress"]["delta"] == 0
    for table in (
        "timetableperiod",
        "homeworkassignment",
        "attendancerecord",
        "classlog",
    ):
        assert report["counts"][table]["delta"] == 0


def test_progress_of_a_section_without_the_subject_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "chapterprogress",
        school_id=world["school"],
        chapter_id=world["ch1"],
        classroom_id=world["rooms"]["c"],
        status="Completed",
        completed_on=None,
        completed_by_employee_id=None,
        updated_at="2026-05-02 00:00:00",
    )
    subjects_before = _count(conn, "SELECT count(*) FROM classroomsubject")
    module = _module()
    with pytest.raises(module.MigrationAbort, match="chapterprogress"):
        _upgrade(conn, module)
    assert _count(conn, "SELECT count(*) FROM classroomsubject") == subjects_before


def test_a_chapter_no_section_can_take_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "chapter",
        school_id=world["school"],
        class_id=world["class_9"],
        subject_id=_id(),
        academic_year_id=world["year"],
        sequence=1,
        name="Orphan",
        planned_date=None,
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="no section of this class"):
        _upgrade(conn, module)


def test_a_timetable_row_without_a_section_subject_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "timetableperiod",
        school_id=world["school"],
        classroom_id=world["rooms"]["c"],
        subject_id=world["maths"],
        academic_year_id=world["year"],
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="timetableperiod"):
        _upgrade(conn, module)
    # Nothing was invented to make the row fit.
    assert _count(conn, "SELECT count(*) FROM classroomsubject") == 4
