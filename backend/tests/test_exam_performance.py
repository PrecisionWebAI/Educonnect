"""Exam module, Phase 9: the number of database statements must not grow with the data.

Each scenario measures one call on a small school and again on a much bigger one (more
exams, more children, more sections) and asserts the **count stays put** - or, where a
statement per child is genuinely unavoidable (each family is sent its own child's marks),
that it grows by no more than a small, stated amount per child. A screen that costs a query
per row is a screen that gets slow exactly when the school gets big.

Runs under pytest.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import event

from app.domains.academic.classroom.exams.plan import service
from tests.test_classroom_exams import _room, _student
from tests.test_exam_class_test import world
from tests.test_exam_marks_entry import entry, make_test, save
from tests.course_support import section_subject

D = Decimal


def count_statements(session, call) -> int:
    seen: list[str] = []
    engine = session.get_bind()

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", on_execute)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)
    return len(seen)


def more_tests(session, data, n, start=1):
    """`n` more class tests of the same section, each on its own day."""
    return [
        make_test(
            session, data, exam_date=date(2026, 12, 1) + timedelta(days=start + i)
        )
        for i in range(n)
    ]


def test_the_exam_list_costs_the_same_for_two_exams_as_for_twelve():
    session, data = world()
    for who in ("office", "meera", "aarav_parent"):
        user = data[who]
        service.list_exams(session, user)  # warm one-off lookups

    more_tests(session, data, 2)
    small = {
        who: count_statements(session, lambda w=who: service.list_exams(session, data[w]))
        for who in ("office", "meera", "aarav_parent")
    }
    more_tests(session, data, 10, start=10)
    big = {
        who: count_statements(session, lambda w=who: service.list_exams(session, data[w]))
        for who in ("office", "meera", "aarav_parent")
    }
    assert big == small, f"{small} vs {big} statements for 2 vs 12 exams"


def test_the_marks_sheet_costs_the_same_for_four_children_as_for_twenty_four():
    session, data = world()
    paper = make_test(session, data).papers[0]
    save(session, paper.id, [entry(data["aarav"], 40)], data["meera"])
    service.paper_marks(session, paper.id, data["meera"])
    small = count_statements(
        session, lambda: service.paper_marks(session, paper.id, data["meera"])
    )

    kids = [_student(session, f"kid {n}", f"P9-{n}", data["room"]) for n in range(20)]
    save(session, paper.id, [entry(kid, 10 + n % 30) for n, kid in enumerate(kids)], data["meera"])
    big = count_statements(
        session, lambda: service.paper_marks(session, paper.id, data["meera"])
    )
    assert big == small, f"{small} vs {big} statements"


def test_the_exam_read_costs_the_same_for_one_section_as_for_eight():
    session, data = world()
    exam = make_test(session, data)
    service.read_exam(session, exam.id, data["office"])
    small = count_statements(
        session, lambda: service.read_exam(session, exam.id, data["office"])
    )

    rooms = [data["room"]]
    for letter in "BCDEFGH":
        room = data["other_room"] if letter == "B" else _room(session, "Class 9", letter, 9)
        if letter != "B":
            section_subject(session, room.id, "Mathematics", code="MTH")
        rooms.append(room)
    bigger = make_test(
        session,
        data,
        user=data["office"],
        section_ids=[room.id for room in rooms],
        taken_by_employee_id=data["employee"].id,
        exam_date=date(2026, 12, 20),
    )
    assert len(bigger.papers) == 8
    service.read_exam(session, bigger.id, data["office"])
    big = count_statements(
        session, lambda: service.read_exam(session, bigger.id, data["office"])
    )
    assert big == small, f"{small} vs {big} statements for 1 vs 8 sections"


def test_publishing_costs_a_few_statements_per_child_and_no_more():
    """Each family is told its own child's marks, so a statement per child is unavoidable
    - but only a handful, never a handful of queries per *message*."""
    session, data = world()

    def publish(n_kids):
        exam = make_test(
            session, data, exam_date=date(2026, 12, 1) + timedelta(days=n_kids)
        )
        paper = exam.papers[0]
        kids = [_student(session, f"p{n_kids}-{n}", f"P9P{n_kids}-{n}", data["room"]) for n in range(n_kids)]
        everyone = list(service._section_students(session, session.get(service.ExamPaper, paper.id)).values())
        save(session, paper.id, [entry(kid, 20) for kid in everyone], data["meera"])
        return count_statements(
            session, lambda: service.publish_paper(session, paper.id, data["meera"])
        )

    publish(1)  # warm one-off lookups
    few = publish(4)
    many = publish(24)
    per_child = (many - few) / 20
    assert per_child <= 6, f"{per_child:.1f} statements per extra child ({few} -> {many})"
