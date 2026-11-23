"""People and hiring after the global subject list: tags, suggestions, and no hidden gate.

Phase 4 (phase3.md): a teacher's subjects are **plain text** on the employee
(`subject_tags`); a hiring candidate's subject is **free text** with suggestions that come
from a school setting; and nothing about either decides who may be assigned.
"""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlmodel import select

from app.domains.academic.classroom.course import service as course_service
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.course.schemas import (
    ChapterCreate,
    ChapterTickIn,
    CourseTeacherAssignIn,
)
from app.domains.admin.platform.models import School
from app.domains.operations.staff_hiring import service as hiring_service
from app.domains.people.staff import service as staff_service
from app.domains.people.staff.models import Employee
from app.domains.people.staff.schemas import StaffProfileCreate
from app.domains.people.teachers import service as teachers_service
from app.domains.people.teachers import subject_tags
from tests.course_support import section_subject
from tests.test_course_chapters import _seed as course_seed
from tests.test_course_chapters import memory_session

# ---- the tag text ----------------------------------------------------------


def test_tags_are_trimmed_deduplicated_and_joined():
    assert subject_tags.normalise("  Maths ,english,, MATHS ,  Lab   Work ") == (
        "Maths, english, Lab Work"
    )
    assert subject_tags.normalise("  , ") is None
    assert subject_tags.normalise(None) is None


def test_a_tag_line_past_the_column_is_refused_not_cut():
    with pytest.raises(HTTPException) as caught:
        subject_tags.normalise("x" * 501)
    assert caught.value.status_code == 422


def test_split_tags_returns_clean_tags_in_order():
    assert subject_tags.split_tags("Maths,  English ,, Lab   Work") == [
        "Maths",
        "English",
        "Lab Work",
    ]
    assert subject_tags.split_tags(None) == []


def test_a_tag_matches_a_whole_subject_name_only():
    assert subject_tags.mentions("English, Maths", "maths") is True
    assert subject_tags.mentions("English, Mathematics", "Maths") is False
    assert subject_tags.mentions(None, "Maths") is False


# ---- the hire form and the lists ----------------------------------------------


def _hire(**overrides) -> StaffProfileCreate:
    fields = {
        "full_name": "Tag Teacher",
        "department": "Science",
        "role_codenames": ["teacher"],
        "contact_email": "tag.teacher@test",
        "phone": "9000000801",
        "bank_name": "HDFC",
        "subject_tags": " Physics ,chemistry, physics",
    }
    fields.update(overrides)
    return StaffProfileCreate(**fields)


def test_the_hire_form_stores_tags_and_every_list_reads_them_back():
    with memory_session() as session:
        data = course_seed(session)
        staff_service.create_profile(session, _hire())
        row = next(
            profile
            for profile in staff_service.list_profiles(session)
            if profile.email.startswith("tag.teacher")
        )
        assert row.subject_tags == "physics, chemistry"

        employee = session.exec(
            select(Employee).where(Employee.employee_code == row.employee_code)
        ).one()
        assert employee.subject_tags == "physics, chemistry"

        # The Teachers directory prints the same text, and no subject id anywhere.
        directory = teachers_service.get_teachers(session, user=data["office"])
        listed = next(item for item in directory if item.staffCode == row.employee_code)
        assert listed.subjectTags == "physics, chemistry"
        assert "subject_id" not in listed.model_dump()

        staff_service.update_profile(session, employee.id, _hire(subject_tags=""))
        session.refresh(employee)
        assert employee.subject_tags is None, "an empty form clears the tags"


def test_a_hire_with_too_long_tags_is_refused():
    with memory_session() as session:
        course_seed(session)
        with pytest.raises(HTTPException) as caught:
            staff_service.create_profile(session, _hire(subject_tags="y" * 501))
        assert caught.value.status_code == 422


# ---- no hidden gate: any active teacher can hold and tick any subject --------------


