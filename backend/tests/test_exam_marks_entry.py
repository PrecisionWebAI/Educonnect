"""Exam module, Phase 5: marks entry, publication, corrections and the trail they leave.

What these scenarios pin (see `plan/service.py`, `plan/marks_text.py`):

1. **the sheet** - one row per child of the section; each row is judged by the paper's **own**
   pass line (marks or grade) and its **own** copy of the grading ladder, and an absent
   child has no percentage and is neither pass nor fail (zero is a score, absence is not);
2. **a mark cannot lie** - above the total, below zero, or for another section: refused;
3. **each mark belongs to an enrollment** of the exam's session year;
4. **publishing one paper does not close the exam** - another section's paper still takes
   marks, and the exam reads "published" only when every paper is out;
5. **a family hears its own child's marks** - never the class's - in the school's display
   mode, and an absent child hears "Absent";
6. **a correction says what changed**, is audited (who, when, from what to what, why), and
   the trail is readable by the people who run the paper but not by a family;
7. **who may enter marks** - the subject teacher, leadership, and (class test only) the
   class teacher; a cancelled exam takes none.

Runs under pytest.
"""

from tests.exam_helpers import publish
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.exams.models import (
    Exam,
    GradeScale,
    Mark,
    MarksAudit,
)
from app.domains.academic.classroom.exams.models import ExamPaper
from app.domains.academic.classroom.exams.plan import class_test, school_exam, service
from app.domains.academic.classroom.exams.plan.schemas import (
    ClassTestCreateIn,
    MarkChangeIn,
    MarkEntryIn,
    MarksSaveIn,
    SchoolExamCreateIn,
    SchoolExamRowIn,
)
from app.domains.academic.classroom.students.models import Enrollment
from app.domains.admin.settings import values as setting_values
from app.domains.auth.models import UserRole
from app.domains.main.notifications.models import Notification
from tests.test_classroom_exams import _role, _student, _teacher
from tests.test_exam_class_test import heard, world

DAY = date(2026, 12, 5)


# ---------------------------------------------------------------- helpers


def make_test(session, data, user=None, **over):
    base = dict(
        classroom_subject_id=data["maths"].id,
        section_ids=[data["room"].id],
        exam_date=DAY,
        total_marks=Decimal("50"),
    )
    base.update(over)
    exam = class_test.create_class_test(
        session, ClassTestCreateIn(**base), user or data["meera"]
    )
    # A new paper's Grade column starts as NA; these scenarios judge the ladder's grade.
    for read in exam.papers:
        stored = session.get(ExamPaper, read.id)
        stored.grade_mode = "auto"
        session.add(stored)
    session.commit()
    return exam


def entry(student, marks=None, absent=False):
    return MarkEntryIn(
        student_id=student.id,
        marks_obtained=None if marks is None else Decimal(str(marks)),
        absent=absent,
    )


def save(session, paper_id, entries, user):
    return service.save_marks(session, paper_id, MarksSaveIn(entries=entries), user)


def row_of(rows, student):
    return next(r for r in rows if r.student_id == student.id)


def told(session, event, user_id):
    return [
        n
        for n in session.exec(
            select(Notification).where(
                Notification.event_type == event, Notification.user_id == user_id
            )
        ).all()
    ]


# ------------------------------------------------------------------- the sheet


def test_every_child_of_the_section_is_a_row_judged_by_the_papers_own_pass_line():
    session, data = world()
    paper = make_test(session, data).papers[0]
    saved = save(
        session,
        paper.id,
        [
            entry(data["aarav"], 45),
            entry(data["kabir"], 10),
            entry(data["ishaan"], absent=True),
        ],
        data["meera"],
    )
    rows = saved.rows
    assert len(rows) == 4, "one row per child of the section, marked or not"

    aarav = row_of(rows, data["aarav"])
    assert aarav.percentage == Decimal("90.00") and aarav.grade == "A1"
    assert aarav.passed is True
    kabir = row_of(rows, data["kabir"])
    assert kabir.percentage == Decimal("20.00") and kabir.passed is False
    ishaan = row_of(rows, data["ishaan"])
    assert ishaan.absent is True
    assert ishaan.percentage is None and ishaan.grade is None
    assert ishaan.passed is None, "an absence is neither a pass nor a fail"
    dev = row_of(rows, data["dev"])
    assert dev.marks_obtained is None and dev.passed is None, "not marked yet"


