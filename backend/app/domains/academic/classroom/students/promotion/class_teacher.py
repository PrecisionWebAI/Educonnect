"""The current class teacher, read from the year's assignment first.

`classroom.class_teacher_id` is kept as the fast pointer for older screens, but
the year's `classteacherassignment` row is the history. New reads go through this
helper so switching the academic year picks that year's teacher, and a section
whose teacher was changed on a date shows the right person for the current year.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Classroom
from app.domains.admin.settings.academic_year_context import current_academic_year_id

from .models import ClassTeacherAssignment


def current_class_teacher_id(session: Session, classroom_id: UUID) -> UUID | None:
    """The teacher who runs `classroom_id` in the current academic year."""
    year_id = current_academic_year_id(session)
    if year_id is not None:
        assignment = session.exec(
            select(ClassTeacherAssignment)
            .where(
                ClassTeacherAssignment.classroom_id == classroom_id,
                ClassTeacherAssignment.academic_year_id == year_id,
                ClassTeacherAssignment.effective_to.is_(None),
            )
            .order_by(ClassTeacherAssignment.effective_from.desc())
        ).first()
        if assignment is not None:
            return assignment.teacher_id

    # A school that has not opened a year yet (or a legacy row) keeps the pointer.
    room = session.get(Classroom, classroom_id)
    return room.class_teacher_id if room is not None else None


def class_teacher_classroom_ids(session: Session, teacher_id: UUID) -> set[UUID]:
    """The class-sections this teacher runs in the current academic year."""
    year_id = current_academic_year_id(session)
    if year_id is not None:
        rows = session.exec(
            select(ClassTeacherAssignment.classroom_id).where(
                ClassTeacherAssignment.teacher_id == teacher_id,
                ClassTeacherAssignment.academic_year_id == year_id,
                ClassTeacherAssignment.effective_to.is_(None),
            )
        ).all()
        if rows:
            return set(rows)

    from app.domains.academic.classroom.academics.models import Classroom

    return set(
        session.exec(
            select(Classroom.id).where(Classroom.class_teacher_id == teacher_id)
        ).all()
    )


def class_teacher_user_id(session: Session, classroom_id: UUID) -> UUID | None:
    """The login of the current class teacher, when they have one."""
    from app.domains.people.staff.models import Employee

    teacher_id = current_class_teacher_id(session, classroom_id)
    if teacher_id is None:
        return None
    employee = session.get(Employee, teacher_id)
    return employee.user_id if employee is not None else None


def class_teacher_rooms_for(
    session: Session, teacher_ids: list[UUID] | None = None
) -> dict[UUID, list[UUID]]:
    """`{teacher id: [class-section ids]}` they run in the current academic year - in bulk.

    The batch form of `class_teacher_classroom_ids`, for screens that ask about many people
    (the Course list, the substitution board) and cannot afford a query each. The year's
    `classteacherassignment` rows are the record; `classroom.class_teacher_id` is only the
    legacy pointer, so it counts **only for a section with no assignment row at all** this
    year - otherwise a stale pointer would name somebody whose assignment has ended.
    `teacher_ids=None` answers for everybody.
    """
    wanted = None if teacher_ids is None else set(teacher_ids)
    year_id = current_academic_year_id(session)
    result: dict[UUID, list[UUID]] = {}
    with_assignment: set[UUID] = set()

    if year_id is not None:
        open_rows = session.exec(
            select(ClassTeacherAssignment.teacher_id, ClassTeacherAssignment.classroom_id).where(
                ClassTeacherAssignment.academic_year_id == year_id,
                ClassTeacherAssignment.effective_to.is_(None),
            )
        ).all()
        for teacher_id, room_id in open_rows:
            with_assignment.add(room_id)
            if wanted is None or teacher_id in wanted:
                result.setdefault(teacher_id, []).append(room_id)
        # A section whose assignment was closed this year has no class teacher now, whatever
        # the legacy pointer still says.
        with_assignment.update(
            session.exec(
                select(ClassTeacherAssignment.classroom_id).where(
                    ClassTeacherAssignment.academic_year_id == year_id
                )
            ).all()
        )

    pointer = select(Classroom.class_teacher_id, Classroom.id).where(
        Classroom.class_teacher_id.is_not(None)  # type: ignore[union-attr]
    )
    for teacher_id, room_id in session.exec(pointer).all():
        if room_id in with_assignment:
            continue
        if wanted is None or teacher_id in wanted:
            result.setdefault(teacher_id, []).append(room_id)
    return result
