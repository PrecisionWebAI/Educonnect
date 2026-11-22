"""The academic-year column is allowed on exactly the tables that own it.

The product rule is "year is a context, not a column sprinkled everywhere": child
tables inherit it through their parent, and date-based modules derive it from the
date. This test is the guard against a later feature quietly adding
`academic_year_id` to `student`, `salarypayment` or a marks/history table.
"""

from sqlmodel import SQLModel

from app.core.schema import load_models

#: Tables that genuinely own a year column.
EXPECTED_WITH_YEAR = {
    "chapter",
    "classroomsubject",
    "classteacherassignment",
    "enrollment",
    "exam",
    "feestructure",
    "holiday",
    "leavebalance",
    "leaverequest",
    "lessonplan",
    "subjectteacher",
    "timetableperiod",
}

#: Tables where a year must be derived from a date or inherited from a parent.
EXPECTED_WITHOUT_YEAR = {
    "student",
    "employee",
    "attendancerecord",
    "staffattendancerecord",
    "salarypayment",
    "feetransaction",
    "lessonplanhistory",
    "promotionbatch",
    "promotiondecision",
    "exam_paper",
    "exam_paper_chapter",
    "marks",
}


def _year_column_tables() -> set[str]:
    load_models()
    return {
        table.name
        for table in SQLModel.metadata.tables.values()
        if "academic_year_id" in table.columns
    }


def test_only_the_expected_tables_own_an_academic_year_column() -> None:
    actual = _year_column_tables()

    assert actual == EXPECTED_WITH_YEAR, (
        "A table gained/lost academic_year_id. Child tables must inherit the year; "
        "date-based tables must derive it instead of storing a second copy."
    )


def test_forbidden_child_tables_have_no_academic_year_column() -> None:
    load_models()
    for table_name in EXPECTED_WITHOUT_YEAR:
        table = SQLModel.metadata.tables.get(table_name)
        assert table is not None, f"expected table {table_name} is not loaded"
        assert "academic_year_id" not in table.columns, (
            f"{table_name} must not carry a second academic-year column"
        )


def test_student_keeps_only_the_separation_event_year() -> None:
    load_models()
    student = SQLModel.metadata.tables["student"]
    assert "separation_academic_year_id" in student.columns
    assert "academic_year_id" not in student.columns