def test_zero_is_a_score_and_a_fail_not_an_absence():
    session, data = world()
    paper = make_test(session, data).papers[0]
    rows = save(session, paper.id, [entry(data["aarav"], 0)], data["meera"]).rows
    aarav = row_of(rows, data["aarav"])
    assert aarav.absent is False and aarav.percentage == Decimal("0.00")
    assert aarav.passed is False


def test_a_grade_based_pass_line_passes_at_the_grades_own_percentage():
    session, data = world()
    paper = make_test(
        session, data, pass_mode="grade", passing_grade="D"
    ).papers[0]
    rows = save(
        session,
        paper.id,
        [entry(data["aarav"], 17), entry(data["kabir"], 16)],
        data["meera"],
    ).rows
    assert row_of(rows, data["aarav"]).passed is True, "34% reaches D (33%)"
    assert row_of(rows, data["kabir"]).passed is False, "32% does not"


def test_a_paper_keeps_its_own_ladder_when_the_schools_changes_later():
    session, data = world()
    paper = make_test(session, data).papers[0]
    session.add(GradeScale(min_percent=Decimal("0"), grade="Z"))
    session.commit()
    rows = save(session, paper.id, [entry(data["aarav"], 45)], data["meera"]).rows
    assert row_of(rows, data["aarav"]).grade == "A1", "judged by the ladder it was set with"


def test_the_paper_read_carries_its_ladder_for_a_live_grade_on_screen():
    session, data = world()
    exam = make_test(session, data)
    scale = exam.papers[0].grading_scale
    assert [r.grade for r in scale][:2] == ["A1", "A2"]
    assert scale[-1].min_percent == Decimal("0")


# ---------------------------------------------------------------- validation


@pytest.mark.parametrize("bad", [51, -1])
def test_a_mark_above_the_total_or_below_zero_is_refused(bad):
    session, data = world()
    paper = make_test(session, data).papers[0]
    with pytest.raises(HTTPException) as caught:
        save(session, paper.id, [entry(data["aarav"], bad)], data["meera"])
    assert caught.value.status_code == 422
    assert session.exec(select(Mark)).all() == []


def test_a_child_of_another_section_cannot_be_marked_on_this_paper():
    session, data = world()
    paper = make_test(session, data).papers[0]
    stranger = _student(session, "zoya khan", "P5-9", data["other_room"])
    with pytest.raises(HTTPException) as caught:
        save(session, paper.id, [entry(stranger, 10)], data["meera"])
    assert caught.value.status_code == 422


# ------------------------------------------------------------------ enrollment


def test_each_mark_belongs_to_the_childs_enrollment_of_the_exams_year():
    session, data = world()
    exam = make_test(session, data)
    save(session, exam.papers[0].id, [entry(data["aarav"], 40)], data["meera"])
    mark = session.exec(select(Mark)).first()
    enrolment = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == data["aarav"].id,
            Enrollment.academic_year_id == exam.academic_year_id,
        )
    ).first()
    assert enrolment is not None
    assert mark.enrollment_id == enrolment.id


# ---------------------------------------------------- publishing one paper


def test_publishing_one_section_does_not_close_the_other_sections_marks():
    session, data = world()
    zoya = _student(session, "zoya khan", "P5-9", data["other_room"])
    exam = make_test(
        session,
        data,
        user=data["office"],
        section_ids=[data["room"].id, data["other_room"].id],
        taken_by_employee_id=data["employee"].id,
    )
    paper_a = next(p for p in exam.papers if p.classroom_id == data["room"].id)
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)

    save(session, paper_a.id, [entry(data["aarav"], 40)], data["meera"])
    publish(session, paper_a.id, data["meera"])
    assert session.get(Exam, exam.id).status == "marks_entry", "9-B is still to come"

    save(session, paper_b.id, [entry(zoya, 30)], data["office"])  # not refused
    publish(session, paper_b.id, data["office"])
    assert session.get(Exam, exam.id).status == "published", "every paper is out"


