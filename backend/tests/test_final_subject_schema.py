"""The finished classroom-owned subject model: nothing of the old one is left.

phase3.md (5.1-5.2) asks for these as checks rather than promises: a subject belongs to
one section; there is no school-wide subject table, no teacher-subject table, no
`chapterprogress`, no `subject_id` column or API field, and no code that imports the old
models.
"""

import ast
import importlib
import pkgutil
from pathlib import Path

from pydantic import BaseModel
from sqlmodel import SQLModel

import app.domains as domains_package
from app.core.schema import MODEL_MODULES

APP = Path(__file__).resolve().parents[1] / "app"
REMOVED_NAMES = {
    "Subject",
    "SubjectBase",
    "SubjectCreate",
    "SubjectUpdate",
    "SubjectRead",
    "TeacherSubject",
    "ChapterProgress",
}


def _load_models() -> None:
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")


def test_the_old_tables_are_not_in_the_schema():
    _load_models()
    tables = set(SQLModel.metadata.tables)
    assert not {"subject", "teachersubject", "chapterprogress"} & tables


def test_no_column_points_at_the_old_subject_and_no_legacy_subject_column_remains():
    _load_models()
    pointing = []
    legacy = []
    for table in SQLModel.metadata.tables.values():
        for column in table.columns:
            if any(key.target_fullname == "subject.id" for key in column.foreign_keys):
                pointing.append(f"{table.name}.{column.name}")
            if column.name == "subject_id":
                legacy.append(table.name)
    assert pointing == [], pointing
    assert legacy == [], legacy


def test_the_exact_columns_the_plan_dropped_are_gone():
    _load_models()
    tables = SQLModel.metadata.tables
    dropped = {
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
        "pipeline_hiring_table": {"subject_id"},
    }
    for table, columns in dropped.items():
        present = set(tables[table].columns.keys())
        assert not columns & present, f"{table} still has {columns & present}"


def test_what_each_row_hangs_from_is_required():
    _load_models()
    tables = SQLModel.metadata.tables
    for table in (
        "subjectteacher",
        "timetableperiod",
        "homeworkassignment",
        "exam_paper",
    ):
        assert tables[table].columns["classroom_subject_id"].nullable is False, table
    assert tables["marks"].columns["exam_paper_id"].nullable is False
    assert tables["chapter"].columns["classroom_subject_id"].nullable is False


def test_no_code_imports_a_removed_model_or_schema():
    offenders = []
    for path in APP.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in REMOVED_NAMES:
                        offenders.append(f"{path.relative_to(APP)}: {alias.name}")
    assert offenders == [], offenders


def test_no_request_or_response_schema_carries_a_subject_id():
    offenders = []
    for module_info in pkgutil.walk_packages(domains_package.__path__, "app.domains."):
        if not module_info.name.endswith(".schemas"):
            continue
        module = importlib.import_module(module_info.name)
        for name, value in vars(module).items():
            if (
                isinstance(value, type)
                and issubclass(value, BaseModel)
                and value.__module__ == module.__name__
                and "subject_id" in value.model_fields
            ):
                offenders.append(f"{module.__name__}.{name}")
    assert offenders == [], offenders
