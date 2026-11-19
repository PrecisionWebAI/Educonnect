"""The one background nudge: a week that ended without a plan.

A reminder is **one row per section subject per week** (`dedupe_key`), sent to the
subject's current teacher. It never creates a plan and never changes a status; the
teacher opens the same popup the app already uses.
"""

from datetime import date

from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import room_label
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    PLAN_APPROVED,
    PLAN_SUBMITTED,
    ClassroomSubject,
    LessonPlan,
)
from app.domains.main.notifications import events
from app.domains.main.notifications.events import notify
from app.domains.people.staff.models import Employee

from . import completion, teaching_days


def remind_unsubmitted(session: Session) -> int:
    """Tell each current teacher about this month's finished-but-unplanned weeks."""
    year = completion.current_year(session)
    if year is None:
        return 0

    today = date.today()
    weeks = teaching_days.week_ranges(session, today.year, today.month)
    due = [week for week in weeks if week.end_date < today]
    if not due:
        return 0

    courses = list(
        session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.academic_year_id == year.id,
                ClassroomSubject.status == COURSE_ACTIVE,
            )
        ).all()
    )
    if not courses:
        return 0

    plans = {
        (plan.classroom_subject_id, plan.week_no): plan.status
        for plan in session.exec(
            select(LessonPlan).where(
                LessonPlan.academic_year_id == year.id,
                LessonPlan.year == today.year,
                LessonPlan.month == today.month,
            )
        ).all()
    }

    subjects = {
        subject.id: subject.name for subject in session.exec(select(Subject)).all()
    }
    sent = 0
    for course in courses:
        missing = [
            week
            for week in due
            if plans.get((course.id, week.week_no))
            not in (PLAN_SUBMITTED, PLAN_APPROVED)
        ]
        if not missing:
            continue

        assignment = session.exec(
            select(SubjectTeacher)
            .where(
                SubjectTeacher.classroom_id == course.classroom_id,
                SubjectTeacher.subject_id == course.subject_id,
                SubjectTeacher.effective_to.is_(None),
            )
            .order_by(SubjectTeacher.effective_from.desc())
        ).first()
        if assignment is None:
            continue
        employee = session.exec(
            select(Employee).where(Employee.id == assignment.teacher_id)
        ).first()
        if employee is None or employee.user_id is None:
            continue

        for week in missing:
            sent += notify(
                session,
                event=events.EVENT_COURSE_REMINDER,
                recipients=[employee.user_id],
                title="Lesson plan due",
                body=(
                    f"{subjects.get(course.subject_id, 'Subject')} · "
                    f"{room_label(session, course.classroom_id)} · "
                    f"Week {week.week_no} has ended without a plan."
                ),
                entity_type="classroom_subject",
                entity_id=course.id,
                dedupe_key=(
                    f"course:reminder:{course.id}:"
                    f"{today.year}-{today.month}-w{week.week_no}"
                ),
            )
    return sent