def test_publishing_the_date_sheet_never_drags_an_exam_back_a_status():
    session, data = world()
    exam = school_exam.create_school_exam(
        session,
        SchoolExamCreateIn(
            classroom_id=data["room"].id,
            exam_type="unit_test",
            rows=[
                SchoolExamRowIn(
                    classroom_subject_id=data["maths"].id,
                    exam_date=DAY,
                    total_marks=Decimal("100"),
                )
            ],
        ),
        data["meera"],
    )
    save(session, exam.papers[0].id, [entry(data["aarav"], 70)], data["meera"])
    assert session.get(Exam, exam.id).status == "marks_entry"
    school_exam.publish_date_sheet(session, exam.id, data["meera"])
    assert session.get(Exam, exam.id).status == "marks_entry"


# ------------------------------------------------------------- notifications


def test_each_family_hears_only_its_own_childs_marks():
    session, data = world()
    paper = make_test(session, data).papers[0]
    save(
        session,
        paper.id,
        [
            entry(data["aarav"], 45),
            entry(data["kabir"], 10),
            entry(data["ishaan"], absent=True),
            entry(data["dev"], 30),
        ],
        data["meera"],
    )
    assert heard(session, service.EVENT_EXAM_PUBLISHED) == [], "a draft tells nobody"
    publish(session, paper.id, data["meera"])

    aarav = told(session, service.EVENT_EXAM_PUBLISHED, data["aarav_parent"].id)
    assert len(aarav) == 1
    assert "45/50 (90%)" in aarav[0].body and "Grade A1" in aarav[0].body
    assert "Pass" in aarav[0].body
    assert "10/50" not in aarav[0].body, "never another child's marks"

    kabir = told(session, service.EVENT_EXAM_PUBLISHED, data["kabir_parent"].id)
    assert "10/50 (20%)" in kabir[0].body and "Fail" in kabir[0].body

    ishaan = told(session, service.EVENT_EXAM_PUBLISHED, data["ishaan_parent"].id)
    assert "Absent" in ishaan[0].body

    dev = told(session, service.EVENT_EXAM_PUBLISHED, data["dev_parent"].id)
    assert len(dev) == 1 and "30/50" in dev[0].body


def test_a_paper_cannot_be_published_while_a_child_has_no_mark_and_is_not_absent():
    session, data = world()
    paper = make_test(session, data).papers[0]
    save(session, paper.id, [entry(data["aarav"], 45)], data["meera"])
    with pytest.raises(HTTPException) as caught:
        service.publish_paper(session, paper.id, data["meera"])
    assert caught.value.status_code == 422
    assert "no marks yet" in caught.value.detail and "kabir singh" in caught.value.detail
    assert heard(session, service.EVENT_EXAM_PUBLISHED) == [], "nobody was told"

    # saving a partial sheet is always allowed; once the rest is in, it publishes
    save(
        session,
        paper.id,
        [entry(data["kabir"], 10), entry(data["ishaan"], absent=True), entry(data["dev"], 0)],
        data["meera"],
    )
    assert service.publish_paper(session, paper.id, data["meera"]).published_at is not None


def test_the_message_follows_the_schools_display_mode():
    session, data = world()
    paper = make_test(session, data).papers[0]
    setting_values.set_value(session, "exam.display_mode", "grades")
    save(session, paper.id, [entry(data["aarav"], 45)], data["meera"])
    publish(session, paper.id, data["meera"])
    body = told(session, service.EVENT_EXAM_PUBLISHED, data["aarav_parent"].id)[0].body
    assert "Grade A1" in body and "45/50" not in body

    paper2 = make_test(session, data, exam_date=date(2026, 12, 9), confirm_duplicate=True).papers[0]
    setting_values.set_value(session, "exam.display_mode", "marks")
    save(session, paper2.id, [entry(data["aarav"], 45)], data["meera"])
    publish(session, paper2.id, data["meera"])
    latest = told(session, service.EVENT_EXAM_PUBLISHED, data["aarav_parent"].id)[-1].body
    assert "45/50" in latest and "Grade" not in latest


# ---------------------------------------------------------------- corrections


def published_test(session, data):
    paper = make_test(session, data).papers[0]
    save(session, paper.id, [entry(data["aarav"], 45)], data["meera"])
    publish(session, paper.id, data["meera"])
    return paper


