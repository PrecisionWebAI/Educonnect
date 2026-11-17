"""Homework: assign, hand in, grade - and the diary line that says what was taught.

Phase 9 finishes the loop the audit found half-drawn:

* **assigning** writes the row and tells the section's children and their guardians
  once (`homework.assigned`, one message per person per assignment);
* **handing in** stamps `submitted_at` and decides `is_late` from the due date - a fact
  stored, not guessed later, because a moved due date must not un-late yesterday;
* **grading** records the score and the remark, and tells that child and their family
  (`homework.feedback`). Only the assignment's teacher, the class teacher or the office
  may grade;
* **the diary** names its subject and its period, so a line can be read by subject.

The board's "3/4 in" comes from one grouped count, and a child who has not handed
anything in still appears - as a row with no id, which is exactly what "nothing to
grade" means.

The API speaks `section_id`; the column is `classroom_id`. This module and
`repository.py` are the only places that know both names.
"""

from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
)
from app.domains.academic.classroom.students import repository as student_repository
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User
from app.domains.auth.service import AuthorizationService
from app.domains.main.notifications import events
from app.domains.people.staff.models import Employee

from . import repository
from .models import HomeworkAssignment, HomeworkSubmission, SubmissionStatus
from .schemas import (
    ClassLogCreate,
    ClassLogRead,
    DiaryEntryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionRead,
    SubmissionFeedbackIn,
    SubmissionItemRead,
    SubmissionSubmitIn,
)

#: Where a notification about homework lands in the bell's tabs - the names live with
#: every other event, so a screen can filter on the same string.
EVENT_ASSIGNED = events.EVENT_HOMEWORK_ASSIGNED
EVENT_FEEDBACK = events.EVENT_HOMEWORK_FEEDBACK

#: The words the board prints for a submission's state.
_STATUS_WORDS = {
    SubmissionStatus.pending: "Pending",
    SubmissionStatus.submitted: "Submitted",
    SubmissionStatus.graded: "Graded",
}


# ---------------------------------------------------------------------------
# Who is asking - the same three answers the exams module gives
# ---------------------------------------------------------------------------


def _employee_of(session: Session, user) -> UUID | None:
    """The `employee` row behind a login, when the person is staff."""
    if user is None or getattr(user, "id", None) is None:
        return None
    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    return employee.id if employee is not None else None


def _is_office(session: Session, user) -> bool:
    """The office: whoever may change classes. The permission, not a role name."""
    if user is None:
        return False
    return AuthorizationService.has_permission(user, "classes.update", session=session)


def _may_grade(session: Session, user, homework: HomeworkAssignment) -> bool:
    """The office, the teacher the assignment was set by, or that room's class teacher."""
    if _is_office(session, user):
        return True
    employee_id = _employee_of(session, user)
    if employee_id is None:
        return False
    if homework.teacher_id == employee_id:
        return True
    room = session.get(Classroom, homework.classroom_id)
    return room is not None and room.class_teacher_id == employee_id


def _require_grade(session: Session, user, homework: HomeworkAssignment) -> None:
    if not _may_grade(session, user, homework):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the assignment's teacher, the class teacher or the office "
                "may grade it."
            ),
        )


# ---------------------------------------------------------------------------
# Reading it back
# ---------------------------------------------------------------------------


def _section_label(session: Session, room_id: UUID | None) -> str:
    """`"Class 9-A"` for a class-section id, from its own rows."""
    if room_id is None:
        return ""
    room = session.get(Classroom, room_id)
    if room is None:
        return ""
    klass = session.get(ClassName, room.class_id)
    letter = session.get(Section, room.section_id)
    name = klass.classname if klass else ""
    return f"{name}-{letter.section_name}" if letter else name


def _teacher_name(session: Session, employee_id: UUID | None) -> str | None:
    if employee_id is None:
        return None
    profile = session.get(Employee, employee_id)
    if profile is None or profile.user_id is None:
        return None
    user = session.get(User, profile.user_id)
    return user.full_name if user else None


def _due_word(due_date: date) -> str:
    days = (due_date - date.today()).days
    if days < 0:
        return "Overdue"
    if days == 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    return f"{days} days"


def _student_name(session: Session, student: Student) -> str:
    if student.user_id:
        user = session.get(User, student.user_id)
        if user is not None:
            return user.full_name
    return student.full_name or "—"


