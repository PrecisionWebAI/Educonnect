"""M3 (`f3e4a5b6c7d8`): class-level exam papers become section papers.

The data steps run here for real, on an in-memory SQLite database built in the **pre-M3
shape** (a paper is `(exam, class, school-wide subject)`; marks hang from that one paper).
The rules under test are the plan's hard rules: no `classroomsubject` row is created,
marks are counted exactly, a student's marks follow the section they **sat in** (read
from `enrollment` for the exam year), and anything unmappable aborts the migration.
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

REVISION = "f3e4a5b6c7d8"
PARENT = "f2d3e4a5b6c7"
PATH = Path("alembic/versions/f3e4a5b6c7d8_subject_exam_papers.py")

sqlite3.register_adapter(UUID, lambda value: value.hex)


def _module():
    spec = importlib.util.spec_from_file_location("m3_migration", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _id() -> str:
    return uuid4().hex


PRE_M3_SCHEMA = """
CREATE TABLE school (id TEXT PRIMARY KEY);
CREATE TABLE app_user (id TEXT PRIMARY KEY);
CREATE TABLE subject (id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE academic_year (id TEXT PRIMARY KEY, school_id TEXT, is_current BOOLEAN);
CREATE TABLE classroom (id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, section_id TEXT);
CREATE TABLE classroomsubject (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_id TEXT, subject_id TEXT,
    academic_year_id TEXT, name TEXT NOT NULL, status TEXT
);
CREATE TABLE chapter (
    id TEXT PRIMARY KEY, school_id TEXT, classroom_subject_id TEXT, sequence INTEGER,
    name TEXT
);
CREATE TABLE enrollment (
    id TEXT PRIMARY KEY, school_id TEXT, student_id TEXT, classroom_id TEXT,
    academic_year_id TEXT
);
CREATE TABLE exam (id TEXT PRIMARY KEY, school_id TEXT, academic_year_id TEXT);
CREATE TABLE exam_paper (
    id TEXT PRIMARY KEY, school_id TEXT, exam_id TEXT, class_id TEXT, subject_id TEXT,
    exam_date DATE, start_time TIME, end_time TIME, max_marks NUMERIC, passing_marks NUMERIC,
    room TEXT, note TEXT, published_at DATETIME
);
CREATE TABLE exam_paper_chapter (
    id TEXT PRIMARY KEY, school_id TEXT, exam_paper_id TEXT, chapter_id TEXT
);
CREATE TABLE marks (
    id TEXT PRIMARY KEY, school_id TEXT, exam_id TEXT, student_id TEXT, subject_id TEXT,
    exam_paper_id TEXT, marks_obtained NUMERIC
);
CREATE TABLE paperdraft (
    id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, subject_id TEXT, section_id TEXT
);
CREATE TABLE examsource (
    id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, subject_id TEXT
);
CREATE TABLE questionusagelog (
    id TEXT PRIMARY KEY, school_id TEXT, class_id TEXT, subject_id TEXT
);
CREATE TABLE timetableperiod (id TEXT PRIMARY KEY);
CREATE TABLE homeworkassignment (id TEXT PRIMARY KEY);
CREATE TABLE attendancerecord (id TEXT PRIMARY KEY);
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
    """School A: Class 9 (sections A, B have Maths; C has none), exam 2025-26 and 2026-27."""
    engine = sa.create_engine("sqlite://")
    conn = engine.connect()
    for statement in PRE_M3_SCHEMA.split(";"):
        if statement.strip():
            conn.execute(sa.text(statement))

    school = _insert(conn, "school")
    past = _insert(conn, "academic_year", school_id=school, is_current=False)
    year = _insert(conn, "academic_year", school_id=school, is_current=True)
    class_9, maths = _id(), _insert(conn, "subject", name="Mathematics")
    room_a = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="a"
    )
    room_b = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="b"
    )
    room_c = _insert(
        conn, "classroom", school_id=school, class_id=class_9, section_id="c"
    )

    def course(room, academic_year, name="Mathematics"):
        return _insert(
            conn,
            "classroomsubject",
            school_id=school,
            classroom_id=room,
            subject_id=maths,
            academic_year_id=academic_year,
            name=name,
            status="Active",
        )

    # The exam sat in 2025-26: both sections had Maths that year.
    a_past, b_past = course(room_a, past), course(room_b, past)
    course(room_a, year)
    course(room_b, year)

    ch1 = _insert(
        conn,
        "chapter",
        school_id=school,
        classroom_subject_id=a_past,
        sequence=1,
        name="Number Systems",
    )
    ch2 = _insert(
        conn,
        "chapter",
        school_id=school,
        classroom_subject_id=a_past,
        sequence=2,
        name="Polynomials",
    )
    _insert(
        conn,
        "chapter",
        school_id=school,
        classroom_subject_id=b_past,
        sequence=1,
        name="Number Systems",
    )
    _insert(
        conn,
        "chapter",
        school_id=school,
        classroom_subject_id=b_past,
        sequence=2,
        name="Polynomials",
    )

    exam = _insert(conn, "exam", school_id=school, academic_year_id=past)
    paper = _insert(
        conn,
        "exam_paper",
        school_id=school,
        exam_id=exam,
        class_id=class_9,
        subject_id=maths,
        max_marks=100,
        published_at=None,
    )
    _insert(
        conn,
        "exam_paper_chapter",
        school_id=school,
        exam_paper_id=paper,
        chapter_id=ch1,
    )
    _insert(
        conn,
        "exam_paper_chapter",
        school_id=school,
        exam_paper_id=paper,
        chapter_id=ch2,
    )

    s_a, s_b, s_promoted = _id(), _id(), _id()
    for student, room in ((s_a, room_a), (s_b, room_b), (s_promoted, room_a)):
        _insert(
            conn,
            "enrollment",
            school_id=school,
            student_id=student,
            classroom_id=room,
            academic_year_id=past,
        )
    # The promoted student sits in 9-B *today* (2026-27), but sat the exam in 9-A.
    _insert(
        conn,
        "enrollment",
        school_id=school,
        student_id=s_promoted,
        classroom_id=room_b,
        academic_year_id=year,
    )
    marks = {
        name: _insert(
            conn,
            "marks",
            school_id=school,
            exam_id=exam,
            student_id=student,
            subject_id=maths,
            exam_paper_id=paper,
            marks_obtained=70,
        )
        for name, student in (("a", s_a), ("b", s_b), ("promoted", s_promoted))
    }

    yield {
        "conn": conn,
        "school": school,
        "past": past,
        "year": year,
        "class_9": class_9,
        "maths": maths,
        "rooms": {"a": room_a, "b": room_b, "c": room_c},
        "a_past": a_past,
        "b_past": b_past,
        "exam": exam,
        "paper": paper,
        "ch1": ch1,
        "marks": marks,
        "students": {"a": s_a, "b": s_b, "promoted": s_promoted},
    }
    conn.close()