def test_a_correction_says_what_changed_and_leaves_a_trail():
    session, data = world()
    paper = published_test(session, data)
    row = service.change_mark(
        session,
        paper.id,
        data["aarav"].id,
        MarkChangeIn(marks_obtained=Decimal("10"), reason="Re-totalled"),
        data["meera"],
    )
    assert row.marks_obtained == Decimal("10.00") and row.passed is False
    assert row.changed_after_publish is True

    body = told(session, service.EVENT_EXAM_MARK_CHANGED, data["aarav_parent"].id)[0].body
    assert "changed from 45/50 (90%)" in body and "to 10/50 (20%)" in body

    trail = service.mark_history(session, paper.id, data["meera"])
    assert len(trail) == 1
    item = trail[0]
    assert item.student_name == "aarav sharma"
    assert (item.old_value, item.new_value) == (Decimal("45.00"), Decimal("10.00"))
    assert item.reason == "Re-totalled"
    assert item.changed_by == data["meera"].full_name
    assert session.exec(select(MarksAudit)).first() is not None


def test_the_trail_is_for_the_people_who_run_the_paper_not_for_a_family():
    session, data = world()
    paper = published_test(session, data)
    for who in (data["aarav_parent"], data["outsider"]):
        with pytest.raises(HTTPException) as caught:
            service.mark_history(session, paper.id, who)
        assert caught.value.status_code == 403
    assert service.mark_history(session, paper.id, data["principal"]) == []


def test_a_correction_to_the_same_mark_is_refused_and_a_draft_is_not_corrected():
    session, data = world()
    paper = published_test(session, data)
    with pytest.raises(HTTPException) as same:
        service.change_mark(
            session, paper.id, data["aarav"].id,
            MarkChangeIn(marks_obtained=Decimal("45")), data["meera"],
        )
    assert same.value.status_code == 409

    draft = make_test(session, data, exam_date=date(2026, 12, 9), confirm_duplicate=True).papers[0]
    save(session, draft.id, [entry(data["aarav"], 10)], data["meera"])
    with pytest.raises(HTTPException) as early:
        service.change_mark(
            session, draft.id, data["aarav"].id,
            MarkChangeIn(marks_obtained=Decimal("12")), data["meera"],
        )
    assert early.value.status_code == 409


# --------------------------------------------------------------- who may enter


def test_the_class_teacher_enters_marks_on_a_class_test_but_not_a_subject_teacher_of_another():
    session, data = world()
    jaya, jaya_user = _teacher(session, "jaya5@test", "EMP-P5-J")
    session.add(UserRole(user_id=jaya_user.id, role_id=_role(session, "teacher").id))
    data["other_room"].class_teacher_id = jaya.id
    session.add(data["other_room"])
    session.commit()
    zoya = _student(session, "zoya khan", "P5-9", data["other_room"])
    exam = make_test(
        session,
        data,
        user=data["office"],
        section_ids=[data["room"].id, data["other_room"].id],
        taken_by_employee_id=data["employee"].id,
    )
    paper_b = next(p for p in exam.papers if p.classroom_id == data["other_room"].id)
    assert save(session, paper_b.id, [entry(zoya, 30)], jaya_user).written == 1

    with pytest.raises(HTTPException) as caught:
        save(session, paper_b.id, [entry(zoya, 31)], data["outsider"])
    assert caught.value.status_code == 403


def test_a_cancelled_exam_takes_no_marks():
    session, data = world()
    exam = make_test(session, data)
    class_test.cancel_class_test(session, exam.id, data["meera"])
    with pytest.raises(HTTPException) as caught:
        save(session, exam.papers[0].id, [entry(data["aarav"], 10)], data["meera"])
    assert caught.value.status_code == 409
    assert "cancelled" in caught.value.detail


def test_the_grade_column_can_be_na_auto_or_manual_and_manual_needs_a_grade_for_every_score():
    session, data = world()
    paper = make_test(session, data).papers[0]

    # auto: the ladder decides; na: no grade at all
    out = service.save_marks(
        session, paper.id, MarksSaveIn(entries=[entry(data["aarav"], 45)], grade_mode="na"),
        data["meera"],
    )
    assert row_of(out.rows, data["aarav"]).grade is None
    out = service.save_marks(
        session, paper.id, MarksSaveIn(entries=[entry(data["aarav"], 45)], grade_mode="auto"),
        data["meera"],
    )
    assert row_of(out.rows, data["aarav"]).grade == "A1"

    # manual: a scored child cannot be saved without a grade; an absent one needs none
    with pytest.raises(HTTPException) as caught:
        service.save_marks(
            session, paper.id, MarksSaveIn(entries=[entry(data["aarav"], 45)], grade_mode="manual"),
            data["meera"],
        )
    assert caught.value.status_code == 422 and "Enter a grade" in caught.value.detail
    session.rollback()
    given = MarkEntryIn(student_id=data["aarav"].id, marks_obtained=Decimal("45"), grade="EX")
    out = service.save_marks(
        session, paper.id,
        MarksSaveIn(entries=[given, entry(data["kabir"], absent=True)], grade_mode="manual"),
        data["meera"],
    )
    assert row_of(out.rows, data["aarav"]).grade == "EX"
    assert row_of(out.rows, data["kabir"]).grade is None

    # a wrong mode is refused
    with pytest.raises(HTTPException):
        service.save_marks(session, paper.id, MarksSaveIn(entries=[], grade_mode="weird"), data["meera"])