def _subject_name(session: Session, subject_id: UUID | None) -> str | None:
    if subject_id is None:
        return None
    subject = session.get(Subject, subject_id)
    return subject.name if subject is not None else None


def _homework_read(
    session: Session,
    homework: HomeworkAssignment,
    *,
    submitted: int = 0,
    total: int = 0,
) -> HomeworkAssignmentRead:
    """One assignment in the shape the board shows: names, not ids."""
    subject = session.get(Subject, homework.subject_id) if homework.subject_id else None
    return HomeworkAssignmentRead(
        id=homework.id,
        title=homework.title,
        description=homework.description,
        section_id=homework.classroom_id,
        subject_id=homework.subject_id,
        teacher_id=homework.teacher_id,
        due_date=homework.due_date,
        subject=subject.name if subject else None,
        className=_section_label(session, homework.classroom_id),
        due=_due_word(homework.due_date),
        assignedBy=_teacher_name(session, homework.teacher_id),
        submitted=submitted,
        total=total,
    )


# ---------------------------------------------------------------------------
# Assigning - and telling the families once
# ---------------------------------------------------------------------------


def _tell_section(
    session: Session,
    homework: HomeworkAssignment,
    *,
    event: str,
    title: str,
    body: str,
    dedupe_key: str,
    student_ids: list[UUID] | None = None,
) -> int:
    """Tell each child (and their guardians) once - never failing the save.

    `events.audience` resolves the recipients from the relationships, so a guardian
    who is also the class teacher gets one row, not two.
    """
    if student_ids is None:
        student_ids = [
            student.id
            for student in session.exec(
                select(Student).where(
                    Student.classroom_id == homework.classroom_id,
                    Student.deactivated_at.is_(None),
                )
            ).all()
        ]
    written = 0
    for student_id in student_ids:
        recipients = events.audience(
            session,
            student_id=student_id,
            roles={events.STUDENT, events.GUARDIANS},
        )
        written += events.notify(
            session,
            event=event,
            recipients=recipients,
            title=title,
            body=body,
            entity_type="homework",
            entity_id=homework.id,
            dedupe_key=f"{dedupe_key}:{student_id}",
        )
    return written


def create_homework(
    session: Session, homework_in: HomeworkAssignmentCreate
) -> HomeworkAssignmentRead:
    """Store the assignment, then tell the class-section it was set for."""
    if session.get(Classroom, homework_in.section_id) is None:
        raise HTTPException(status_code=404, detail="Class section not found")
    homework = repository.create_homework(session, homework_in)
    subject = session.get(Subject, homework.subject_id)
    label = _section_label(session, homework.classroom_id)
    _tell_section(
        session,
        homework,
        event=EVENT_ASSIGNED,
        title=f"New homework: {homework.title}",
        body=(
            f"{subject.name if subject else 'Homework'} · due {homework.due_date}. "
            f"Set for {label}."
        ),
        dedupe_key=EVENT_ASSIGNED,
    )
    total = repository.roll_counts(session, [homework.classroom_id]).get(
        homework.classroom_id, 0
    )
    return _homework_read(session, homework, submitted=0, total=total)


def get_homework_by_section(
    session: Session, section_id: UUID
) -> list[HomeworkAssignmentRead]:
    """One class-section's assignments, with subject, due word and the "3/4 in" count."""
    rows = repository.get_homework_by_section(session, section_id)
    counts = repository.submission_counts(session, [row.id for row in rows])
    total = repository.roll_counts(session, [section_id]).get(section_id, 0)
    return [
        _homework_read(session, row, submitted=counts.get(row.id, 0), total=total)
        for row in rows
    ]


