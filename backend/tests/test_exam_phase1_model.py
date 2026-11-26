"""Exam module, Phase 1: the new columns, enums, defaults and migration chain.

Nothing here runs a request - it checks that the data model says what `phase3.md` says,
and that the migration is the next link in the chain.
"""

import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.exams.models import (
    EXAM_STATUSES,
    EXAM_TYPES,
    PASS_MODES,
    SCHOOL_EXAM_TYPES,
    Exam,
    ExamPaper,
    ExamStatus,
    ExamType,
    Mark,
    PassMode,
)
from app.domains.admin.settings import values as setting_values


def memory_session() -> Session:
    import importlib

    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_a_test_can_be_cancelled_and_the_old_statuses_still_exist():
    assert "cancelled" in EXAM_STATUSES
    assert ExamStatus.cancelled == "cancelled"
    for kept in ("draft", "scheduled", "done", "marks_entry", "published"):
        assert kept in EXAM_STATUSES


def test_exam_types_are_the_ones_in_the_spec():
    assert set(EXAM_TYPES) == {
        "class_test",
        "unit_test",
        "periodic_test",
        "mid_term_test",
        "half_yearly",
        "annual",
        "pre_board",
        "practical",
        "custom",
    }
    # A school exam is never a class test, and a class test is not in its dropdown.
    assert "class_test" not in SCHOOL_EXAM_TYPES
    assert ExamType.custom in [ExamType(word) for word in SCHOOL_EXAM_TYPES]
    assert PASS_MODES == (PassMode.marks.value, PassMode.grade.value)


def test_new_columns_are_all_optional_so_old_rows_read_unchanged():
    session = memory_session()
    exam = Exam(name="Unit Test 1")
    session.add(exam)
    session.commit()
    session.refresh(exam)
    assert exam.family_note is None
    assert exam.datesheet_published_at is None
    assert exam.datesheet_published_by_user_id is None
    assert exam.status == ExamStatus.draft


def test_a_paper_keeps_its_own_pass_line_grading_copy_and_syllabus():
    session = memory_session()
    from tests.test_classroom_timetable import seed

    data = seed(session)
    exam = Exam(name="Class Test", exam_type="class_test", family_note="Bring a ruler")
    session.add(exam)
    session.commit()
    session.refresh(exam)

    ladder = [
        {"min_percent": 90, "grade": "A1"},
        {"min_percent": 0, "grade": "E"},
    ]
    paper = ExamPaper(
        exam_id=exam.id,
        classroom_subject_id=data["maths"].id,
        exam_date=date(2026, 12, 1),
        max_marks=Decimal("50"),
        taken_by_employee_id=data["meera"].id,
        pass_mode=PassMode.grade,
        pass_percent=Decimal("33"),
        passing_grade="D",
        grading_scale=ladder,
        syllabus_text="Fractions and decimals",
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)

    assert paper.taken_by_employee_id == data["meera"].id
    assert paper.pass_mode == "grade"
    assert paper.passing_grade == "D"
    assert paper.pass_percent == Decimal("33.00")
    assert paper.grading_scale == ladder, "the ladder is stored as the paper's own copy"
    assert paper.syllabus_text == "Fractions and decimals"
    # No start/end time is asked for any more: the old columns just stay empty.
    assert paper.start_time is None and paper.end_time is None


def test_a_mark_can_name_its_enrollment_but_does_not_have_to():
    # `enrollment_id` is optional (older marks are backfilled by the migration).
    assert Mark.model_fields["enrollment_id"].default is None


def test_the_school_defaults_are_33_percent_and_both_marks_and_grades():
    session = memory_session()
    from tests.test_classroom_timetable import seed

    seed(session)  # a school in the session: settings belong to a school
    assert setting_values.get_value(session, "exam.pass_percent") == "33"
    assert setting_values.get_value(session, "exam.display_mode") == "both"
    # A school's own answer wins over the default, and only for that key.
    setting_values.set_value(session, "exam.pass_percent", 40)
    assert setting_values.get_value(session, "exam.pass_percent") == "40"
    assert setting_values.get_value(session, "exam.display_mode") == "both"


def test_the_migration_is_the_next_link_after_0005():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0006_exam_marking_setup.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0006"
    assert module.down_revision == "0005"
    # Both directions exist, so a bad deploy can be undone.
    assert callable(module.upgrade) and callable(module.downgrade)

    others = {
        p.name
        for p in path.parent.glob("*.py")
        if p.name not in (path.name, "__init__.py")
    }
    assert "0005_chapter_approved_count.py" in others


def test_nothing_else_in_the_exam_tables_changed_shape():
    # The older read paths still work on the table: a row with none of the new fields.
    session = memory_session()
    session.add(Exam(name="Mid Term", exam_type="Mid-term"))
    session.commit()
    row = session.exec(select(Exam)).first()
    assert row.exam_type == "Mid-term", "an older free-text type is kept as it was"
    assert isinstance(row.created_at, datetime)


def test_the_passing_grade_migration_follows_0006():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0007_exam_passing_grade.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0007", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0007" and module.down_revision == "0006"
    assert callable(module.upgrade) and callable(module.downgrade)


def test_the_indexes_migration_follows_0007_and_the_models_carry_the_same_indexes():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0008_exam_indexes.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0008", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0008" and module.down_revision == "0007"
    assert callable(module.upgrade) and callable(module.downgrade)

    from app.domains.main.notifications.models import Notification

    assert any(i.name == "ix_exam_academic_year_id" for i in Exam.__table__.indexes)
    assert any(
        i.name == "ix_notification_event_entity" for i in Notification.__table__.indexes
    )
