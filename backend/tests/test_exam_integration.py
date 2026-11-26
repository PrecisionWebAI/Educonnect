"""Exam module, Phase 8: the exam module with the rest of the school.

What these scenarios pin:

1. **the reminder** (`service.reminder_job`) - decided **per paper**, not per exam: a class test
   is reminded the day before, a School Exam only once its date sheet is published, a
   cancelled or already-published paper never, and the Science paper two days after Maths
   marks were entered is still reminded. The teacher who takes it is reminded too (the
   picked one, else the assigned one). Once per paper however often the job ticks;
2. **promotion and de-promotion** - the marks of the year being undone are counted in the
   warning and deleted with it (with their audit trail), the previous year's marks stay,
   and a mark tied to an enrollment goes with that enrollment even when its exam has no
   year (it must never point at a deleted row).

Runs under pytest.
"""

from tests.exam_helpers import publish
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.exams.models import (
    Exam,
    ExamPaper,
    Mark,
    MarksAudit,
)
from app.domains.academic.classroom.exams.plan import class_test, school_exam, service
from app.domains.academic.classroom.exams.plan.schemas import (
    SchoolExamCreateIn,
    SchoolExamRowIn,
)
from app.domains.academic.classroom.students.promotion import direct
from app.domains.auth.models import UserRole
from app.domains.main.notifications.models import Notification
from tests.test_classroom_exams import _role, _teacher
from tests.test_classroom_students import _student
from tests.test_classroom_students import memory_session as students_session
from tests.test_exam_class_test import world
from tests.test_exam_marks_entry import entry, make_test, save
from tests.test_student_promotion import _enrollment, _setup

D = Decimal


def tomorrow() -> date:
    """The job asks about **today's** tomorrow, so papers must be dated that way."""
    return datetime.utcnow().date() + timedelta(days=1)


def reminders(session, user_id=None):
    statement = select(Notification).where(Notification.event_type == "exam.reminder")
    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)
    return list(session.exec(statement).all())


def sheet(session, data, rows, **over):
    return school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type=over.pop("exam_type", "unit_test"),
            rows=rows,
            **over,
        ),
        data["meera"],
    )


def row(course, day, total="100"):
    return SchoolExamRowIn(
        classroom_subject_id=course.id, exam_date=day, total_marks=D(total)
    )


# ------------------------------------------------------------------ reminders


def test_a_class_test_is_reminded_the_day_before_to_families_and_the_teacher_once():
    session, data = world()
    make_test(session, data, exam_date=tomorrow(), family_note="Bring a ruler")
    assert reminders(session) == []

    assert service.reminder_job(session) >= 1
    family = reminders(session, data["aarav_parent"].id)
    assert len(family) == 1
    assert family[0].title == "Class Test: Mathematics is tomorrow"
    assert "Bring a ruler" in family[0].body
    teacher = reminders(session, data["meera"].id)
    assert len(teacher) == 1 and "you take it tomorrow" in teacher[0].title

    assert service.reminder_job(session) == 0, "once per paper, however often it ticks"


def test_the_teacher_who_takes_it_is_reminded_not_the_assigned_one_when_someone_covers():
    session, data = world()
    cover, cover_user = _teacher(session, "cover8@test", "EMP-P8-C")
    session.add(UserRole(user_id=cover_user.id, role_id=_role(session, "teacher").id))
    session.commit()
    make_test(
        session, data, exam_date=tomorrow(), taken_by_employee_id=cover.id
    )
    service.reminder_job(session)
    assert len(reminders(session, cover_user.id)) == 1
    assert reminders(session, data["meera"].id) == [], "Meera is not taking it"


def test_a_cancelled_class_test_is_not_reminded():
    session, data = world()
    exam = make_test(session, data, exam_date=tomorrow())
    class_test.cancel_class_test(session, exam.id, data["meera"])
    assert service.reminder_job(session) == 0
    assert reminders(session) == []


def test_a_paper_whose_marks_are_already_out_is_history_not_a_reminder():
    session, data = world()
    exam = make_test(session, data, exam_date=tomorrow())
    paper = exam.papers[0]
    save(session, paper.id, [entry(data["aarav"], 40)], data["meera"])
    publish(session, paper.id, data["meera"])
    assert service.reminder_job(session) == 0


