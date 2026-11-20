"""Where a student sits - the **one** writer for a placement.

Two rows say which class a child is in, and they must never disagree (Rule 1):

* `student.classroom_id` - the placement that is true **today** (the directory, the
  register and the marks all read it);
* `enrollment` - the same fact **per session**, which is what lets a report say
  "Class 9-A in 2025-26, Class 10-B in 2026-27" without rewriting the first one.

Every path that moves a child (admission, the edit modal, a class-section move) calls
`place_student`; nothing else writes `student.classroom_id`. The lifecycle buttons
call `set_enrollment_status`, so "left the roll" also reads as `left` in the year's
history instead of the two drifting apart.

`academic_year` is the school's own session row (`is_current`). A school that has not
opened one yet gets it **here**, from the calendar: an Indian session runs April ->
March, so 14 Nov 2026 belongs to "2026-27". Creating it is deliberate and
idempotent - `enrollment.academic_year_id` is NOT NULL, so without the year there is
nowhere to record the placement, and a second place to keep the class is exactly the
drift this module exists to prevent.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.students.models import Enrollment, Student
from app.domains.admin.settings.models import AcademicYear
from app.domains.auth.models import utcnow


def current_academic_year(session: Session, today: date | None = None) -> AcademicYear:
    """The current academic year - opened on first use by onboarding.

    Kept as a thin wrapper so existing callers keep their name; the rule lives in
    `academic_year_context.ensure_current_academic_year` (current row, then a row
    covering today, then create).
    """
    from app.domains.admin.settings.academic_year_context import (
        ensure_current_academic_year,
    )

    return ensure_current_academic_year(session, today)


def place_student(
    session: Session,
    student: Student,
    classroom_id: UUID | None,
    *,
    year: AcademicYear | None = None,
    update_current: bool = True,
    commit: bool = True,
) -> Enrollment | None:
    """Put the student in `classroom_id`, for today **and** for one academic year.

    `year` defaults to the current year; a future admission can pass the target year
    with `update_current=False`, so the enrollment is recorded without moving today's
    class placement. Both facts are committed together, so a move cannot leave the
    student row saying one class and the year's history another. A bulk caller passes
    `commit=False` to keep the whole batch in one transaction.
    """
    if update_current:
        student.classroom_id = classroom_id
    session.add(student)

    if classroom_id is None:
        if commit:
            session.commit()
            session.refresh(student)
        else:
            session.flush()
        return None

    target_year = year or current_academic_year(session)
    statement = select(Enrollment).where(
        Enrollment.student_id == student.id,
        Enrollment.academic_year_id == target_year.id,
    )
    enrollment = session.exec(statement).first()
    if enrollment is None:
        enrollment = Enrollment(
            student_id=student.id,
            classroom_id=classroom_id,
            academic_year_id=target_year.id,
            status="active",
            joined_on=date.today(),
            school_id=tenant_of(session),
        )
        session.add(enrollment)
    else:
        # A transfer inside the same session is an **update**, not a second row: the
        # roll count must not double-count a child.
        enrollment.classroom_id = classroom_id
        enrollment.updated_at = utcnow()
        if enrollment.status == "left":
            enrollment.status = "active"
            enrollment.left_on = None
        session.add(enrollment)

    if not commit:
        session.flush()
        return enrollment

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(statement).first()
        if existing is None:  # pragma: no cover - uq_enrollment_school_student_year
            raise
        existing.classroom_id = classroom_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    session.refresh(student)
    session.refresh(enrollment)
    return enrollment


def backfill_current_enrollments(
    session: Session, year: AcademicYear | None = None
) -> int:
    """Create the current year's enrollment for students who predate the table.

    A school that was already running before `enrollment` existed has students but
    no per-year row. The default-current-year bootstrap calls this once; a student
    with no class-section has nothing to place, so it is skipped.
    """
    target = year or current_academic_year(session)
    have = set(
        session.exec(
            select(Enrollment.student_id).where(
                Enrollment.academic_year_id == target.id
            )
        ).all()
    )
    students = session.exec(
        select(Student).where(Student.classroom_id.is_not(None))
    ).all()
    added = 0
    for student in students:
        if student.id in have:
            continue
        separated = bool(student.separation_date or student.separation_reason)
        session.add(
            Enrollment(
                student_id=student.id,
                classroom_id=student.classroom_id,
                academic_year_id=target.id,
                status="left" if separated else "active",
                joined_on=student.created_on,
                left_on=student.separation_date if separated else None,
                school_id=tenant_of(session),
            )
        )
        added += 1
    if added:
        session.commit()
    return added


def set_enrollment_status(session: Session, student: Student, status: str) -> None:
    """Make the year's history agree with the roll: `active` or `left`.

    Called by the lifecycle buttons. A student nobody placed yet has no enrollment
    row to correct, so that case simply returns.
    """
    year = current_academic_year(session)
    enrollment = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.academic_year_id == year.id,
        )
    ).first()
    if enrollment is None:
        return
    enrollment.status = status
    enrollment.left_on = date.today() if status == "left" else None
    enrollment.updated_at = utcnow()
    session.add(enrollment)
    session.commit()
