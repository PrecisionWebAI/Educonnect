"""Exam module, Phase 4: a School Exam's date sheet, its syllabus, and its publication.

What these scenarios pin (see `plan/school_exam.py`):

1. **who sets the date sheet** - the class teacher of the section or leadership; the subject
   teacher does not;
2. **who writes a syllabus** - the subject's teacher (their own subject only), the class
   teacher, leadership; free text;
3. **a draft does not exist for families** - they cannot list it, read it or read its
   syllabus, and nobody is notified, until it is published;
4. **publishing is the class teacher's** and tells the section's families once;
5. **after publishing** a change tells the families what changed; before, it is silent;
6. **the type** is one of the spec's list, a custom exam carries its own name, and a
   section cannot have two of the same kind;
7. **marks protect the sheet** - a subject with marks stays, a total cannot go below a mark.

Runs under pytest.
"""

from datetime import date
from decimal import Decimal

import uuid

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.academics.models import SubjectTeacher
from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.exams.plan import class_test, school_exam, service
from app.domains.academic.classroom.exams.plan.schemas import (
    ClassTestCreateIn,
    SchoolExamCreateIn,
    SchoolExamRowIn,
    SchoolExamUpdateIn,
    SyllabusIn,
)
from app.domains.auth.models import UserRole
from tests.test_classroom_exams import _role, _teacher
from tests.test_exam_class_test import heard, world

MATHS_DAY = date(2027, 1, 12)
SCIENCE_DAY = date(2027, 1, 14)


# ---------------------------------------------------------------- helpers


def with_science_teacher(session, data):
    """Bose holds Science in 9-A (a subject teacher who is *not* the class teacher)."""
    bose, bose_user = _teacher(session, "bose@test", "EMP-P4-B")
    session.add(UserRole(user_id=bose_user.id, role_id=_role(session, "teacher").id))
    session.add(
        SubjectTeacher(
            classroom_subject_id=data["science"].id,
            teacher_id=bose.id,
            effective_from=date(2026, 6, 1),
        )
    )
    session.commit()
    return bose, bose_user


def rows(data, **over):
    return [
        SchoolExamRowIn(
            classroom_subject_id=data["maths"].id,
            exam_date=MATHS_DAY,
            total_marks=Decimal("100"),
            **over,
        ),
        SchoolExamRowIn(
            classroom_subject_id=data["science"].id,
            exam_date=SCIENCE_DAY,
            total_marks=Decimal("50"),
        ),
    ]


def create_in(data, **over):
    base = dict(
        classroom_id=data["room"].id,
        exam_type="unit_test",
        rows=rows(data),
        # these scenarios set several sheets on the same days; the warning has its own test
        confirm_duplicate=True,
    )
    base.update(over)
    return SchoolExamCreateIn(**base)


def make(session, data, user=None, **over):
    return school_exam.create_school_exam(
        session, create_in(data, **over), user or data["meera"]
    )


def paper_of(exam, course):
    return next(p for p in exam.papers if p.classroom_subject_id == course.id)


def listed(session, user):
    return service.list_exams(session, user)


# ------------------------------------------------------------- the date sheet


def test_the_class_teacher_sets_a_draft_date_sheet_for_every_subject():
    session, data = world()
    out = make(session, data, family_note="Reach 15 minutes early")
    assert out.exam_type == "unit_test" and out.name == "Unit Test"
    assert out.status == "draft" and out.datesheet_published_at is None
    assert out.classroom_id == data["room"].id and out.scope == "class"
    assert out.family_note == "Reach 15 minutes early"
    assert out.can_manage is True
    maths = paper_of(out, data["maths"])
    assert maths.exam_date == MATHS_DAY and maths.max_marks == Decimal("100")
    # Each subject has its own pass line (33% of its own total).
    assert maths.pass_mode == "marks" and maths.passing_marks == Decimal("33.00")
    assert paper_of(out, data["science"]).passing_marks == Decimal("16.50")
    # No time of day and no first/last day: only a date per subject.
    assert maths.start_time is None and out.start_date is None and out.end_date is None
    assert heard(session, school_exam.EVENT_PUBLISHED) == [], "a draft tells nobody"


