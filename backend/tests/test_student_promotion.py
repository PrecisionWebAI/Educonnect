"""Promote, retain, complete and de-promote from the Students tab.

One enrollment per student per year; the old record is never overwritten. Everything a
request does is one transaction, a student already in the target year is skipped, and
de-promote deletes what hangs from the next-year record only after confirmation.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.academic.classroom.academics.models import ClassName, Section
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.students.models import Enrollment, Student
from app.domains.academic.classroom.students.promotion import direct
from app.domains.admin.settings.academic_year_context import (
    ensure_current_academic_year,
)
from app.domains.admin.settings.models import AcademicYear
from app.domains.auth.permissions import (
    PRINCIPAL_PERMISSIONS,
    SCHOOL_ADMIN_PERMISSIONS,
    TEACHER_PERMISSIONS,
    VICE_PRINCIPAL_PERMISSIONS,
)
from app.domains.finance.fees.models import FeeTransaction
from app.domains.operations.fees_structure.models import FeeStructure
from tests.test_classroom_students import _bind, _school, _student, memory_session


def _setup(session):
    """Classes 6, 7 and 8 (the highest), sections A and B, a current and a next year."""
    school = _school(session, "promo school", "prm")
    _bind(session, school)
    classes = []
    for name, level in (("Class 6", 6), ("Class 7", 7), ("Class 8", 8)):
        row = ClassName(classname=name, level=level)
        session.add(row)
        classes.append(row)
    for letter in "AB":
        session.add(Section(section_name=letter))
    session.commit()
    sections = {s.section_name: s for s in session.exec(select(Section)).all()}
    rooms = {
        (c.classname, letter): ensure_room(
            session, c.class_id, sections[letter].section_id
        )
        for c in classes
        for letter in "AB"
    }
    current = ensure_current_academic_year(session)
    nxt = AcademicYear(
        name="2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
        school_id=current.school_id,
    )
    session.add(nxt)
    session.commit()
    session.refresh(nxt)
    return {
        "classes": {c.classname: c for c in classes},
        "rooms": rooms,
        "current": current,
        "next": nxt,
    }


def _enrollment(session, student, year):
    return session.exec(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.academic_year_id == year.id,
        )
    ).first()


def test_promote_creates_next_year_record_and_notes_the_old_one():
    with memory_session() as session:
        w = _setup(session)
        aarav = _student(session, "aarav", "PR-1", w["rooms"][("Class 6", "A")])

        result = direct.promote(session, [aarav.id], None)

        assert result.done == 1 and result.skipped == []
        old = _enrollment(session, aarav, w["current"])
        new = _enrollment(session, aarav, w["next"])
        assert old.classroom_id == w["rooms"][("Class 6", "A")].id  # not overwritten
        assert old.status == "active"
        assert old.next_year_outcome == "Promoted to Class 7"
        assert old.promotion_status == "NEW_ADMISSION"
        assert (
            new.classroom_id == w["rooms"][("Class 7", "A")].id
        )  # same section letter
        assert new.promotion_status == "PROMOTED"
        assert new.previous_enrollment_id == old.id
        # Today's placement is untouched until the new year is switched to.
        assert session.get(Student, aarav.id).classroom_id == old.classroom_id


def test_promote_to_a_chosen_class_and_retain_in_the_same_class():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])
        b = _student(session, "b", "PR-2", w["rooms"][("Class 6", "B")])

        direct.promote(session, [a.id], w["classes"]["Class 8"].class_id)
        direct.retain(session, [b.id])

        assert (
            _enrollment(session, a, w["current"]).next_year_outcome
            == "Promoted to Class 8"
        )
        kept = _enrollment(session, b, w["next"])
        assert kept.classroom_id == w["rooms"][("Class 6", "B")].id
        assert kept.promotion_status == "RETAINED"
        assert (
            _enrollment(session, b, w["current"]).next_year_outcome
            == "Retained in Class 6"
        )


def test_a_student_is_never_promoted_twice_and_the_skip_is_reported():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])
        b = _student(session, "b", "PR-2", w["rooms"][("Class 6", "A")])
        direct.promote(session, [a.id], None)

        result = direct.promote(session, [a.id, b.id], None)

        assert result.done == 1
        assert [row.student_id for row in result.skipped] == [a.id]
        assert "already" in result.skipped[0].reason.lower()
        assert (
            len(
                session.exec(
                    select(Enrollment).where(Enrollment.student_id == a.id)
                ).all()
            )
            == 2
        )


def test_the_highest_class_completes_instead_and_depromote_restores_it():
    with memory_session() as session:
        w = _setup(session)
        top = _student(session, "top", "PR-1", w["rooms"][("Class 8", "A")])
        low = _student(session, "low", "PR-2", w["rooms"][("Class 6", "A")])

        # The highest class has no "next class".
        assert (
            direct.promote(session, [top.id], None)
            .skipped[0]
            .reason.startswith("Is in the highest")
        )
        # Only the highest class can be completed.
        assert direct.complete(session, [low.id]).done == 0

        assert direct.complete(session, [top.id]).done == 1
        old = _enrollment(session, top, w["current"])
        assert (
            old.promotion_status == "COMPLETED" and old.next_year_outcome == "Completed"
        )
        assert _enrollment(session, top, w["next"]) is None

        assert direct.depromote(session, [top.id], confirmed=False).done == 1
        old = _enrollment(session, top, w["current"])
        assert old.promotion_status == "NEW_ADMISSION" and old.next_year_outcome is None


def test_depromote_warns_with_counts_and_deletes_only_after_confirmation():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])
        direct.promote(session, [a.id], None)
        new = _enrollment(session, a, w["next"])

        structure = FeeStructure(
            name="tuition",
            amount=Decimal("100"),
            class_id=w["classes"]["Class 7"].class_id,
            frequency="monthly",
            academic_year_id=w["next"].id,
            school_id=w["current"].school_id,
        )
        session.add(structure)
        session.commit()
        session.refresh(structure)
        session.add(
            FeeTransaction(
                student_id=a.id,
                fee_structure_id=structure.id,
                amount_paid=Decimal("100"),
                date=date(2027, 5, 2),
                payment_mode="cash",
                receipt_number="R-1",
                school_id=w["current"].school_id,
            )
        )
        for day in (date(2027, 6, 1), date(2027, 6, 2)):
            session.add(
                AttendanceRecord(
                    student_id=a.id,
                    classroom_id=new.classroom_id,
                    date=day,
                    status="present",
                    school_id=w["current"].school_id,
                )
            )
        session.commit()

        preview = direct.preview_depromote(session, [a.id])
        assert (preview.attendance, preview.fees, preview.marks) == (2, 1, 0)

        with pytest.raises(HTTPException) as refused:
            direct.depromote(session, [a.id], confirmed=False)
        assert refused.value.status_code == 409
        assert (
            "2 attendance" in refused.value.detail and "1 fee" in refused.value.detail
        )
        assert _enrollment(session, a, w["next"]) is not None  # nothing changed

        assert direct.depromote(session, [a.id], confirmed=True).done == 1
        assert _enrollment(session, a, w["next"]) is None
        assert _enrollment(session, a, w["current"]).next_year_outcome is None
        assert session.exec(select(AttendanceRecord)).all() == []
        assert session.exec(select(FeeTransaction)).all() == []


def test_a_bad_request_changes_nothing_and_the_next_year_must_exist():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])

        with pytest.raises(HTTPException) as unknown_class:
            direct.promote(session, [a.id], w["current"].id)  # not a class id
        assert unknown_class.value.status_code == 404
        assert _enrollment(session, a, w["next"]) is None

        session.delete(w["next"])
        session.commit()
        with pytest.raises(HTTPException) as missing:
            direct.promote(session, [a.id], None)
        assert missing.value.status_code == 409
        assert (
            "2027-28" in missing.value.detail
            and "not created yet" in missing.value.detail
        )


def test_only_principal_and_admin_hold_the_promote_right():
    assert "students.promote" in PRINCIPAL_PERMISSIONS
    assert "students.promote" in SCHOOL_ADMIN_PERMISSIONS
    assert "students.promote" not in VICE_PRINCIPAL_PERMISSIONS
    assert "students.promote" not in TEACHER_PERMISSIONS


def test_promote_into_a_section_the_admin_picked_creates_that_room():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])

        # Class 7 has A and B; the admin picks B for a child who sat in A.
        result = direct.promote(session, [a.id], None, "b")
        assert result.done == 1
        new = _enrollment(session, a, w["next"])
        assert new.classroom_id == w["rooms"][("Class 7", "B")].id

        with pytest.raises(HTTPException) as unknown:
            direct.promote(session, [a.id], None, "Z")
        assert unknown.value.status_code == 404


def test_a_student_can_only_be_promoted_to_a_higher_class():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 7", "A")])

        for target in ("Class 6", "Class 7"):  # lower, and their own class
            result = direct.promote(session, [a.id], w["classes"][target].class_id)
            assert result.done == 0
            assert "higher class" in result.skipped[0].reason
        assert _enrollment(session, a, w["next"]) is None

        assert (
            direct.promote(session, [a.id], w["classes"]["Class 8"].class_id).done == 1
        )


def test_demote_moves_a_student_one_class_down_into_the_chosen_section():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 7", "A")])
        low = _student(session, "low", "PR-2", w["rooms"][("Class 6", "A")])
        kept = _student(session, "kept", "PR-3", w["rooms"][("Class 7", "A")])
        direct.retain(
            session, [kept.id]
        )  # has a next-year outcome -> cannot be moved down

        result = direct.demote(session, [a.id, low.id, kept.id], "b")

        assert result.done == 1
        reasons = {row.name: row.reason for row in result.skipped}
        assert "No class below Class 6" in reasons["low"]
        assert "next-year outcome" in reasons["kept"]
        # Same year, same single enrollment: only its class changed.
        moved = _enrollment(session, a, w["current"])
        assert moved.classroom_id == w["rooms"][("Class 6", "B")].id
        assert (
            session.get(Student, a.id).classroom_id == w["rooms"][("Class 6", "B")].id
        )

        with pytest.raises(HTTPException) as unknown:
            direct.demote(session, [a.id], "Z")
        assert unknown.value.status_code == 404


def test_undo_takes_back_a_promotion_a_retain_and_a_move_down():
    with memory_session() as session:
        w = _setup(session)
        promoted = _student(session, "p", "PR-1", w["rooms"][("Class 6", "A")])
        retained = _student(session, "r", "PR-2", w["rooms"][("Class 6", "B")])
        down = _student(session, "d", "PR-3", w["rooms"][("Class 7", "A")])
        nothing = _student(session, "n", "PR-4", w["rooms"][("Class 6", "A")])
        direct.promote(session, [promoted.id], None)
        direct.retain(session, [retained.id])
        direct.demote(session, [down.id], "b")
        assert (
            _enrollment(session, down, w["current"]).moved_from_classroom_id is not None
        )

        result = direct.undo(
            session, [promoted.id, retained.id, down.id, nothing.id], False
        )

        assert result.done == 3
        assert [row.name for row in result.skipped] == ["n"]
        for student in (promoted, retained):
            assert _enrollment(session, student, w["next"]) is None
            assert _enrollment(session, student, w["current"]).next_year_outcome is None
        back = _enrollment(session, down, w["current"])
        assert back.classroom_id == w["rooms"][("Class 7", "A")].id  # class AND section
        assert back.moved_from_classroom_id is None
        assert session.get(Student, down.id).classroom_id == back.classroom_id


def test_undo_with_data_asks_first_and_changes_nothing_until_confirmed():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])
        direct.promote(session, [a.id], None)
        new = _enrollment(session, a, w["next"])
        session.add(
            AttendanceRecord(
                student_id=a.id,
                classroom_id=new.classroom_id,
                date=date(2027, 6, 1),
                status="present",
                school_id=w["current"].school_id,
            )
        )
        session.commit()

        with pytest.raises(HTTPException) as asked:
            direct.undo(session, [a.id], False)
        assert asked.value.status_code == 409 and "1 attendance" in asked.value.detail
        assert _enrollment(session, a, w["next"]) is not None

        preview = direct.preview_undo(session, [a.id])
        assert (preview.attendance, preview.fees, preview.marks) == (1, 0, 0)
        assert direct.undo(session, [a.id], True).done == 1
        assert _enrollment(session, a, w["next"]) is None


def test_the_promotion_routes_the_screen_calls_exist():
    """The Students tab calls these paths; a typo here is a 404 on the office's screen."""
    from app.main import app

    paths = app.openapi()["paths"]
    for path in (
        "/promotions/promote",
        "/promotions/retain",
        "/promotions/complete",
        "/promotions/demote",
        "/promotions/undo",
        "/promotions/undo/preview",
        "/promotions/depromote",
        "/promotions/depromote/preview",
    ):
        assert "post" in paths.get(path, {}), path


