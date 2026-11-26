"""Exam module, Phase 9: another school is a `404`, and a notification is sent exactly as often
as it should be.

Part one - **isolation.** A second school lives in the same database. Everything the first
school's strongest caller (the school admin) can do must answer `404` - never `403`, which
would confirm the id exists - when it names the other school's exam, paper, subject, section,
student or syllabus; lists never mention it; a duplicate warning never sees it; and nothing the
first school does writes a notification into the other.

Part two - **notifications.** Repeating the *same* thing tells nobody twice; a *different*
change (a second reschedule, a second correction, a second syllabus edit) is never swallowed by
the dedupe key of the first.

Runs under pytest.
"""

from tests.exam_helpers import publish
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.exams.plan import (
    class_test,
    overview,
    school_exam,
    service,
)
from app.domains.academic.classroom.exams.plan.schemas import (
    ClassTestCreateIn,
    ClassTestUpdateIn,
    MarkChangeIn,
    SchoolExamCreateIn,
    SchoolExamRowIn,
    SchoolExamUpdateIn,
    SyllabusIn,
)
from app.domains.admin.platform.models import School
from app.domains.main.notifications.models import Notification
from tests.course_support import section_subject
from tests.test_classroom_exams import _room, _student
from tests.test_exam_class_test import heard, world
from tests.test_exam_marks_entry import entry, make_test, save, told
from tests.test_exam_school_exam import make, rows

D = Decimal
DAY = date(2027, 1, 12)
LADDER = [{"min_percent": 0, "grade": "E"}]


# ----------------------------------------------------------- the other school


class Other:
    """School B's exam world: a class test with a mark, and a published date sheet."""

    pass