def test_only_the_class_teacher_and_leadership_set_the_date_sheet():
    session, data = world()
    _, bose_user = with_science_teacher(session, data)
    for who in (bose_user, data["outsider"]):
        with pytest.raises(HTTPException) as caught:
            make(session, data, user=who)
        assert caught.value.status_code == 403
    make(session, data, user=data["principal"], exam_type="annual")
    make(session, data, user=data["office"], exam_type="practical")
    assert len(session.exec(select(Exam)).all()) == 2


def test_the_type_is_one_of_the_list_and_custom_carries_its_own_name():
    session, data = world()
    for bad in ("class_test", "midterm", "", "Unit test"):
        with pytest.raises(HTTPException) as caught:
            make(session, data, exam_type=bad)
        assert caught.value.status_code == 422, bad

    with pytest.raises(HTTPException) as caught:
        make(session, data, exam_type="custom")
    assert "name" in caught.value.detail

    out = make(session, data, exam_type="custom", custom_name="  Science   Fair  ")
    assert out.exam_type == "custom" and out.name == "Science Fair"
    assert make(session, data, exam_type="mid_term_test").name == "Mid Term Test"


def test_a_section_cannot_have_two_of_the_same_kind():
    session, data = world()
    make(session, data, exam_type="half_yearly")
    with pytest.raises(HTTPException) as caught:
        make(session, data, exam_type="half_yearly")
    assert caught.value.status_code == 409
    make(session, data, exam_type="custom", custom_name="Quiz A")
    make(session, data, exam_type="custom", custom_name="Quiz B")
    with pytest.raises(HTTPException):
        make(session, data, exam_type="custom", custom_name="quiz a")


def test_every_row_must_be_a_subject_of_this_section_once():
    session, data = world()
    from app.domains.academic.classroom.course.models import ClassroomSubject

    b_maths = session.exec(
        select(ClassroomSubject).where(
            ClassroomSubject.classroom_id == data["other_room"].id
        )
    ).first()
    stray = SchoolExamRowIn(
        classroom_subject_id=b_maths.id, exam_date=MATHS_DAY, total_marks=Decimal("50")
    )
    with pytest.raises(HTTPException) as caught:
        make(session, data, rows=[stray])
    assert caught.value.status_code == 422 and "not a subject of this section" in caught.value.detail

    twice = rows(data)[:1] * 2
    with pytest.raises(HTTPException) as caught:
        make(session, data, rows=twice)
    assert "twice" in caught.value.detail
    assert session.exec(select(Exam)).all() == [], "nothing half-saved"


def test_each_subject_keeps_its_own_grade_based_pass_line():
    session, data = world()
    graded = SchoolExamRowIn(
        classroom_subject_id=data["maths"].id,
        exam_date=MATHS_DAY,
        total_marks=Decimal("100"),
        pass_mode="grade",
        passing_grade="P",
        custom_min_percent=Decimal("35"),
    )
    out = make(session, data, rows=[graded])
    paper = out.papers[0]
    assert paper.pass_mode == "grade" and paper.passing_grade == "P"
    assert paper.pass_percent == Decimal("35.00")


# --------------------------------------------------- draft is invisible


def test_a_draft_does_not_exist_for_families_until_it_is_published():
    session, data = world()
    out = make(session, data)
    parent = data["aarav_parent"]

    assert listed(session, parent) == []
    with pytest.raises(HTTPException) as caught:
        service.read_exam(session, out.id, parent)
    assert caught.value.status_code == 404
    maths = paper_of(out, data["maths"])
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Algebra"), data["meera"])
    with pytest.raises(HTTPException) as hidden:
        school_exam.get_syllabus(session, maths.id, parent)
    assert hidden.value.status_code == 404

    school_exam.publish_date_sheet(session, out.id, data["meera"])
    seen = listed(session, parent)
    assert [e.id for e in seen] == [out.id]
    assert {p.classroom_id for p in seen[0].papers} == {data["room"].id}
    assert all(p.can_edit is False and p.can_syllabus is False for p in seen[0].papers)
    assert school_exam.get_syllabus(session, maths.id, parent).syllabus_text == "Algebra"


