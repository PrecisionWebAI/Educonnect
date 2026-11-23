"""Attendance, homework, the class diary and AI papers show only the current year.

Switch the school to another academic year and last year's rows disappear from every
read; switch back and they are all there - nothing is deleted.
"""

from datetime import date
from uuid import uuid4

from sqlmodel import select

from app.domains.academic.classroom.attendance import (
    register,
)
from app.domains.academic.classroom.attendance import repository as attendance_repo
from app.domains.academic.classroom.attendance import (
    service as attendance_service,
)
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.exams import repository as exam_repo
from app.domains.academic.classroom.exams.models import PaperDraft
from app.domains.academic.classroom.homework import repository as homework_repo
from app.domains.academic.classroom.homework.models import ClassLog, HomeworkAssignment
from app.domains.admin.settings import academic_years
from tests.course_support import section_subject
from tests.test_classroom_students import memory_session, seed
from tests.test_student_year_roster import _years


def _switch(session, year):
    academic_years.make_academic_year_current(
        year.id, session=session, current_user=None
    )


def _mark(session, data, student, day, status="absent"):
    session.add(
        AttendanceRecord(
            student_id=student.id,
            classroom_id=data["first"].id,
            date=day,
            status=status,
            school_id=data["school"].id,
        )
    )
    session.commit()


def test_attendance_reads_follow_the_current_year():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        day = date(2026, 11, 16)  # inside 2026-27
        _mark(session, data, data["aarav"], day)
        _mark(session, data, data["diya"], day, "present")

        room = data["first"].id
        assert len(attendance_repo.records_on(session, room, day, None)) == 2
        assert register.attendance_window(session, room) == (day, day)
        assert attendance_repo.saved_dates(session, room, day, day) == {day}
        assert (
            len(attendance_service.get_attendance_by_student(session, data["aarav"].id))
            == 1
        )
        assert len(attendance_service.get_all_attendance(session)) == 2
        assert attendance_repo.get_absent_counts(session) == [(data["aarav"].id, 1)]

        _switch(session, b)

        assert attendance_repo.records_on(session, room, day, None) == []
        assert register.attendance_window(session, room) is None
        assert attendance_repo.saved_dates(session, room, day, day) == set()
        assert (
            attendance_service.get_attendance_by_student(session, data["aarav"].id)
            == []
        )
        assert attendance_service.get_all_attendance(session) == []
        assert attendance_repo.get_absent_counts(session) == []
        assert len(session.exec(select(AttendanceRecord)).all()) == 2  # nothing deleted

        _switch(session, a)
        assert len(attendance_repo.records_on(session, room, day, None)) == 2


def test_homework_diary_and_papers_follow_the_current_year():
    with memory_session() as session:
        data = seed(session)
        a, b = _years(session)
        subject = section_subject(session, data["first"].id, "maths", year=a)
        teacher = uuid4()
        session.add(
            HomeworkAssignment(
                title="ch 1",
                description="solve",
                classroom_id=data["first"].id,
                classroom_subject_id=subject.id,
                teacher_id=teacher,
                due_date=date(2026, 12, 1),
                school_id=data["school"].id,
            )
        )
        session.add(
            ClassLog(
                classroom_id=data["first"].id,
                teacher_id=teacher,
                classroom_subject_id=subject.id,
                date=date(2026, 11, 16),
                note="intro",
                school_id=data["school"].id,
            )
        )
        session.add(
            PaperDraft(
                title="unit test",
                classroom_subject_id=subject.id,
                school_id=data["school"].id,
            )
        )
        session.add(PaperDraft(title="loose draft", school_id=data["school"].id))
        session.commit()

        room = data["first"].id
        assert len(homework_repo.get_homework_by_section(session, room)) == 1
        assert len(homework_repo.get_all_homework(session)) == 1
        assert len(homework_repo.get_class_log_by_section(session, room)) == 1
        assert len(exam_repo.list_papers(session)) == 2

        _switch(session, b)

        assert homework_repo.get_homework_by_section(session, room) == []
        assert homework_repo.get_all_homework(session) == []
        assert homework_repo.get_all_submissions(session) == []
        assert homework_repo.get_class_log_by_section(session, room) == []
        assert homework_repo.get_all_class_logs(session) == []
        # The paper tied to last year's subject is hidden; a draft with no subject yet stays.
        assert [paper.title for paper in exam_repo.list_papers(session)] == [
            "loose draft"
        ]

        _switch(session, a)
        assert len(homework_repo.get_homework_by_section(session, room)) == 1
        assert len(exam_repo.list_papers(session)) == 2