def _upgrade(conn, module=None):
    module = module or _module()
    with Operations.context(MigrationContext.configure(conn)):
        module.upgrade()
    return module


def test_m3_is_the_single_head_with_the_expected_parent():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    # M4 is the head now and descends from M3, so the chain is still one line.
    assert script.get_heads() == ["f4a5b6c7d8e9"]
    assert script.get_revision("f4a5b6c7d8e9").down_revision == REVISION
    assert script.get_revision(REVISION).down_revision == PARENT
    module = _module()
    assert callable(module.upgrade) and callable(module.downgrade)


def test_a_class_paper_becomes_one_paper_per_section_sharing_a_group(world):
    conn = world["conn"]
    subjects_before = _count(conn, "SELECT count(*) FROM classroomsubject")
    _upgrade(conn)

    assert _count(conn, "SELECT count(*) FROM classroomsubject") == subjects_before
    papers = conn.execute(
        sa.text("SELECT id, classroom_subject_id, paper_group_id FROM exam_paper")
    ).all()
    assert len(papers) == 2, "the section with no Maths (9-C) gets no paper"
    assert {row[1] for row in papers} == {world["a_past"], world["b_past"]}
    assert len({row[2] for row in papers}) == 1 and papers[0][2] is not None

    # The old row survives as the first section's paper.
    assert world["paper"] in {row[0] for row in papers}

    group = conn.execute(
        sa.text("SELECT display_title FROM exam_paper_group")
    ).scalar_one()
    assert group == "Mathematics"
    names = (
        conn.execute(
            sa.text("SELECT name FROM exam_paper_group_chapter ORDER BY sequence")
        )
        .scalars()
        .all()
    )
    assert names == ["Number Systems", "Polynomials"]
    assert _count(conn, "SELECT count(*) FROM exam_paper_chapter") == 0, (
        "chapters live on the group"
    )