def test_a_teacher_of_the_subject_sees_the_draft_and_other_families_never_do():
    session, data = world()
    _, bose_user = with_science_teacher(session, data)
    out = make(session, data)
    assert [e.id for e in listed(session, bose_user)] == [out.id]
    assert listed(session, data["outsider"]) == []
    # A family from another section would not see it either (their room is not on it).
    assert listed(session, data["dev_parent"]) == []


# ---------------------------------------------------------------- publishing


def test_publishing_is_the_class_teachers_and_tells_the_families_once():
    session, data = world()
    _, bose_user = with_science_teacher(session, data)
    out = make(session, data, family_note="Reach 15 minutes early")
    with pytest.raises(HTTPException) as caught:
        school_exam.publish_date_sheet(session, out.id, bose_user)
    assert caught.value.status_code == 403, "the subject teacher cannot publish"
    assert heard(session, school_exam.EVENT_PUBLISHED) == []

    done = school_exam.publish_date_sheet(session, out.id, data["meera"])
    assert done.status == "scheduled" and done.datesheet_published_at is not None
    told = heard(session, school_exam.EVENT_PUBLISHED)
    assert {row.user_id for row in told} >= {data["aarav_parent"].id}
    body = told[0].body
    assert body.index("Mathematics 12 Jan") < body.index("Science 14 Jan"), "in date order"
    assert "Reach 15 minutes early" in body

    count = len(told)
    with pytest.raises(HTTPException) as again:
        school_exam.publish_date_sheet(session, out.id, data["meera"])
    assert again.value.status_code == 409
    assert len(heard(session, school_exam.EVENT_PUBLISHED)) == count


def test_leadership_may_publish_too():
    session, data = world()
    out = make(session, data)
    done = school_exam.publish_date_sheet(session, out.id, data["principal"])
    assert done.datesheet_published_at is not None


# ------------------------------------------------------------------- editing


def test_changes_before_publishing_are_silent_and_after_publishing_are_told():
    session, data = world()
    out = make(session, data)
    new_rows = [
        SchoolExamRowIn(
            classroom_subject_id=data["maths"].id,
            exam_date=date(2027, 1, 13),
            total_marks=Decimal("100"),
        ),
        rows(data)[1],
    ]
    school_exam.update_school_exam(
        session, out.id, SchoolExamUpdateIn(rows=new_rows), data["meera"]
    )
    assert heard(session, school_exam.EVENT_CHANGED) == [], "a draft changes silently"

    school_exam.publish_date_sheet(session, out.id, data["meera"])
    moved = [
        SchoolExamRowIn(
            classroom_subject_id=data["maths"].id,
            exam_date=date(2027, 1, 20),
            total_marks=Decimal("80"),
        ),
        rows(data)[1],
    ]
    school_exam.update_school_exam(
        session, out.id, SchoolExamUpdateIn(rows=moved), data["meera"]
    )
    told = heard(session, school_exam.EVENT_CHANGED)
    assert told and {r.user_id for r in told} >= {data["aarav_parent"].id}
    assert "Mathematics: 13 Jan 2027 -> 20 Jan 2027" in told[0].body
    assert "total marks 100 -> 80" in told[0].body


def test_a_changed_note_alone_is_told_after_publishing_and_nothing_changed_is_not():
    session, data = world()
    out = make(session, data, family_note="Reach 15 minutes early")
    school_exam.publish_date_sheet(session, out.id, data["meera"])
    before = len(heard(session, school_exam.EVENT_CHANGED))
    school_exam.update_school_exam(
        session,
        out.id,
        SchoolExamUpdateIn(family_note="Reach 15 minutes early", rows=rows(data)),
        data["meera"],
    )
    assert len(heard(session, school_exam.EVENT_CHANGED)) == before, "no change, no message"

    school_exam.update_school_exam(
        session, out.id, SchoolExamUpdateIn(family_note="Bring a pen"), data["meera"]
    )
    told = heard(session, school_exam.EVENT_CHANGED)
    assert len(told) > before and "note for families changed" in told[-1].body


