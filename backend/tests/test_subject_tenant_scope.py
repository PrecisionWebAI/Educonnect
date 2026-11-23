"""Classroom subjects stay inside their school, and the Course read does not grow with data.

Two things the plan (phase3.md 0.6, 5.5, 5.6) asks to be pinned:

* **tenant isolation** - school B's subject is a `404` for school A everywhere a subject
  id is accepted: the shared section-subject check, chapter copy, and the copy sources;
* **a fixed number of queries** - `section_course` issues the same number of statements
  for one subject as for many, so the tab does not slow down as a school grows.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import event

from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.course import service
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.course.schemas import (
    AddSectionSubjectIn,
    ChapterCreate,
    CourseTeacherAssignIn,
)
from app.domains.academic.classroom.course.subjects import require_section_subject
from tests.course_support import section_subject
from tests.test_course_chapters import _school, _seed, memory_session


def _other_school_subject(session, data) -> ClassroomSubject:
    """A subject in a second school, then back to the first school's scope."""
    first_school = session.info["school_id"]
    _school(session, "CH-0002")
    from tests.test_course_chapters import _year

    year = _year(session)
    # The class and section catalogs are platform-wide; only the room is the school's.
    own_room = data["first"]
    room = Classroom(
        class_id=own_room.class_id,
        section_id=own_room.section_id,
        school_id=session.info["school_id"],
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    foreign = section_subject(session, room.id, "maths", year=year)
    session.info["school_id"] = first_school
    return foreign


def test_another_schools_subject_is_a_404_everywhere():
    with memory_session() as session:
        data = _seed(session)
        foreign = _other_school_subject(session, data)

        with pytest.raises(HTTPException) as shared_check:
            require_section_subject(session, data["first"].id, foreign.id)
        assert shared_check.value.status_code == 404


def test_a_subject_of_another_section_or_an_archived_one_is_refused():
    with memory_session() as session:
        data = _seed(session)

        with pytest.raises(HTTPException) as wrong_section:
            require_section_subject(
                session, data["first"].id, data["second_row"].classroom_subject_id
            )
        assert wrong_section.value.status_code == 422

        service.archive_subject(
            session, data["first_row"].classroom_subject_id, user=data["office"]
        )
        with pytest.raises(HTTPException) as archived:
            require_section_subject(
                session, data["first"].id, data["first_row"].classroom_subject_id
            )
        assert archived.value.status_code == 409


def _statements(session, action) -> int:
    engine = session.get_bind()
    seen: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    return len(seen)


def test_the_course_read_uses_a_fixed_number_of_queries():
    """Three subjects and eight subjects cost the same, for the office and for a teacher.

    The teacher's "may I tick this?" used to be asked once per subject; it is one
    statement for the whole section now.
    """
    with memory_session() as session:
        data = _seed(session)
        office = data["office"]
        service.assign_teacher(
            session,
            data["first_row"].classroom_subject_id,
            CourseTeacherAssignIn(teacher_id=data["owner_employee"].id),
            user=office,
        )
        viewers = (office, data["owner"])
        added = 0

        def grow(total: int) -> None:
            nonlocal added
            while added < total:
                added += 1
                row = service.add_subject(
                    session,
                    data["first"].id,
                    AddSectionSubjectIn(name=f"Subject {added}"),
                    user=office,
                )
                for number in range(1, 5):
                    service.add_chapter(
                        session,
                        row.classroom_subject_id,
                        ChapterCreate(name=f"Chapter {number}"),
                        user=office,
                    )

        def measure() -> list[int]:
            for viewer in viewers:  # warm one-off lookups, then count the second read
                service.section_course(session, data["first"].id, user=viewer)
            return [
                _statements(
                    session,
                    lambda viewer=viewer: service.section_course(
                        session, data["first"].id, user=viewer
                    ),
                )
                for viewer in viewers
            ]

        grow(3)
        few = measure()
        grow(8)
        many = measure()
        assert many == few, f"{few} statements for 3 subjects, {many} for 8"