def test_marks_follow_the_section_the_student_sat_in(world):
    conn = world["conn"]
    _upgrade(conn)

    def paper_of(student):
        return conn.execute(
            sa.text(
                "SELECT cs.classroom_id FROM marks AS m "
                "JOIN exam_paper AS p ON p.id = m.exam_paper_id "
                "JOIN classroomsubject AS cs ON cs.id = p.classroom_subject_id "
                "WHERE m.student_id = :student"
            ),
            {"student": student},
        ).scalar_one()

    assert paper_of(world["students"]["a"]) == world["rooms"]["a"]
    assert paper_of(world["students"]["b"]) == world["rooms"]["b"]
    # Sat in 9-A in 2025-26, is in 9-B now: the mark stays on 9-A's paper.
    assert paper_of(world["students"]["promoted"]) == world["rooms"]["a"]
    assert _count(conn, "SELECT count(*) FROM marks") == 3, (
        "marks: before == after, exactly"
    )


def test_the_count_report_adds_up(world):
    module = _module()
    conn = world["conn"]
    with Operations.context(MigrationContext.configure(conn)):
        module._create_group_tables(conn)
        module._add_columns(conn)
        report = module.run_data_steps(conn)
    assert report["copies"] == 1 and report["groups"] == 1
    assert report["counts"]["exam_paper"] == {
        "before": 1,
        "expected_after": 2,
        "actual_after": 2,
        "delta": 0,
    }
    assert report["counts"]["exam_paper_chapter"] == {
        "before": 2,
        "expected_after": 0,
        "actual_after": 0,
        "delta": 0,
    }
    assert report["counts"]["marks"]["delta"] == 0
    assert report["counts"]["classroomsubject"]["delta"] == 0
    assert len(report["skipped_sections"]) == 1, "9-C is reported, not invented"


def test_a_student_with_no_enrollment_that_year_aborts(world):
    conn = world["conn"]
    stranger = _id()
    _insert(
        conn,
        "marks",
        school_id=world["school"],
        exam_id=world["exam"],
        student_id=stranger,
        subject_id=world["maths"],
        exam_paper_id=world["paper"],
        marks_obtained=1,
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="no enrollment"):
        _upgrade(conn, module)


def test_an_exam_without_a_year_aborts_its_marks(world):
    conn = world["conn"]
    conn.execute(sa.text("UPDATE exam SET academic_year_id = NULL"))
    module = _module()
    # The school's current year is used for the papers, but marks need the exam's own year.
    with pytest.raises(module.MigrationAbort, match="no academic year"):
        _upgrade(conn, module)


def test_a_paper_no_section_can_take_aborts_and_creates_nothing(world):
    conn = world["conn"]
    _insert(
        conn,
        "exam_paper",
        school_id=world["school"],
        exam_id=world["exam"],
        class_id=world["class_9"],
        subject_id=_id(),
        max_marks=50,
    )
    before = _count(conn, "SELECT count(*) FROM classroomsubject")
    module = _module()
    with pytest.raises(module.MigrationAbort, match="no section of this class"):
        _upgrade(conn, module)
    assert _count(conn, "SELECT count(*) FROM classroomsubject") == before