def test_a_subject_can_be_added_or_taken_off_unless_it_has_marks():
    session, data = world()
    out = make(session, data)
    science = paper_of(out, data["science"])
    session.add(
        Mark(student_id=data["aarav"].id, exam_paper_id=science.id, marks_obtained=Decimal("40"))
    )
    session.commit()

    only_maths = SchoolExamUpdateIn(rows=rows(data)[:1])
    with pytest.raises(HTTPException) as caught:
        school_exam.update_school_exam(session, out.id, only_maths, data["meera"])
    assert caught.value.status_code == 409 and "already has marks" in caught.value.detail

    lowered = [
        rows(data)[0],
        SchoolExamRowIn(
            classroom_subject_id=data["science"].id,
            exam_date=SCIENCE_DAY,
            total_marks=Decimal("30"),
        ),
    ]
    with pytest.raises(HTTPException) as below:
        school_exam.update_school_exam(
            session, out.id, SchoolExamUpdateIn(rows=lowered), data["meera"]
        )
    assert below.value.status_code == 422
    assert paper_of(service.read_exam(session, out.id, data["office"]), data["science"]).max_marks == Decimal("50")


def test_the_type_can_change_but_not_into_a_twin():
    session, data = world()
    first = make(session, data, exam_type="unit_test")
    make(session, data, exam_type="annual")
    with pytest.raises(HTTPException) as caught:
        school_exam.update_school_exam(
            session, first.id, SchoolExamUpdateIn(exam_type="annual"), data["meera"]
        )
    assert caught.value.status_code == 409
    out = school_exam.update_school_exam(
        session, first.id, SchoolExamUpdateIn(exam_type="periodic_test"), data["meera"]
    )
    assert out.name == "Periodic Test"


# ------------------------------------------------------------------ syllabus


def test_the_subject_teacher_writes_only_their_own_subjects_syllabus():
    session, data = world()
    _, bose_user = with_science_teacher(session, data)
    out = make(session, data)
    science = paper_of(out, data["science"])
    maths = paper_of(out, data["maths"])

    read = school_exam.set_syllabus(
        session, science.id, SyllabusIn(syllabus_text="  Light and sound\nElectricity  "), bose_user
    )
    assert read.syllabus_text == "Light and sound\nElectricity" and read.can_edit is True

    with pytest.raises(HTTPException) as caught:
        school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="x"), bose_user)
    assert caught.value.status_code == 403
    with pytest.raises(HTTPException) as stranger:
        school_exam.set_syllabus(session, science.id, SyllabusIn(syllabus_text="x"), data["outsider"])
    assert stranger.value.status_code == 403

    # The class teacher and leadership may write any subject's.
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Fractions"), data["meera"])
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Fractions, decimals"), data["principal"])


def test_the_row_knows_whether_a_syllabus_is_written_and_who_may_write_it():
    session, data = world()
    _, bose_user = with_science_teacher(session, data)
    out = make(session, data)
    science = paper_of(out, data["science"])
    assert paper_of(out, data["science"]).has_syllabus is False

    school_exam.set_syllabus(session, science.id, SyllabusIn(syllabus_text="Light"), bose_user)
    seen = service.read_exam(session, out.id, bose_user)
    assert paper_of(seen, data["science"]).has_syllabus is True
    assert paper_of(seen, data["science"]).can_syllabus is True
    assert paper_of(seen, data["maths"]).can_syllabus is False

    by_class_teacher = service.read_exam(session, out.id, data["meera"])
    assert all(p.can_syllabus for p in by_class_teacher.papers)
    assert seen.can_manage is False and by_class_teacher.can_manage is True

    school_exam.set_syllabus(session, science.id, SyllabusIn(syllabus_text="   "), bose_user)
    cleared = service.read_exam(session, out.id, data["office"])
    assert paper_of(cleared, data["science"]).has_syllabus is False, "blank clears it"


def test_a_syllabus_change_is_silent_until_published_then_told():
    session, data = world()
    out = make(session, data)
    maths = paper_of(out, data["maths"])
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Fractions"), data["meera"])
    assert heard(session, school_exam.EVENT_SYLLABUS) == []

    school_exam.publish_date_sheet(session, out.id, data["meera"])
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Fractions, decimals"), data["meera"])
    told = heard(session, school_exam.EVENT_SYLLABUS)
    assert told and "Mathematics" in told[0].title
    n = len(told)
    school_exam.set_syllabus(session, maths.id, SyllabusIn(syllabus_text="Fractions, decimals"), data["meera"])
    assert len(heard(session, school_exam.EVENT_SYLLABUS)) == n, "same text, no message"