def test_the_grade_column_can_be_changed_after_publishing_manual_needs_every_grade():
    from app.domains.academic.classroom.exams.plan.schemas import GradeEntryIn, GradeModeIn

    session, data = world()
    paper = make_test(session, data).papers[0]
    save(session, paper.id, [entry(data["aarav"], 45), entry(data["kabir"], 20)], data["meera"])

    # before publishing, Manual needs a grade for every scored child
    with pytest.raises(HTTPException) as caught:
        service.set_grade_mode(session, paper.id, GradeModeIn(grade_mode="manual"), data["meera"])
    assert caught.value.status_code == 422 and "Enter a grade" in caught.value.detail
    session.rollback()

    publish(session, paper.id, data["meera"])
    # after publishing: NA <-> Auto at once
    rows = service.set_grade_mode(session, paper.id, GradeModeIn(grade_mode="auto"), data["meera"])
    assert row_of(rows, data["aarav"]).grade == "A1"
    rows = service.set_grade_mode(session, paper.id, GradeModeIn(grade_mode="na"), data["meera"])
    assert row_of(rows, data["aarav"]).grade is None

    # Manual after publishing needs every scored child's grade, like before it
    with pytest.raises(HTTPException) as caught:
        service.set_grade_mode(
            session,
            paper.id,
            GradeModeIn(
                grade_mode="manual",
                grades=[GradeEntryIn(student_id=data["aarav"].id, grade="EX")],
            ),
            data["meera"],
        )
    assert caught.value.status_code == 422 and "Enter a grade" in caught.value.detail
    session.rollback()
    rows = service.set_grade_mode(
        session,
        paper.id,
        GradeModeIn(
            grade_mode="manual",
            grades=[
                GradeEntryIn(student_id=data["aarav"].id, grade="EX"),
                GradeEntryIn(student_id=data["kabir"].id, grade="WK"),
            ],
        ),
        data["meera"],
    )
    assert row_of(rows, data["aarav"]).grade == "EX"
    # once Manual, one grade can be edited on its own
    rows = service.set_grade_mode(
        session,
        paper.id,
        GradeModeIn(
            grade_mode="manual",
            grades=[GradeEntryIn(student_id=data["kabir"].id, grade="FR")],
        ),
        data["meera"],
    )
    assert row_of(rows, data["kabir"]).grade == "FR"
    assert row_of(rows, data["aarav"]).grade == "EX"

    # a stranger cannot
    with pytest.raises(HTTPException):
        service.set_grade_mode(session, paper.id, GradeModeIn(grade_mode="auto"), data["aarav_parent"])


def test_a_manual_grade_follows_the_same_rule_as_a_custom_passing_grade():
    from app.domains.academic.classroom.exams.plan.schemas import GradeEntryIn, GradeModeIn

    session, data = world()
    paper = make_test(session, data).papers[0]
    for bad in ("EXC", "1A", "A!"):
        with pytest.raises(HTTPException) as caught:
            service.save_marks(
                session,
                paper.id,
                MarksSaveIn(
                    entries=[MarkEntryIn(student_id=data["aarav"].id, marks_obtained=Decimal("45"), grade=bad)],
                    grade_mode="manual",
                ),
                data["meera"],
            )
        assert caught.value.status_code == 422 and "capital letter first" in caught.value.detail
        session.rollback()
    out = service.save_marks(
        session,
        paper.id,
        MarksSaveIn(
            entries=[MarkEntryIn(student_id=data["aarav"].id, marks_obtained=Decimal("45"), grade="b2")],
            grade_mode="manual",
        ),
        data["meera"],
    )
    assert row_of(out.rows, data["aarav"]).grade == "B2", "kept in capitals"
