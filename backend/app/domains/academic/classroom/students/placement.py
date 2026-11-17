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

#: The months an Indian school session covers (April -> March).
SESSION_START_MONTH = 4
SESSION_END_MONTH = 3


def _session_bounds(today: date) -> tuple[date, date, str]:
    """(`start`, `end`, "2026-27") for the session `today` falls in."""
    start_year = today.year if today.month >= SESSION_START_MONTH else today.year - 1
    start = date(start_year, SESSION_START_MONTH, 1)
    end = date(start_year + 1, SESSION_END_MONTH, 31)
    return start, end, f"{start_year}-{str(start_year + 1)[-2:]}"


def current_academic_year(session: Session, today: date | None = None) -> AcademicYear:
    """The session the screens treat as "now" - opened on first use.

    `is_current` is a flag, not "the latest start date": a school opens next year's
    dates in advance and must keep showing the year that is running. When no row is
    current, this one is created from the calendar; two processes racing for it
    settle on one row (`uq_academicyear_school_name`, plus the partial unique index
    that allows one current row per school) and the loser reads the winner's row.
    """
    found = session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()
    if found is not None:
        return found

    start, end, name = _session_bounds(today or date.today())
    year = AcademicYear(
        name=name,
        start_date=start,
        end_date=end,
        is_current=True,
        school_id=tenant_of(session),
    )
    session.add(year)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(AcademicYear).where(AcademicYear.name == name)
        ).first()
        if existing is None:  # pragma: no cover - the unique keys guarantee one
            raise
        return existing
    session.refresh(year)
    return year


def place_student(
    session: Session, student: Student, classroom_id: UUID | None
) -> Enrollment | None:
    """Put the student in `classroom_id`, for today **and** for this session.

    Returns the enrollment row it wrote (`None` when the placement was cleared and
    there is nothing to record). Both facts are committed together, so a move cannot
    leave the student row saying one class and the year's history another.
    """
    student.classroom_id = classroom_id
    session.add(student)

    if classroom_id is None:
        session.commit()
        session.refresh(student)
        return None

    year = current_academic_year(session)
    statement = select(Enrollment).where(
        Enrollment.student_id == student.id,
        Enrollment.academic_year_id == year.id,
    )
    enrollment = session.exec(statement).first()
    if enrollment is None:
        enrollment = Enrollment(
            student_id=student.id,
            classroom_id=classroom_id,
            academic_year_id=year.id,
            status="active",
            joined_on=date.today(),
            school_id=tenant_of(session),
        )
        session.add(enrollment)
    else:
        # A transfer inside the same session is an **update**, not a second row: the
        # roll count must not double-count a child.
        enrollment.classroom_id = classroom_id
        if enrollment.status == "left":
            enrollment.status = "active"
            enrollment.left_on = None
        session.add(enrollment)

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
    session.add(enrollment)
    session.commit()
