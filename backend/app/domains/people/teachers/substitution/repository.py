"""Reads and writes behind the cover board.

Every query here is **set-shaped**: a day's timetable, a day's assignments, the
teachers of one subject, the names of the people involved. The board asks about
forty periods at once, and a query per period is how a screen that felt instant on
a laptop takes seconds against a hosted database.

The writes are deliberately small: `ensure_request` upserts the absence, and the
assignment itself is inserted by the service so the unique key can answer `409`.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.models import TeacherSubject

from .models import SubstitutionAssignment, SubstitutionRequest


def weekday_key(on_date: date) -> DayOfWeek:
    """The timetable's own word for `on_date`'s weekday (`monday` ... `sunday`)."""
    return DayOfWeek(on_date.strftime("%A").lower())


# --- the timetable ----------------------------------------------------------


def periods_on_weekday(
    session: Session, day: DayOfWeek, employee_ids: list[UUID] | None = None
) -> list[TimetablePeriod]:
    """Every period on that weekday, oldest first - one query for the whole board.

    Narrowing to some teachers is what the board asks for; the clash check wants the
    whole school's day, because a candidate's clash is their own period in another
    room.
    """
    statement = select(TimetablePeriod).where(TimetablePeriod.day_of_week == day)
    if employee_ids is not None:
        if not employee_ids:
            return []
        statement = statement.where(TimetablePeriod.teacher_id.in_(employee_ids))
    return list(
        session.exec(
            statement.order_by(TimetablePeriod.start_time)  # type: ignore[arg-type]
        ).all()
    )


def period(session: Session, period_id: UUID) -> TimetablePeriod | None:
    """One slot by its own id."""
    return session.get(TimetablePeriod, period_id)


def teacher_ids_for_subject(
    session: Session, classroom_subject_id: UUID | None
) -> list[UUID]:
    """Who may be offered a period of this section subject.

    A subject that still carries a school-wide qualification (`classroomsubject.subject_id`
    with `teachersubject` rows) keeps that list, so a colleague who does not teach Physics
    is not a candidate for a Physics period. A subject created by name has no such list -
    any active teacher can take any subject - so the pool is every active teacher and the
    engine's clash/leave/load rules decide. (Phase 4 removes the legacy gate entirely.)
    """
    course = (
        session.get(ClassroomSubject, classroom_subject_id)
        if classroom_subject_id
        else None
    )
    if course is not None and course.subject_id is not None:
        qualified = list(
            session.exec(
                select(TeacherSubject.teacher_id).where(
                    TeacherSubject.subject_id == course.subject_id
                )
            ).all()
        )
        if qualified:
            return qualified
    return list(
        session.exec(
            select(Employee.id).where(
                Employee.left_on.is_(None), Employee.deactivated_at.is_(None)
            )
        ).all()
    )


def subject_names(
    session: Session, classroom_subject_ids: list[UUID | None]
) -> dict[UUID, str]:
    """`{classroom_subject_id: name}` in one query."""
    wanted = [item for item in dict.fromkeys(classroom_subject_ids) if item]
    if not wanted:
        return {}
    rows = session.exec(
        select(ClassroomSubject.id, ClassroomSubject.name).where(
            ClassroomSubject.id.in_(wanted)
        )
    ).all()
    return dict(rows)


# --- people -----------------------------------------------------------------


def employees(session: Session, employee_ids: list[UUID]) -> dict[UUID, Employee]:
    """`{employee_id: Employee}` in one query."""
    wanted = [employee_id for employee_id in dict.fromkeys(employee_ids) if employee_id]
    if not wanted:
        return {}
    rows = session.exec(select(Employee).where(Employee.id.in_(wanted))).all()
    return {employee.id: employee for employee in rows}


def employees_by_user_ids(
    session: Session, user_ids: list[UUID]
) -> dict[UUID, Employee]:
    """`{user_id: Employee}` - leave is keyed by user, the timetable by employee."""
    wanted = [user_id for user_id in dict.fromkeys(user_ids) if user_id]
    if not wanted:
        return {}
    rows = session.exec(select(Employee).where(Employee.user_id.in_(wanted))).all()
    return {employee.user_id: employee for employee in rows if employee.user_id}


# --- the two tables ---------------------------------------------------------


def assignments_on(session: Session, on_date: date) -> list[SubstitutionAssignment]:
    """Every cover arranged for one date."""
    return list(
        session.exec(
            select(SubstitutionAssignment).where(
                SubstitutionAssignment.on_date == on_date
            )
        ).all()
    )


def assignment(session: Session, assignment_id: UUID) -> SubstitutionAssignment | None:
    """One cover by its own id (`404` handled by the caller)."""
    return session.get(SubstitutionAssignment, assignment_id)


def assignments_for_employee(
    session: Session, employee_id: UUID, on_date: date
) -> list[SubstitutionAssignment]:
    """The covers *this* person is walking into that day (their own extra load)."""
    return list(
        session.exec(
            select(SubstitutionAssignment).where(
                SubstitutionAssignment.substitute_employee_id == employee_id,
                SubstitutionAssignment.on_date == on_date,
            )
        ).all()
    )


def request_on(
    session: Session, *, employee_id: UUID, on_date: date
) -> SubstitutionRequest | None:
    """The absence row for this person on this day, if one has been written."""
    return session.exec(
        select(SubstitutionRequest).where(
            SubstitutionRequest.employee_id == employee_id,
            SubstitutionRequest.on_date == on_date,
        )
    ).first()


def requests_on(session: Session, on_date: date) -> list[SubstitutionRequest]:
    """Every written absence for one date."""
    return list(
        session.exec(
            select(SubstitutionRequest).where(SubstitutionRequest.on_date == on_date)
        ).all()
    )


def ensure_request(
    session: Session,
    *,
    employee_id: UUID,
    on_date: date,
    reason: str,
    note: str | None,
    leave_request_id: UUID | None,
    user_id: UUID | None,
) -> SubstitutionRequest:
    """The absence row, created on the first cover arranged for it.

    Created here rather than on the board's `GET`: a read must not write, and the
    board can say everything it needs from the leave itself. The row appears when
    somebody actually arranges cover, which is the moment "why" stops being derivable
    (a leave can later be edited; a training day never had a leave row).
    """
    row = request_on(session, employee_id=employee_id, on_date=on_date)
    if row is None:
        row = SubstitutionRequest(
            employee_id=employee_id,
            on_date=on_date,
            reason=reason,
            note=note,
            leave_request_id=leave_request_id,
            created_by_user_id=user_id,
        )
    else:
        # The reason may have been a placeholder ("Leave") before the leave was
        # approved; the latest statement of it wins.
        row.reason = reason or row.reason
        row.note = note if note is not None else row.note
        row.leave_request_id = leave_request_id or row.leave_request_id
    session.add(row)
    return row
