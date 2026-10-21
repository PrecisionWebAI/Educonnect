from fastapi import HTTPException
from sqlmodel import Session

from app.domains.students import repository as student_repository

from . import repository
from .models import ClassDiary, HomeworkAssignment, HomeworkSubmission
from .schemas import (
    ClassDiaryCreate,
    HomeworkAssignmentCreate,
    HomeworkSubmissionCreate,
)


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> HomeworkAssignment:
    return repository.create_homework(session, homework_in)


def get_homework_by_class(
    session: Session, class_id: int, section_id: int | None = None
) -> list[HomeworkAssignment]:
    return repository.get_homework_by_class(session, class_id, section_id)


def submit_homework(
    session: Session, submission_in: HomeworkSubmissionCreate
) -> HomeworkSubmission:
    # Ensure student exists
    student = student_repository.get_student_by_id(session, submission_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return repository.create_or_update_submission(session, submission_in)


def create_diary_note(session: Session, diary_in: ClassDiaryCreate) -> ClassDiary:
    student = student_repository.get_student_by_id(session, diary_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return repository.create_diary_note(session, diary_in)


def get_diary_by_student(session: Session, student_id: int) -> list[ClassDiary]:
    return repository.get_diary_by_student(session, student_id)


def list_homework(session: Session) -> list["HomeworkAssignmentRead"]:
    """The homework board, built from real `homeworkassignment` rows."""
    from datetime import date

    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.teachers.models import TeacherProfile
    from app.domains.users.models import User

    from .schemas import HomeworkAssignmentRead

    result: list[HomeworkAssignmentRead] = []
    for homework in repository.get_all_homework(session):
        classroom = session.get(Classroom, homework.classroom_id) if homework.classroom_id else None
        section = session.get(Section, homework.section_id) if homework.section_id else None
        subject = session.get(Subject, homework.subject_id) if homework.subject_id else None
        teacher_name = None
        if homework.teacher_id:
            profile = session.get(TeacherProfile, homework.teacher_id)
            if profile and profile.user_id:
                user = session.get(User, profile.user_id)
                teacher_name = user.full_name if user else None
        class_name = classroom.name if classroom else ""
        if section:
            class_name = f"{class_name}-{section.name}"
        days = (homework.due_date - date.today()).days
        due = (
            "Overdue" if days < 0
            else "Today" if days == 0
            else "Tomorrow" if days == 1
            else f"{days} days"
        )
        result.append(
            HomeworkAssignmentRead(
                id=homework.id,
                title=homework.title,
                description=homework.description,
                classroom_id=homework.classroom_id,
                section_id=homework.section_id,
                subject_id=homework.subject_id,
                teacher_id=homework.teacher_id,
                due_date=homework.due_date,
                subject=subject.name if subject else None,
                className=class_name,
                due=due,
                assignedBy=teacher_name,
            )
        )
    return result


def list_submissions(session: Session) -> list["SubmissionItemRead"]:
    """Submissions from `homeworksubmission`, joined to homework + student names."""
    from app.domains.students.models import StudentProfile
    from app.domains.users.models import User

    from .schemas import SubmissionItemRead

    result: list[SubmissionItemRead] = []
    for submission in repository.get_all_submissions(session):
        homework = session.get(HomeworkAssignment, submission.homework_id)
        student = session.get(StudentProfile, submission.student_id) if submission.student_id else None
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
    """Diary notes from `classdiary`; subject/homework/activity are not stored."""
    from app.domains.academics.models import Classroom, Section
    from app.domains.students.models import StudentProfile

    from .schemas import DiaryEntryRead

    result: list[DiaryEntryRead] = []
    for entry in repository.get_all_diary(session):
        student = session.get(StudentProfile, entry.student_id) if entry.student_id else None
        classroom = session.get(Classroom, student.classroom_id) if (student and student.classroom_id) else None
        section = session.get(Section, student.section_id) if (student and student.section_id) else None
        class_name = classroom.name if classroom else ""
        if section:
            class_name = f"{class_name}-{section.name}"
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