def build_other_school(session) -> Other:
    mine = session.info["school_id"]
    school = School(name="the other school", code="oth9", email="oth9@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    try:
        room = _room(session, "Class 9", "A", 9)
        course = section_subject(session, room.id, "Mathematics", code="MATH")
        student = _student(session, "other kid", "OTH-1", room)

        test = Exam(
            name="Class Test - Mathematics",
            exam_type="class_test",
            scope="class",
            class_id=room.class_id,
            academic_year_id=course.academic_year_id,
            status="scheduled",
        )
        sheet = Exam(
            name="Unit Test",
            exam_type="unit_test",
            scope="class",
            class_id=room.class_id,
            classroom_id=room.id,
            academic_year_id=course.academic_year_id,
            status="scheduled",
            datesheet_published_at=datetime.utcnow(),
        )
        session.add_all([test, sheet])
        session.flush()
        papers = []
        for exam in (test, sheet):
            paper = ExamPaper(
                exam_id=exam.id,
                classroom_subject_id=course.id,
                exam_date=DAY,
                max_marks=D("50"),
                pass_mode="marks",
                passing_marks=D("16.5"),
                pass_percent=D("33"),
                grading_scale=LADDER,
                syllabus_text="their syllabus",
            )
            session.add(paper)
            papers.append(paper)
        session.flush()
        mark = Mark(
            student_id=student.id, exam_paper_id=papers[0].id, marks_obtained=D("40")
        )
        session.add(mark)
        session.commit()
        other = Other()
        other.school, other.room, other.course, other.student = school, room, course, student
        other.test, other.sheet = test, sheet
        other.test_paper, other.sheet_paper, other.mark = papers[0], papers[1], mark
        return other
    finally:
        session.info["school_id"] = mine


@pytest.fixture
def two_schools():
    session, data = world()
    return session, data, build_other_school(session)


def not_found(call):
    with pytest.raises(HTTPException) as caught:
        call()
    assert caught.value.status_code == 404, (
        f"expected 404, got {caught.value.status_code}: {caught.value.detail}"
    )


# -------------------------------------------------------------- isolation


def test_another_schools_exam_is_a_404_never_a_403(two_schools):
    session, data, other = two_schools
    admin = data["office"]
    not_found(lambda: service.read_exam(session, other.test.id, admin))
    not_found(lambda: service.read_exam(session, other.sheet.id, admin))


def test_the_list_never_mentions_another_school(two_schools):
    session, data, other = two_schools
    make_test(session, data)
    ids = {e.id for e in service.list_exams(session, data["office"])}
    assert other.test.id not in ids and other.sheet.id not in ids
    assert len(ids) == 1


def test_marks_of_another_school_cannot_be_read_written_published_or_corrected(two_schools):
    session, data, other = two_schools
    admin = data["office"]
    paper = other.test_paper.id
    not_found(lambda: service.paper_marks(session, paper, admin))
    not_found(lambda: save(session, paper, [entry(data["aarav"], 10)], admin))
    not_found(lambda: service.publish_paper(session, paper, admin))
    not_found(
        lambda: service.change_mark(
            session, paper, other.student.id, MarkChangeIn(marks_obtained=D("1")), admin
        )
    )
    not_found(lambda: service.mark_history(session, paper, admin))
    assert session.get(Mark, other.mark.id).marks_obtained == D("40.00"), "untouched"


def test_another_schools_syllabus_is_a_404_to_read_and_to_write(two_schools):
    session, data, other = two_schools
    admin = data["office"]
    not_found(lambda: school_exam.get_syllabus(session, other.sheet_paper.id, admin))
    not_found(
        lambda: school_exam.set_syllabus(
            session, other.sheet_paper.id, SyllabusIn(syllabus_text="mine now"), admin
        )
    )
    assert session.get(ExamPaper, other.sheet_paper.id).syllabus_text == "their syllabus"


def test_another_schools_class_test_and_date_sheet_cannot_be_edited_cancelled_or_deleted(
    two_schools,
):
    session, data, other = two_schools
    admin = data["office"]
    not_found(
        lambda: class_test.update_class_test(
            session, other.test.id, ClassTestUpdateIn(total_marks=D("10")), admin
        )
    )
    not_found(lambda: class_test.cancel_class_test(session, other.test.id, admin))
    not_found(lambda: class_test.delete_class_test(session, other.test.id, admin))
    not_found(
        lambda: school_exam.update_school_exam(
            session, other.sheet.id, SchoolExamUpdateIn(family_note="x"), admin
        )
    )
    not_found(lambda: school_exam.publish_date_sheet(session, other.sheet.id, admin))
    not_found(lambda: school_exam.delete_school_exam(session, other.sheet.id, admin))
    assert session.get(Exam, other.test.id).status == "scheduled"


def test_nothing_can_be_scheduled_into_another_school(two_schools):
    session, data, other = two_schools
    admin = data["office"]
    base = dict(exam_date=DAY, total_marks=D("50"))
    # Their subject as the anchor, their section among ours, their section alone.
    not_found(
        lambda: class_test.create_class_test(
            session,
            ClassTestCreateIn(
                classroom_subject_id=other.course.id, section_ids=[other.room.id], **base
            ),
            admin,
        )
    )
    not_found(
        lambda: class_test.create_class_test(
            session,
            ClassTestCreateIn(
                classroom_subject_id=data["maths"].id,
                section_ids=[data["room"].id, other.room.id],
                taken_by_employee_id=data["employee"].id,
                **base,
            ),
            admin,
        )
    )
    row = SchoolExamRowIn(
        classroom_subject_id=other.course.id, exam_date=DAY, total_marks=D("50")
    )
    not_found(
        lambda: school_exam.create_school_exam(
            session,
            SchoolExamCreateIn(classroom_id=other.room.id, exam_type="unit_test", rows=[row]),
            admin,
        )
    )
    not_found(
        lambda: school_exam.create_school_exam(
            session,
            SchoolExamCreateIn(
                classroom_id=data["room"].id, exam_type="unit_test", rows=[row]
            ),
            admin,
        )
    )
    assert len(session.exec(select(Exam)).all()) == 0, "nothing was half-saved here"


def test_the_result_overview_of_another_schools_section_is_a_404(two_schools):
    session, data, other = two_schools
    for kind in ("class_test", "school_exam"):
        not_found(
            lambda kind=kind: overview.result_overview(
                session, data["office"], kind, other.room.id
            )
        )


def test_another_schools_test_is_not_a_duplicate_of_ours(two_schools):
    session, data, other = two_schools
    # Theirs is Mathematics on the same day as ours: still no warning for us.
    make_test(session, data, exam_date=DAY)


def test_nothing_this_school_does_ever_notifies_the_other(two_schools):
    session, data, other = two_schools
    exam = make_test(session, data)
    save(session, exam.papers[0].id, [entry(data["aarav"], 40)], data["meera"])
    publish(session, exam.papers[0].id, data["meera"])
    sheet = make(session, data, user=data["office"])
    school_exam.publish_date_sheet(session, sheet.id, data["office"])
    rows_ = session.exec(select(Notification)).all()
    assert rows_, "something was sent"
    mine = session.info["school_id"]
    assert {n.school_id for n in rows_} == {mine}


def test_the_reminder_job_for_one_school_never_touches_anothers_papers(two_schools):
    session, data, other = two_schools
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    mine = session.info["school_id"]
    session.info["school_id"] = other.school.id
    paper = session.get(ExamPaper, other.test_paper.id)
    paper.exam_date = tomorrow
    session.add(paper)
    session.commit()
    session.info["school_id"] = mine

    assert service.reminder_job(session) == 0, "their paper is not ours to remind about"


# ----------------------------------------------------------- notifications


def test_repeating_the_same_marks_saves_nothing_new_and_tells_nobody():
    session, data = world()
    exam = make_test(session, data)
    paper = exam.papers[0]
    save(session, paper.id, [entry(data["aarav"], 40)], data["meera"])
    save(session, paper.id, [entry(data["aarav"], 40)], data["meera"])
    assert len(session.exec(select(Mark)).all()) == 1, "one mark per child per paper"
    assert heard(session, service.EVENT_EXAM_PUBLISHED) == [], "a draft tells nobody"

    publish(session, paper.id, data["meera"])
    count = len(heard(session, service.EVENT_EXAM_PUBLISHED))
    with pytest.raises(HTTPException):
        service.publish_paper(session, paper.id, data["meera"])
    assert len(heard(session, service.EVENT_EXAM_PUBLISHED)) == count


def test_two_reschedules_both_tell_the_family():
    session, data = world()
    exam = make_test(session, data)
    for day in (date(2026, 12, 9), date(2026, 12, 14)):
        class_test.update_class_test(
            session, exam.id, ClassTestUpdateIn(exam_date=day), data["meera"]
        )
    moved = told(session, class_test.EVENT_RESCHEDULED, data["aarav_parent"].id)
    assert len(moved) == 2
    assert "9 Dec 2026" in moved[0].body and "14 Dec 2026" in moved[1].body


def test_two_corrections_of_the_same_mark_both_tell_the_family():
    session, data = world()
    exam = make_test(session, data)
    paper = exam.papers[0]
    save(session, paper.id, [entry(data["aarav"], 45)], data["meera"])
    publish(session, paper.id, data["meera"])
    for value in ("10", "20"):
        service.change_mark(
            session, paper.id, data["aarav"].id,
            MarkChangeIn(marks_obtained=D(value)), data["meera"],
        )
    assert len(told(session, service.EVENT_EXAM_MARK_CHANGED, data["aarav_parent"].id)) == 2


def test_each_change_after_publishing_a_date_sheet_is_told_and_a_repeat_is_not():
    session, data = world()
    exam = make(session, data, user=data["office"])
    school_exam.publish_date_sheet(session, exam.id, data["office"])
    maths = next(p for p in exam.papers if p.classroom_subject_id == data["maths"].id)

    for text in ("Fractions", "Fractions, decimals", "Fractions, decimals, ratio"):
        school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text=text), data["office"])
    school_exam.set_syllabus(
        session, maths.id, SyllabusIn(syllabus_text="Fractions, decimals, ratio"), data["office"]
    )
    assert len(told(session, school_exam.EVENT_SYLLABUS, data["aarav_parent"].id)) == 3

    for note in ("Bring a pen", "Bring a pencil"):
        school_exam.update_school_exam(
            session, exam.id, SchoolExamUpdateIn(family_note=note), data["office"]
        )
    assert len(told(session, school_exam.EVENT_CHANGED, data["aarav_parent"].id)) == 2


def test_two_tests_on_one_day_each_announce_themselves():
    session, data = world()
    make_test(session, data)
    make_test(session, data, confirm_duplicate=True, total_marks=D("20"))
    sent = told(session, class_test.EVENT_SCHEDULED, data["aarav_parent"].id)
    assert len(sent) == 2, "the second is its own test, not a repeat of the first"
