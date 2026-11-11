from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session

from app.domains.students import repository as student_repository

from . import repository
from .models import ClassLog, HomeworkAssignment, HomeworkSubmission
from .schemas import (
    ClassLogCreate,
    HomeworkAssignmentCreate,
    HomeworkSubmissionCreate,
)


def _homework_read(session: Session, homework: HomeworkAssignment) -> "HomeworkAssignmentRead":
    """One assignment in the shape the board shows: names, not ids.

    Shared by the school-wide board, the class-section board and the assign call,
    so a row that was just written looks exactly like one that was re-read.
    """
    from datetime import date

    from app.domains.academics.models import ClassName, Classroom, Section, Subject
    from app.domains.staff.models import Employee
    from app.domains.users.models import User

    from .schemas import HomeworkAssignmentRead

    section = session.get(Classroom, homework.classroom_id) if homework.classroom_id else None
    classroom = session.get(ClassName, section.class_id) if section else None
    letter = session.get(Section, section.section_id) if section else None
    subject = session.get(Subject, homework.subject_id) if homework.subject_id else None
    teacher_name = None
    if homework.teacher_id:
        profile = session.get(Employee, homework.teacher_id)
        if profile and profile.user_id:
            user = session.get(User, profile.user_id)
            teacher_name = user.full_name if user else None
    class_name = classroom.classname if classroom else ""
    if letter:
        class_name = f"{class_name}-{letter.section_name}"
    days = (homework.due_date - date.today()).days
    due = (
        "Overdue" if days < 0
        else "Today" if days == 0
        else "Tomorrow" if days == 1
        else f"{days} days"
    )
    return HomeworkAssignmentRead(
        id=homework.id,
        title=homework.title,
        description=homework.description,
        section_id=homework.classroom_id,
        subject_id=homework.subject_id,
        teacher_id=homework.teacher_id,
        due_date=homework.due_date,
        subject=subject.name if subject else None,
        className=class_name,
        due=due,
        assignedBy=teacher_name,
    )


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> "HomeworkAssignmentRead":
    """Store the assignment and hand back the row the board will show."""
    homework = repository.create_homework(session, homework_in)
    return _homework_read(session, homework)


def get_homework_by_section(
    session: Session, section_id: UUID
) -> list["HomeworkAssignmentRead"]:
    """One class-section's assignments, with subject and due as the board shows them."""
    return [
        _homework_read(session, homework)
        for homework in repository.get_homework_by_section(session, section_id)
    ]


def submit_homework(
    session: Session, submission_in: HomeworkSubmissionCreate
) -> HomeworkSubmission:
    # Ensure student exists
    student = student_repository.get_student_by_id(session, submission_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return repository.create_or_update_submission(session, submission_in)


def create_class_log(session: Session, log_in: ClassLogCreate) -> ClassLog:
    """Write the day's log for a class-section."""
    return repository.create_class_log(session, log_in)


def get_class_log_by_section(session: Session, section_id: UUID) -> list[ClassLog]:
    return repository.get_class_log_by_section(session, section_id)


def list_homework(session: Session) -> list["HomeworkAssignmentRead"]:
    """The homework board, built from real `homeworkassignment` rows."""
    return [
        _homework_read(session, homework)
        for homework in repository.get_all_homework(session)
    ]


def list_submissions(session: Session) -> list["SubmissionItemRead"]:
    """Submissions from `homeworksubmission`, joined to homework + student names."""
    from app.domains.students.models import Student
    from app.domains.users.models import User

    from .schemas import SubmissionItemRead

    result: list[SubmissionItemRead] = []
    for submission in repository.get_all_submissions(session):
        homework = session.get(HomeworkAssignment, submission.homework_id)
        student = session.get(Student, submission.student_id) if submission.student_id else None
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        result.append(
            SubmissionItemRead(
                id=submission.id,
                homeworkTitle=homework.title if homework else "",
                student=user.full_name if user else f"Student {submission.student_id}",
                status=submission.status.value.capitalize(),
                submittedAt="",  # no timestamp column on the row
            )
        )
    return result


def list_diary(session: Session) -> list["DiaryEntryRead"]:
    """The class log: one line per class-section per day."""
    from app.domains.academics.models import ClassName, Classroom, Section

    from .schemas import DiaryEntryRead

    result: list[DiaryEntryRead] = []
    for entry in repository.get_all_class_logs(session):
        section = session.get(Classroom, entry.classroom_id)
        classroom = session.get(ClassName, section.class_id) if section else None
        letter = session.get(Section, section.section_id) if section else None
        class_name = classroom.classname if classroom else ""
        if letter:
            class_name = f"{class_name}-{letter.section_name}"
        result.append(
            DiaryEntryRead(
                id=entry.id,
                className=class_name,
                day=entry.date.strftime("%a"),
                subject="",
                topic=entry.note,
                homework="",
                activity="",
            )
        )
    return result