def test_a_class_test_can_have_a_syllabus_and_it_is_readable_at_once():
    session, data = world()
    test = class_test.create_class_test(
        session,
        ClassTestCreateIn(
            classroom_subject_id=data["maths"].id,
            section_ids=[data["room"].id],
            exam_date=MATHS_DAY,
            total_marks=Decimal("20"),
        ),
        data["meera"],
    )
    school_exam.set_syllabus(
        session, test.papers[0].id, SyllabusIn(syllabus_text="Chapter 2"), data["meera"]
    )
    read = school_exam.get_syllabus(session, test.papers[0].id, data["aarav_parent"])
    assert read.syllabus_text == "Chapter 2"


# ------------------------------------------------------------------- delete


def test_an_unpublished_sheet_can_be_deleted_a_published_one_cannot():
    session, data = world()
    draft = make(session, data, exam_type="unit_test")
    school_exam.delete_school_exam(session, draft.id, data["meera"])
    assert session.get(Exam, draft.id) is None
    assert session.exec(select(ExamPaper)).all() == []

    live = make(session, data, exam_type="annual")
    school_exam.publish_date_sheet(session, live.id, data["meera"])
    with pytest.raises(HTTPException) as caught:
        school_exam.delete_school_exam(session, live.id, data["meera"])
    assert caught.value.status_code == 409

    marked = make(session, data, exam_type="practical")
    session.add(
        Mark(
            student_id=data["aarav"].id,
            exam_paper_id=marked.papers[0].id,
            marks_obtained=Decimal("5"),
        )
    )
    session.commit()
    with pytest.raises(HTTPException) as with_marks:
        school_exam.delete_school_exam(session, marked.id, data["meera"])
    assert with_marks.value.status_code == 409


def test_a_class_test_is_not_a_school_exam():
    session, data = world()
    test = class_test.create_class_test(
        session,
        ClassTestCreateIn(
            classroom_subject_id=data["maths"].id,
            section_ids=[data["room"].id],
            exam_date=MATHS_DAY,
            total_marks=Decimal("20"),
        ),
        data["meera"],
    )
    for call in (
        lambda: school_exam.publish_date_sheet(session, test.id, data["meera"]),
        lambda: school_exam.delete_school_exam(session, test.id, data["meera"]),
    ):
        with pytest.raises(HTTPException) as caught:
            call()
        assert caught.value.status_code == 404


def test_the_same_subject_on_the_same_date_asks_before_it_is_set_again():
    session, data = world()
    make(session, data)
    with pytest.raises(HTTPException) as caught:
        make(session, data, exam_type="periodic_test", confirm_duplicate=False)
    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == "DUPLICATE_EXAM"
    assert {item["subject"].lower() for item in caught.value.detail["existing"]} == {
        "mathematics",
        "science",
    }
    session.rollback()
    again = make(session, data, exam_type="periodic_test", confirm_duplicate=True)
    assert again.papers, "create anyway goes through"


def test_a_date_sheet_can_name_who_takes_each_subject_and_a_class_teacher_may_mark_it():
    from app.domains.academic.classroom.exams.plan import service
    from app.domains.academic.classroom.exams.plan.schemas import MarkEntryIn, MarksSaveIn

    session, data = world()
    mine = rows(data)
    mine[0] = mine[0].model_copy(update={"taken_by_employee_id": data["employee"].id})
    out = make(session, data, rows=mine)
    taker = paper_of(out, data["maths"])
    assert taker.taken_by_employee_id == data["employee"].id
    # a nobody is refused
    bad = rows(data)
    bad[0] = bad[0].model_copy(update={"taken_by_employee_id": uuid.uuid4()})
    with pytest.raises(HTTPException) as caught:
        make(session, data, rows=bad, exam_type="mid_term")
    assert caught.value.status_code == 422
    session.rollback()
    # the class teacher (Meera, class teacher of 9-A) marks a school exam paper of a subject
    # she does not teach (Science)
    service.save_marks(
        session,
        paper_of(out, data["science"]).id,
        MarksSaveIn(entries=[MarkEntryIn(student_id=data["aarav"].id, marks_obtained=Decimal("40"))]),
        data["meera"],
    )