def test_a_single_section_paper_gets_no_group_and_keeps_its_own_chapters(world):
    conn = world["conn"]
    # A second class with exactly one section that has the subject.
    class_10 = _id()
    room = _insert(
        conn, "classroom", school_id=world["school"], class_id=class_10, section_id="a"
    )
    cs = _insert(
        conn,
        "classroomsubject",
        school_id=world["school"],
        classroom_id=room,
        subject_id=world["maths"],
        academic_year_id=world["past"],
        name="Mathematics",
        status="Active",
    )
    chapter = _insert(
        conn,
        "chapter",
        school_id=world["school"],
        classroom_subject_id=cs,
        sequence=1,
        name="Algebra",
    )
    paper = _insert(
        conn,
        "exam_paper",
        school_id=world["school"],
        exam_id=world["exam"],
        class_id=class_10,
        subject_id=world["maths"],
        max_marks=50,
    )
    # An old link pointing at a chapter of a *different* section subject.
    _insert(
        conn,
        "chapter",
        school_id=world["school"],
        classroom_subject_id=world["a_past"],
        sequence=3,
        name="Algebra",
    )
    other = conn.execute(
        sa.text(
            "SELECT id FROM chapter WHERE classroom_subject_id = :cs AND name = 'Algebra'"
        ),
        {"cs": world["a_past"]},
    ).scalar_one()
    _insert(
        conn,
        "exam_paper_chapter",
        school_id=world["school"],
        exam_paper_id=paper,
        chapter_id=other,
    )

    _upgrade(conn)

    row = conn.execute(
        sa.text(
            "SELECT classroom_subject_id, paper_group_id FROM exam_paper WHERE id = :id"
        ),
        {"id": paper},
    ).one()
    assert row[0] == cs and row[1] is None
    linked = conn.execute(
        sa.text("SELECT chapter_id FROM exam_paper_chapter WHERE exam_paper_id = :id"),
        {"id": paper},
    ).scalar_one()
    assert linked == chapter, (
        "the link was re-pointed to this section's chapter of that name"
    )


def test_drafts_and_the_library_link_only_when_unambiguous(world):
    conn = world["conn"]
    # A draft that names section + subject resolves to that section's subject.
    _insert(
        conn,
        "paperdraft",
        school_id=world["school"],
        class_id=world["class_9"],
        subject_id=world["maths"],
        section_id="a",
    )
    # A class-level draft/source has no single section: it stays NULL, and is not an error.
    loose = _insert(
        conn,
        "paperdraft",
        school_id=world["school"],
        class_id=world["class_9"],
        subject_id=world["maths"],
    )
    source = _insert(
        conn,
        "examsource",
        school_id=world["school"],
        class_id=world["class_9"],
        subject_id=world["maths"],
    )
    _upgrade(conn)

    linked = conn.execute(
        sa.text("SELECT classroom_subject_id FROM paperdraft WHERE section_id = 'a'")
    ).scalar_one()
    assert linked is not None
    assert (
        conn.execute(
            sa.text("SELECT classroom_subject_id FROM paperdraft WHERE id = :id"),
            {"id": loose},
        ).scalar_one()
        is None
    )
    assert (
        conn.execute(
            sa.text("SELECT classroom_subject_id FROM examsource WHERE id = :id"),
            {"id": source},
        ).scalar_one()
        is None
    )


def test_a_draft_that_names_a_missing_section_subject_aborts(world):
    conn = world["conn"]
    _insert(
        conn,
        "paperdraft",
        school_id=world["school"],
        class_id=world["class_9"],
        subject_id=world["maths"],
        section_id="c",
    )
    module = _module()
    with pytest.raises(module.MigrationAbort, match="paperdraft"):
        _upgrade(conn, module)