def test_a_teacher_who_lists_other_subjects_can_hold_and_tick_a_subject():
    with memory_session() as session:
        data = course_seed(session)
        owner_employee = data["owner_employee"]
        # They list Art; the subject is Maths. The tags are only text.
        owner_employee.subject_tags = "Art"
        session.add(owner_employee)
        session.commit()

        row_id = data["first_row"].classroom_subject_id
        course_service.assign_teacher(
            session,
            row_id,
            CourseTeacherAssignIn(teacher_id=owner_employee.id),
            user=data["office"],
        )
        chapter = course_service.add_chapter(
            session, row_id, ChapterCreate(name="Algebra"), user=data["office"]
        )
        ticked = course_service.tick_chapter(
            session,
            chapter.chapter_id,
            ChapterTickIn(classroom_id=data["first"].id, status="Completed"),
            user=data["owner"],
        )
        assert ticked.status == "Completed"


# ---- hiring: the subject is free text, suggestions are a setting -----------------


def test_suggestions_default_to_this_schools_section_subject_names_and_never_cross_schools():
    with memory_session() as session:
        data = course_seed(session)
        first_school = session.info["school_id"]
        section_subject(session, data["second"].id, "Computer Science", code="CS")

        names = hiring_service.subject_suggestions(session)
        assert names == sorted({"Computer Science", "maths"}, key=str.lower)

        other = School(name="Other", code="OTH-9", email="oth9@test")
        session.add(other)
        session.commit()
        session.refresh(other)
        session.info["school_id"] = other.id
        assert hiring_service.subject_suggestions(session) == []
        session.info["school_id"] = first_school


def test_a_saved_list_wins_is_cleaned_and_is_not_a_link():
    with memory_session() as session:
        data = course_seed(session)
        saved = hiring_service.save_subject_suggestions(
            session, [" Physics ", "physics", "", "Drama  Club"]
        )
        assert saved == ["Physics", "Drama Club"]
        assert hiring_service.subject_suggestions(session) == saved

        # Renaming a real section subject leaves the saved list exactly as it was.
        row = session.get(ClassroomSubject, data["first_row"].classroom_subject_id)
        row.name = "Renamed"
        session.add(row)
        session.commit()
        assert hiring_service.subject_suggestions(session) == saved

        with pytest.raises(HTTPException) as too_many:
            hiring_service.save_subject_suggestions(
                session, [f"Subject {n}" for n in range(101)]
            )
        assert too_many.value.status_code == 422


def test_a_candidate_keeps_whatever_subject_text_was_typed():
    from app.domains.operations.staff_hiring.schemas import HiringCandidateCreate

    with memory_session() as session:
        course_seed(session)
        candidate = hiring_service.create_candidate(
            session,
            HiringCandidateCreate(
                candidate_name="Asha Rao",
                department="Science",
                applied_for="teacher",
                role="Teacher",
                subject_name="Quantum Basket Weaving",
                phone="9000000802",
                email="asha.rao@test",
                applied_on=date(2026, 11, 1),
            ),
        )
        # The request base class stores text in its canonical (lower) case; screens title-case it.
        assert candidate.subject_name == "quantum basket weaving"
        assert not hasattr(candidate, "subject_id")


# ---- the dashboard reads the section's own subject -------------------------------


def test_the_dashboard_has_no_school_wide_subject_roll_up():
    from app.domains.main.dashboard import service as dashboard

    with memory_session() as session:
        course_seed(session)
        assert dashboard.subject_perf(session) == []


def test_the_teachers_directory_read_uses_a_fixed_number_of_queries():
    with memory_session() as session:
        course_seed(session)

        def count_for(extra: int) -> int:
            for number in range(extra):
                staff_service.create_profile(
                    session,
                    _hire(
                        full_name=f"Extra {extra}-{number}",
                        contact_email=f"extra{extra}{number}@test",
                        phone=f"90000{extra:02d}{number:03d}"[:10],
                        subject_tags="Maths, English",
                    ),
                )
            seen: list[str] = []
            engine = session.get_bind()

            def on_execute(conn, cursor, statement, parameters, context, many):
                seen.append(statement)

            event.listen(engine, "before_cursor_execute", on_execute)
            try:
                teachers_service.workload_matrix(session)
            finally:
                event.remove(engine, "before_cursor_execute", on_execute)
            return len(seen)

        three = count_for(3)
        ten = count_for(7)
        assert ten == three, f"{three} statements for 3 extra teachers, {ten} for 10"
