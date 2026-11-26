"""Exam module, Phase 3: scheduling a class test.

What these scenarios pin (see `plan/class_test.py`):

1. **who may schedule** - the subject teacher, the class teacher, or leadership; anybody
   else is a `403`;
2. **one class, existing courses** - sections of different classes cannot share a test,
   and a section without the subject is refused rather than given one;
3. **who takes it** - the assigned teacher by default; someone else is *temporary*
   (derived live); a section with nobody assigned needs a teacher picked;
4. **its own pass line** - marks (33% default) or a passing grade, custom grades allowed;
5. **a duplicate is a warning** - `409 DUPLICATE_EXAM` with the existing test, then
   "create anyway";
6. **what a notification says** - a new date is a reschedule; any other edit names what
   changed; a changed note only says the note changed; no change tells nobody;
7. **sections can be edited** - added freely, removed only while they have no marks;
8. **delete vs cancel** - a test with marks is cancelled, never deleted; both tell families.

Runs under pytest.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.exams.plan import class_test, service
from app.domains.academic.classroom.exams.plan.schemas import (
    ClassTestCreateIn,
    ClassTestUpdateIn,
)
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.auth.models import UserRole
from app.domains.main.notifications.models import Notification
from tests.course_support import section_subject
from tests.test_classroom_exams import (
    _role,
    _room,
    _teacher,
    memory_session,
    seed,
)

DAY = date(2026, 12, 5)
NEXT_DAY = date(2026, 12, 8)


# ---------------------------------------------------------------- helpers


def world():
    """The Phase 7 school, with Meera made a *teaching* login (so she can be picked)."""
    session = memory_session()
    data = seed(session)
    session.add(
        UserRole(user_id=data["meera"].id, role_id=_role(session, "teacher").id)
    )
    session.commit()
    return session, data


def create_in(data, **over):
    base = dict(
        classroom_subject_id=data["maths"].id,
        section_ids=[data["room"].id],
        exam_date=DAY,
        total_marks=Decimal("50"),
    )
    base.update(over)
    return ClassTestCreateIn(**base)


def heard(session, event):
    rows = session.exec(
        select(Notification).where(Notification.event_type == event)
    ).all()
    return rows


def parents(data):
    return {
        data[key].id
        for key in ("aarav_parent", "kabir_parent", "ishaan_parent", "dev_parent")
    }


def code_of(caught):
    detail = caught.value.detail
    return detail.get("code") if isinstance(detail, dict) else None


# ----------------------------------------------------------- scheduling


def test_the_subject_teacher_schedules_a_test_and_families_hear_once():
    session, data = world()
    out = class_test.create_class_test(
        session,
        create_in(data, family_note="Bring a ruler"),
        data["meera"],
    )
    assert out.exam_type == "class_test" and out.scope == "class"
    assert out.status == "scheduled"
    assert out.family_note == "Bring a ruler"
    assert len(out.papers) == 1
    paper = out.papers[0]
    assert paper.exam_date == DAY and paper.max_marks == Decimal("50")
    # The pass line starts at 33% of 50 and is the paper's own.
    assert paper.pass_mode == "marks" and paper.passing_marks == Decimal("16.50")
    assert paper.pass_percent == Decimal("33.00")
    # Nobody was named, so the assigned teacher takes it - not a temporary teacher.
    assert paper.taken_by_employee_id == data["employee"].id
    assert paper.is_temporary is False

    told = heard(session, class_test.EVENT_SCHEDULED)
    assert {row.user_id for row in told} >= {
        data["aarav_parent"].id,
        data["kabir_parent"].id,
    }
    assert any("Bring a ruler" in row.body for row in told), "the note goes with it"
    assert any("Mathematics" in row.title for row in told)


def test_a_stranger_may_not_schedule_but_leadership_and_the_class_teacher_may():
    session, data = world()
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(session, create_in(data), data["outsider"])
    assert caught.value.status_code == 403

    class_test.create_class_test(session, create_in(data), data["principal"])
    class_test.create_class_test(
        session, create_in(data, exam_date=NEXT_DAY), data["office"]
    )

    # A class teacher who does not hold the subject may still schedule it.
    jaya, jaya_user = _teacher(session, "jaya@test", "EMP-P3-J")
    session.add(UserRole(user_id=jaya_user.id, role_id=_role(session, "teacher").id))
    data["other_room"].class_teacher_id = jaya.id
    session.add(data["other_room"])
    session.commit()
    b_maths = session.exec(
        select(ClassroomSubject).where(
            ClassroomSubject.classroom_id == data["other_room"].id
        )
    ).first()
    out = class_test.create_class_test(
        session,
        create_in(
            data,
            classroom_subject_id=b_maths.id,
            section_ids=[data["other_room"].id],
            taken_by_employee_id=jaya.id,
        ),
        jaya_user,
    )
    assert out.papers[0].classroom_id == data["other_room"].id


def test_a_subject_that_does_not_exist_is_refused():
    session, data = world()
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session, create_in(data, classroom_subject_id=uuid4()), data["office"]
        )
    assert caught.value.status_code == 404


# ------------------------------------------------------------- sections


def test_one_test_sits_in_several_sections_of_the_same_class():
    session, data = world()
    # 9-B's Mathematics has nobody assigned, so someone must be picked to take it.
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session,
            create_in(data, section_ids=[data["room"].id, data["other_room"].id]),
            data["office"],
        )
    assert caught.value.status_code == 422
    assert "Pick who takes the test" in caught.value.detail

    out = class_test.create_class_test(
        session,
        create_in(
            data,
            section_ids=[data["room"].id, data["other_room"].id],
            taken_by_employee_id=data["employee"].id,
        ),
        data["office"],
    )
    assert {p.classroom_id for p in out.papers} == {
        data["room"].id,
        data["other_room"].id,
    }
    by_room = {p.classroom_id: p for p in out.papers}
    # Meera is 9-A's own teacher; for 9-B (nobody assigned) she is the temporary one.
    assert by_room[data["room"].id].is_temporary is False
    assert by_room[data["other_room"].id].is_temporary is True
    assert by_room[data["other_room"].id].assigned_teacher_id is None


def test_sections_of_two_different_classes_cannot_share_a_test():
    session, data = world()
    tenth = _room(session, "Class 10", "A", 10)
    section_subject(session, tenth.id, "Mathematics", code="MATH")
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session,
            create_in(
                data,
                section_ids=[data["room"].id, tenth.id],
                taken_by_employee_id=data["employee"].id,
            ),
            data["office"],
        )
    assert caught.value.status_code == 422
    assert "same class" in caught.value.detail


def test_a_section_without_the_subject_is_refused_not_given_one():
    session, data = world()
    # Science exists in 9-A only.
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session,
            create_in(
                data,
                classroom_subject_id=data["science"].id,
                section_ids=[data["room"].id, data["other_room"].id],
                taken_by_employee_id=data["employee"].id,
            ),
            data["office"],
        )
    assert caught.value.status_code == 422
    assert "no subject named" in caught.value.detail


# -------------------------------------------------------------- pass line


def test_a_passing_grade_with_its_own_custom_percentage_is_kept_on_the_paper():
    session, data = world()
    out = class_test.create_class_test(
        session,
        create_in(
            data,
            pass_mode="grade",
            passing_grade="P",
            custom_min_percent=Decimal("35"),
        ),
        data["meera"],
    )
    paper = out.papers[0]
    assert paper.pass_mode == "grade" and paper.passing_grade == "P"
    assert paper.pass_percent == Decimal("35.00")
    stored = session.exec(select(ExamPaper)).first()
    assert len(stored.grading_scale) == 9, "the school's 8 grades plus this test's own"


def test_a_pass_line_that_cannot_be_true_stops_the_save():
    session, data = world()
    for bad in (
        dict(pass_mode="marks", passing_marks=Decimal("51")),
        dict(pass_mode="grade"),
        dict(pass_mode="grade", passing_grade="PQR"),
        dict(pass_mode="percent"),
    ):
        with pytest.raises(HTTPException) as caught:
            class_test.create_class_test(session, create_in(data, **bad), data["meera"])
        assert caught.value.status_code == 422, bad
    assert session.exec(select(Exam)).all() == [], "nothing was half-saved"


def test_a_taker_who_is_not_teaching_is_refused():
    session, data = world()
    nobody, _ = _teacher(session, "nobody@test", "EMP-P3-N")  # no teaching role
    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session,
            create_in(data, taken_by_employee_id=nobody.id),
            data["office"],
        )
    assert caught.value.status_code == 422
    assert "teaching now" in caught.value.detail


def test_someone_other_than_the_assigned_teacher_is_a_temporary_teacher():
    session, data = world()
    cover, cover_user = _teacher(session, "cover@test", "EMP-P3-C")
    session.add(UserRole(user_id=cover_user.id, role_id=_role(session, "teacher").id))
    session.commit()
    out = class_test.create_class_test(
        session, create_in(data, taken_by_employee_id=cover.id), data["office"]
    )
    paper = out.papers[0]
    assert paper.taken_by_employee_id == cover.id
    assert paper.is_temporary is True
    assert paper.assigned_teacher_id == data["employee"].id


# ------------------------------------------------------------- duplicates


def test_a_duplicate_is_a_warning_with_the_existing_test_then_create_anyway():
    session, data = world()
    class_test.create_class_test(session, create_in(data), data["meera"])

    with pytest.raises(HTTPException) as caught:
        class_test.create_class_test(
            session, create_in(data, total_marks=Decimal("20")), data["meera"]
        )
    assert caught.value.status_code == 409 and code_of(caught) == "DUPLICATE_EXAM"
    existing = caught.value.detail["existing"][0]
    assert existing["subject"] == "Mathematics"
    assert Decimal(existing["total_marks"]) == Decimal("50")
    assert existing["section"] and existing["exam_date"] == DAY.isoformat()
    assert len(session.exec(select(Exam)).all()) == 1

    class_test.create_class_test(
        session,
        create_in(data, total_marks=Decimal("20"), confirm_duplicate=True),
        data["meera"],
    )
    assert len(session.exec(select(Exam)).all()) == 2


def test_a_cancelled_test_is_not_a_duplicate():
    session, data = world()
    first = class_test.create_class_test(session, create_in(data), data["meera"])
    class_test.cancel_class_test(session, first.id, data["meera"])
    class_test.create_class_test(session, create_in(data), data["meera"])  # no 409


# ----------------------------------------------------------------- editing


def test_a_new_date_is_a_reschedule_that_states_the_new_date():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(exam_date=NEXT_DAY), data["meera"]
    )
    moved = heard(session, class_test.EVENT_RESCHEDULED)
    assert moved and all("8 Dec 2026" in row.body for row in moved)
    assert not heard(session, class_test.EVENT_UPDATED)
    assert {p.exam_date for p in session.exec(select(ExamPaper)).all()} == {NEXT_DAY}


def test_any_other_edit_says_what_changed_and_is_not_a_reschedule():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(total_marks=Decimal("40")), data["meera"]
    )
    updated = heard(session, class_test.EVENT_UPDATED)
    assert updated and all("total marks 50 -> 40" in row.body for row in updated)
    assert not heard(session, class_test.EVENT_RESCHEDULED)
    paper = session.exec(select(ExamPaper)).first()
    assert paper.max_marks == Decimal("40")
    # The pass marks followed the total (33% of 40), since the teacher never set their own.
    assert paper.passing_marks == Decimal("13.20")


def test_a_teachers_own_pass_marks_survive_a_change_of_total():
    session, data = world()
    exam = class_test.create_class_test(
        session, create_in(data, passing_marks=Decimal("25")), data["meera"]
    )
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(total_marks=Decimal("60")), data["meera"]
    )
    assert session.exec(select(ExamPaper)).first().passing_marks == Decimal("25.00")


def test_a_changed_note_only_says_the_note_changed():
    session, data = world()
    exam = class_test.create_class_test(
        session, create_in(data, family_note="Bring a ruler"), data["meera"]
    )
    class_test.update_class_test(
        session, exam.id, ClassTestUpdateIn(family_note="Bring a compass"), data["meera"]
    )
    changed = heard(session, class_test.EVENT_NOTE_CHANGED)
    assert changed
    assert all("changed" in row.body for row in changed)
    assert all("compass" not in row.body for row in changed), "it does not repeat the note"
    assert not heard(session, class_test.EVENT_RESCHEDULED)
    assert not heard(session, class_test.EVENT_UPDATED)
    assert session.get(Exam, exam.id).family_note == "Bring a compass"


def test_saving_without_a_change_tells_nobody():
    session, data = world()
    exam = class_test.create_class_test(
        session, create_in(data, family_note="Bring a ruler"), data["meera"]
    )
    before = len(session.exec(select(Notification)).all())
    class_test.update_class_test(
        session,
        exam.id,
        ClassTestUpdateIn(exam_date=DAY, total_marks=Decimal("50"), family_note="Bring a ruler"),
        data["meera"],
    )
    assert len(session.exec(select(Notification)).all()) == before


def test_total_marks_cannot_go_below_a_mark_already_entered():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    paper = session.exec(select(ExamPaper)).first()
    session.add(
        Mark(
            student_id=data["aarav"].id,
            exam_paper_id=paper.id,
            marks_obtained=Decimal("45"),
        )
    )
    session.commit()
    with pytest.raises(HTTPException) as caught:
        class_test.update_class_test(
            session, exam.id, ClassTestUpdateIn(total_marks=Decimal("30")), data["meera"]
        )
    assert caught.value.status_code == 422
    assert session.exec(select(ExamPaper)).first().max_marks == Decimal("50")


def test_sections_can_be_added_and_removed_but_not_once_they_have_marks():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    both = [data["room"].id, data["other_room"].id]
    out = class_test.update_class_test(
        session,
        exam.id,
        ClassTestUpdateIn(
            section_ids=both, taken_by_employee_id=data["employee"].id
        ),
        data["office"],
    )
    assert {p.classroom_id for p in out.papers} == set(both)

    paper_a = next(p for p in out.papers if p.classroom_id == data["room"].id)
    session.add(
        Mark(
            student_id=data["aarav"].id,
            exam_paper_id=paper_a.id,
            marks_obtained=Decimal("10"),
        )
    )
    session.commit()
    with pytest.raises(HTTPException) as caught:
        class_test.update_class_test(
            session,
            exam.id,
            ClassTestUpdateIn(section_ids=[data["other_room"].id]),
            data["office"],
        )
    assert caught.value.status_code == 409 and "marks" in caught.value.detail

    out = class_test.update_class_test(
        session,
        exam.id,
        ClassTestUpdateIn(section_ids=[data["room"].id]),
        data["office"],
    )
    assert {p.classroom_id for p in out.papers} == {data["room"].id}


def test_moving_to_a_taken_date_warns_before_it_saves():
    session, data = world()
    class_test.create_class_test(session, create_in(data, exam_date=NEXT_DAY), data["meera"])
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    with pytest.raises(HTTPException) as caught:
        class_test.update_class_test(
            session, exam.id, ClassTestUpdateIn(exam_date=NEXT_DAY), data["meera"]
        )
    assert caught.value.status_code == 409 and code_of(caught) == "DUPLICATE_EXAM"
    assert session.get(Exam, exam.id) is not None
    assert {p.exam_date for p in session.exec(
        select(ExamPaper).where(ExamPaper.exam_id == exam.id)
    ).all()} == {DAY}, "nothing moved"


# ------------------------------------------------------- cancel and delete


def test_a_test_with_no_marks_can_be_deleted_and_families_are_told():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    class_test.delete_class_test(session, exam.id, data["meera"])
    assert session.exec(select(Exam)).all() == []
    assert session.exec(select(ExamPaper)).all() == []
    told = heard(session, class_test.EVENT_DELETED)
    assert told and {row.user_id for row in told} >= {data["aarav_parent"].id}


def test_a_test_with_marks_is_cancelled_never_deleted():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    paper = session.exec(select(ExamPaper)).first()
    session.add(
        Mark(
            student_id=data["aarav"].id,
            exam_paper_id=paper.id,
            marks_obtained=Decimal("30"),
        )
    )
    session.commit()
    with pytest.raises(HTTPException) as caught:
        class_test.delete_class_test(session, exam.id, data["meera"])
    assert caught.value.status_code == 409 and "Cancel it instead" in caught.value.detail

    out = class_test.cancel_class_test(session, exam.id, data["meera"])
    assert out.status == "cancelled"
    assert session.exec(select(Mark)).first() is not None, "the marks stay"
    assert heard(session, class_test.EVENT_CANCELLED)

    with pytest.raises(HTTPException) as again:
        class_test.cancel_class_test(session, exam.id, data["meera"])
    assert again.value.status_code == 409
    with pytest.raises(HTTPException) as edit:
        class_test.update_class_test(
            session, exam.id, ClassTestUpdateIn(total_marks=Decimal("40")), data["meera"]
        )
    assert edit.value.status_code == 409


def test_only_a_class_test_can_be_handled_here():
    session, data = world()
    other = Exam(name="Mid Term", exam_type="mid_term_test", scope="class")
    session.add(other)
    session.commit()
    with pytest.raises(HTTPException) as caught:
        class_test.cancel_class_test(session, other.id, data["office"])
    assert caught.value.status_code == 404


# ------------------------------------------------------------------ reading


def test_a_class_test_shows_only_in_the_sections_that_sit_it():
    session, data = world()
    exam = class_test.create_class_test(session, create_in(data), data["meera"])
    in_a = service.list_exams(session, data["office"], classroom_id=data["room"].id)
    in_b = service.list_exams(
        session, data["office"], classroom_id=data["other_room"].id
    )
    assert [e.id for e in in_a] == [exam.id]
    assert in_b == [], "9-B does not sit it"


def test_the_class_teacher_sees_the_tests_of_their_section_without_holding_the_subject():
    session, data = world()
    jaya, jaya_user = _teacher(session, "jaya2@test", "EMP-P3-J2")
    data["other_room"].class_teacher_id = jaya.id
    session.add(data["other_room"])
    session.commit()
    exam = class_test.create_class_test(
        session,
        create_in(
            data,
            section_ids=[data["room"].id, data["other_room"].id],
            taken_by_employee_id=data["employee"].id,
        ),
        data["office"],
    )
    seen = service.list_exams(session, jaya_user)
    assert [e.id for e in seen] == [exam.id]
    assert any(p.can_edit for p in seen[0].papers if p.classroom_id == data["other_room"].id)


def test_a_teacher_with_no_link_to_the_test_does_not_see_it():
    session, data = world()
    class_test.create_class_test(session, create_in(data), data["meera"])
    assert service.list_exams(session, data["outsider"]) == []