def test_a_school_exam_is_reminded_only_once_its_date_sheet_is_published():
    session, data = world()
    exam = sheet(session, data, [row(data["maths"], tomorrow())])
    assert exam.status == "draft"
    assert service.reminder_job(session) == 0, "a draft date sheet is nobody's business"

    school_exam.publish_date_sheet(session, exam.id, data["meera"])
    assert service.reminder_job(session) >= 1
    family = reminders(session, data["aarav_parent"].id)
    assert len(family) == 1 and "Unit Test" in family[0].title
    assert "tomorrow" in family[0].body


def test_the_next_subject_is_still_reminded_after_the_first_has_marks():
    session, data = world()
    exam = sheet(
        session,
        data,
        [
            row(data["maths"], tomorrow() - timedelta(days=3)),
            row(data["science"], tomorrow()),
        ],
    )
    school_exam.publish_date_sheet(session, exam.id, data["meera"])
    maths = next(p for p in exam.papers if p.classroom_subject_id == data["maths"].id)
    save(session, maths.id, [entry(data["aarav"], 80)], data["meera"])
    assert session.get(Exam, exam.id).status == "marks_entry"

    assert service.reminder_job(session) >= 1, "Science is tomorrow, whatever Maths did"
    assert any("Science" in n.title for n in reminders(session, data["aarav_parent"].id))


# ----------------------------------------------------------------- promotion


def _exam_in(session, year, room, student, enrollment, *, with_year=True, audit=False):
    """A class test of `year` in `room`, with one mark for `student` tied to `enrollment`."""
    course = ClassroomSubject(
        classroom_id=room.id, name="Mathematics", academic_year_id=year.id
    )
    session.add(course)
    session.flush()
    exam = Exam(
        name="Class Test - Mathematics",
        exam_type="class_test",
        scope="class",
        class_id=room.class_id,
        academic_year_id=year.id if with_year else None,
        status="scheduled",
    )
    session.add(exam)
    session.flush()
    paper = ExamPaper(
        exam_id=exam.id,
        classroom_subject_id=course.id,
        exam_date=date(2027, 6, 1),
        max_marks=D("50"),
    )
    session.add(paper)
    session.flush()
    mark = Mark(
        student_id=student.id,
        exam_paper_id=paper.id,
        marks_obtained=D("40"),
        enrollment_id=enrollment.id,
    )
    session.add(mark)
    session.flush()
    if audit:
        session.add(
            MarksAudit(
                marks_id=mark.id, old_value=D("30"), new_value=D("40"), reason="re-total"
            )
        )
    session.commit()
    return exam, paper, mark


def test_undoing_a_promotion_counts_and_deletes_that_years_marks_and_keeps_the_old_ones():
    with students_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-8", w["rooms"][("Class 6", "A")])
        old = _enrollment(session, a, w["current"])
        _, _, old_mark = _exam_in(
            session, w["current"], w["rooms"][("Class 6", "A")], a, old
        )

        direct.promote(session, [a.id], None)
        new = _enrollment(session, a, w["next"])
        _, _, new_mark = _exam_in(
            session, w["next"], w["rooms"][("Class 7", "A")], a, new, audit=True
        )

        preview = direct.preview_depromote(session, [a.id])
        assert preview.marks == 1, "only the year being undone"
        with pytest.raises(HTTPException) as refused:
            direct.depromote(session, [a.id], confirmed=False)
        assert refused.value.status_code == 409 and "1 marks" in refused.value.detail
        assert session.get(Mark, new_mark.id) is not None, "nothing changed yet"

        assert direct.depromote(session, [a.id], confirmed=True).done == 1
        assert session.get(Mark, new_mark.id) is None
        assert session.exec(select(MarksAudit)).all() == [], "its trail goes with it"
        assert _enrollment(session, a, w["next"]) is None
        kept = session.get(Mark, old_mark.id)
        assert kept is not None and kept.enrollment_id == old.id, "last year's marks stay"


def test_a_mark_tied_to_an_enrollment_goes_with_it_even_when_its_exam_has_no_year():
    with students_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-9", w["rooms"][("Class 6", "A")])
        direct.promote(session, [a.id], None)
        new = _enrollment(session, a, w["next"])
        _, _, mark = _exam_in(
            session, w["next"], w["rooms"][("Class 7", "A")], a, new, with_year=False
        )

        assert direct.preview_depromote(session, [a.id]).marks == 1
        direct.depromote(session, [a.id], confirmed=True)
        assert session.get(Mark, mark.id) is None, "no mark left pointing at a deleted row"
        assert _enrollment(session, a, w["next"]) is None