def _third_year(session, w):
    year = AcademicYear(
        name="2028-29",
        start_date=date(2028, 4, 1),
        end_date=date(2029, 3, 31),
        is_current=False,
        school_id=w["current"].school_id,
    )
    session.add(year)
    session.commit()
    session.refresh(year)
    return year


def test_undoing_a_promotion_also_removes_what_was_done_to_it_the_next_year():
    with memory_session() as session:
        w = _setup(session)
        third = _third_year(session, w)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])

        direct.promote(session, [a.id], None)  # year 1 -> year 2 (Class 7)
        session.info["academic_year_id"] = w["next"].id  # look at year 2
        direct.retain(session, [a.id])  # year 2 -> year 3 (Class 7 again)
        assert _enrollment(session, a, third) is not None
        session.add(
            AttendanceRecord(
                student_id=a.id,
                classroom_id=_enrollment(session, a, third).classroom_id,
                date=date(2028, 6, 1),
                status="present",
                school_id=w["current"].school_id,
            )
        )
        session.commit()

        session.info.pop("academic_year_id")  # back to year 1
        preview = direct.preview_undo(session, [a.id])
        assert (
            preview.attendance == 1 and preview.skipped == []
        )  # year 3's data is counted
        with pytest.raises(HTTPException) as asked:
            direct.undo(session, [a.id], False)
        assert asked.value.status_code == 409
        assert _enrollment(session, a, third) is not None  # nothing changed yet

        assert direct.undo(session, [a.id], True).done == 1
        assert _enrollment(session, a, w["next"]) is None
        assert _enrollment(session, a, third) is None
        assert _enrollment(session, a, w["current"]).next_year_outcome is None
        assert session.exec(select(AttendanceRecord)).all() == []


def test_undoing_a_promotion_also_removes_a_move_down_made_the_next_year():
    with memory_session() as session:
        w = _setup(session)
        a = _student(session, "a", "PR-1", w["rooms"][("Class 6", "A")])

        direct.promote(session, [a.id], None)
        session.info["academic_year_id"] = w["next"].id
        assert direct.demote(session, [a.id], "b").done == 1  # moved down inside year 2
        assert _enrollment(session, a, w["next"]).moved_from_classroom_id is not None

        session.info.pop("academic_year_id")
        assert direct.undo(session, [a.id], False).done == 1
        assert _enrollment(session, a, w["next"]) is None
        assert _enrollment(session, a, w["current"]).next_year_outcome is None
