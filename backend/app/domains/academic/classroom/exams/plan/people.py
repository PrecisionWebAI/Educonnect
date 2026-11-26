"""Who teaches what - the small lookups the exam screens share.

A section subject has no school-wide identity, so "assigned teacher" is read from the
**open** history row (`effective_to IS NULL`) of that one section subject. Everything
here is batched (one query for many subjects) so a date sheet of thirty rows costs the
same as one row.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Classroom, SubjectTeacher
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee


def employee_of(session: Session, user) -> UUID | None:
    """The `employee` row behind a login, when the person is staff."""
    if user is None or getattr(user, "id", None) is None:
        return None
    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    return employee.id if employee is not None else None


def assigned_teachers(session: Session, course_ids: set[UUID]) -> dict[UUID, UUID]:
    """`{section subject: employee}` for the teacher who holds each one **now**."""
    if not course_ids:
        return {}
    rows = session.exec(
        select(SubjectTeacher.classroom_subject_id, SubjectTeacher.teacher_id).where(
            SubjectTeacher.classroom_subject_id.in_(course_ids),
            SubjectTeacher.effective_to.is_(None),
        )
    ).all()
    return {course_id: teacher_id for course_id, teacher_id in rows if course_id}


def employee_names(session: Session, employee_ids: set[UUID]) -> dict[UUID, str]:
    """`{employee: full name}` for a set of employees, in one query."""
    if not employee_ids:
        return {}
    rows = session.exec(
        select(Employee.id, User.full_name)
        .join(User, User.id == Employee.user_id)
        .where(Employee.id.in_(employee_ids))
    ).all()
    return {employee_id: name for employee_id, name in rows}


def class_teacher_room_ids(session: Session, user) -> set[UUID]:
    """The class-sections this person is the **class teacher** of."""
    employee_id = employee_of(session, user)
    if employee_id is None:
        return set()
    return set(
        session.exec(
            select(Classroom.id).where(Classroom.class_teacher_id == employee_id)
        ).all()
    )