def list_homework(session: Session) -> list[HomeworkAssignmentRead]:
    """The school-wide board, built from real `homeworkassignment` rows."""
    rows = repository.get_all_homework(session)
    counts = repository.submission_counts(session, [row.id for row in rows])
    totals = repository.roll_counts(session, [row.classroom_id for row in rows])
    return [
        _homework_read(
            session,
            row,
            submitted=counts.get(row.id, 0),
            total=totals.get(row.classroom_id, 0),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Handing in - the child's own act
# ---------------------------------------------------------------------------


def submit_homework(
    session: Session, submission_in: SubmissionSubmitIn, *, now: datetime | None = None
) -> HomeworkSubmissionRead:
    """Stamp one child's work as handed in, and decide whether it was late.

    Lateness is decided **here, once**, from the assignment's due date: a due date
    moved afterwards must not re-open a child's record, and a parent re-uploading a
    photo of the same page must not turn an on-time submission late (the flag is only
    ever set, never cleared).
    """
    homework = session.get(HomeworkAssignment, submission_in.homework_id)
    if homework is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    student = student_repository.get_student_by_id(session, submission_in.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.classroom_id != homework.classroom_id:
        raise HTTPException(
            status_code=422,
            detail="That child is not in the class-section this homework is set for.",
        )

    moment = now or datetime.utcnow()
    existing = repository.get_submission(session, homework.id, submission_in.student_id)
    row = repository.save_submission(
        session,
        existing=existing,
        homework_id=homework.id,
        student_id=submission_in.student_id,
        content_url=submission_in.content_url,
        submitted_at=moment,
        is_late=moment.date() > homework.due_date,
    )
    return HomeworkSubmissionRead(
        id=row.id,
        homework_id=row.homework_id,
        student_id=row.student_id,
        status=row.status,
        content_url=row.content_url,
        submitted_at=row.submitted_at,
        is_late=row.is_late,
        graded_at=row.graded_at,
        marks_awarded=row.marks_awarded,
        teacher_feedback=row.teacher_feedback,
    )


# ---------------------------------------------------------------------------
# Grading - the teacher's answer, and the family hears it once
# ---------------------------------------------------------------------------


def _submission_read(
    session: Session,
    submission: HomeworkSubmission,
    *,
    homework: HomeworkAssignment | None = None,
    student: Student | None = None,
) -> SubmissionItemRead:
    """One row of the review board, with the names it needs."""
    homework = homework or session.get(HomeworkAssignment, submission.homework_id)
    student = student or session.get(Student, submission.student_id)
    subject = (
        session.get(Subject, homework.subject_id)
        if homework is not None and homework.subject_id
        else None
    )
    return SubmissionItemRead(
        id=submission.id,
        homeworkId=submission.homework_id,
        homeworkTitle=homework.title if homework is not None else "",
        studentId=submission.student_id,
        student=_student_name(session, student) if student is not None else "—",
        sectionId=homework.classroom_id if homework is not None else None,
        subject=subject.name if subject is not None else None,
        status=_STATUS_WORDS.get(submission.status, submission.status.value.title()),
        submittedAt=(
            submission.submitted_at.strftime("%Y-%m-%d %H:%M")
            if submission.submitted_at is not None
            else ""
        ),
        isLate=submission.is_late,
        marksAwarded=submission.marks_awarded,
        feedback=submission.teacher_feedback,
        gradedAt=(
            submission.graded_at.strftime("%Y-%m-%d %H:%M")
            if submission.graded_at is not None
            else None
        ),
    )


def grade_submission(
    session: Session,
    submission_id: UUID,
    feedback_in: SubmissionFeedbackIn,
    user,
    *,
    now: datetime | None = None,
) -> SubmissionItemRead:
    """Record a score and/or a remark on one submission, then tell that family."""
    if (
        feedback_in.marks_awarded is None
        and not (feedback_in.teacher_feedback or "").strip()
    ):
        raise HTTPException(status_code=422, detail="Give a score, a remark, or both.")
    if feedback_in.marks_awarded is not None and feedback_in.marks_awarded < 0:
        raise HTTPException(status_code=422, detail="A score cannot be negative.")

    submission = repository.get_submission_by_id(session, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    homework = session.get(HomeworkAssignment, submission.homework_id)
    if homework is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    _require_grade(session, user, homework)

    moment = now or datetime.utcnow()
    row = repository.save_feedback(session, submission, feedback_in, graded_at=moment)

    subject = session.get(Subject, homework.subject_id) if homework.subject_id else None
    score = f" · {row.marks_awarded} marks" if row.marks_awarded is not None else ""
    remark = f" “{row.teacher_feedback}”" if row.teacher_feedback else ""
    _tell_section(
        session,
        homework,
        event=EVENT_FEEDBACK,
        title=f"Feedback on {homework.title}",
        body=f"{subject.name if subject else 'Homework'} checked{score}{remark}.",
        # `graded_at` in the key: a correction is a new message, a double-click is not.
        dedupe_key=f"{EVENT_FEEDBACK}:{row.id}:{moment.strftime('%Y%m%d%H%M%S')}",
        student_ids=[row.student_id],
    )
    return _submission_read(session, row, homework=homework)


# ---------------------------------------------------------------------------
# The review board
# ---------------------------------------------------------------------------


def list_submissions(
    session: Session, section_id: UUID | None = None
) -> list[SubmissionItemRead]:
    """The review board: one line per child per assignment.

    With a `section_id`, children who have not handed anything in appear too - as a row
    with **no submission id** and the status "Pending". That is what a teacher needs to
    see ("four children, three in"), and a row with no id is honestly un-gradeable.
    """
    if section_id is None:
        return [
            _submission_read(session, row)
            for row in repository.get_all_submissions(session)
        ]

    homework = repository.get_homework_by_section(session, section_id)
    by_pair = {
        (row.homework_id, row.student_id): row
        for row in repository.get_submissions_for_section(session, section_id)
    }
    students = list(
        session.exec(
            select(Student).where(
                Student.classroom_id == section_id,
                Student.deactivated_at.is_(None),
            )
        ).all()
    )
    rows: list[SubmissionItemRead] = []
    for assignment in homework:
        for student in students:
            stored = by_pair.get((assignment.id, student.id))
            if stored is not None:
                rows.append(
                    _submission_read(
                        session, stored, homework=assignment, student=student
                    )
                )
                continue
            rows.append(
                SubmissionItemRead(
                    id=None,
                    homeworkId=assignment.id,
                    homeworkTitle=assignment.title,
                    studentId=student.id,
                    student=_student_name(session, student),
                    sectionId=section_id,
                    subject=_subject_name(session, assignment.subject_id),
                    status="Pending",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# The diary
# ---------------------------------------------------------------------------


def create_class_log(session: Session, log_in: ClassLogCreate, user) -> ClassLogRead:
    """Write one line of a class-section's day.

    A line that names a period must name **this section's** period: a log written
    against another room's slot would put work on a teacher who was somewhere else.
    The unique keys then refuse a second line for the same day and period (`409`).
    """
    from app.domains.academic.classroom.timetable.models import TimetablePeriod

    if session.get(Classroom, log_in.section_id) is None:
        raise HTTPException(status_code=404, detail="Class section not found")
    if log_in.timetableperiod_id is not None:
        period = session.get(TimetablePeriod, log_in.timetableperiod_id)
        if period is None:
            raise HTTPException(status_code=404, detail="Timetable period not found")
        if period.classroom_id != log_in.section_id:
            raise HTTPException(
                status_code=422,
                detail="That period belongs to a different class-section.",
            )
    if (
        log_in.subject_id is not None
        and session.get(Subject, log_in.subject_id) is None
    ):
        raise HTTPException(status_code=404, detail="Subject not found")

    try:
        row = repository.create_class_log(session, log_in)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="That day already has a log line for this period.",
        ) from None
    return ClassLogRead(
        id=row.id,
        section_id=row.classroom_id,
        teacher_id=row.teacher_id,
        timetableperiod_id=row.timetableperiod_id,
        subject_id=row.subject_id,
        date=row.date,
        note=row.note,
    )


def get_class_log_by_section(session: Session, section_id: UUID) -> list[ClassLogRead]:
    return [
        ClassLogRead(
            id=row.id,
            section_id=row.classroom_id,
            teacher_id=row.teacher_id,
            timetableperiod_id=row.timetableperiod_id,
            subject_id=row.subject_id,
            date=row.date,
            note=row.note,
        )
        for row in repository.get_class_log_by_section(session, section_id)
    ]


def _period_text(session: Session, timetableperiod_id: UUID | None) -> str:
    """`"09:50-10:35"` for a per-period line, `""` for the day-level one."""
    if timetableperiod_id is None:
        return ""
    from app.domains.academic.classroom.timetable.models import TimetablePeriod

    period = session.get(TimetablePeriod, timetableperiod_id)
    if period is None:
        return ""
    start = period.start_time.strftime("%H:%M")
    end = period.end_time.strftime("%H:%M")
    return f"{start} - {end}"


def list_diary(
    session: Session, section_id: UUID | None = None
) -> list[DiaryEntryRead]:
    """The diary, newest first - one line per class-section per day or per period."""
    rows = (
        repository.get_class_log_by_section(session, section_id)
        if section_id is not None
        else repository.get_all_class_logs(session)
    )
    return [
        DiaryEntryRead(
            id=row.id,
            className=_section_label(session, row.classroom_id),
            date=row.date.isoformat(),
            day=row.date.strftime("%a"),
            subject=_subject_name(session, row.subject_id) or "",
            period=_period_text(session, row.timetableperiod_id),
            topic=row.note,
        )
        for row in rows
    ]
