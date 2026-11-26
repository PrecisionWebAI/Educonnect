"""May this person take that class-section's attendance on that day?

When a class teacher is away the office hands their class's daily attendance to somebody
(see `service.set_attendance_access`). This is the one question the rest of the app asks:
the class-section page and the attendance save call it, nothing else.

It is deliberately **narrow**. A grant is for one class-section and one date and unlocks
exactly two things - opening that section and saving its register. It never makes the
person a class teacher, never reaches their other classes, and never lasts past the day.
Only an **approved** grant counts: until the office signs it the person has no access.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels

from .models import ClassAttendanceAccess


def _employee_id(session: Session, user: User | None) -> UUID | None:
    if user is None:
        return None
    return session.exec(select(Employee.id).where(Employee.user_id == user.id)).first()


def has_access(
    session: Session, user: User | None, classroom_id: UUID, on_date: date
) -> bool:
    """True when `user` holds an approved grant for this class-section on this date."""
    employee_id = _employee_id(session, user)
    if employee_id is None:
        return False
    return (
        session.exec(
            select(ClassAttendanceAccess.id).where(
                ClassAttendanceAccess.classroom_id == classroom_id,
                ClassAttendanceAccess.on_date == on_date,
                ClassAttendanceAccess.delegate_employee_id == employee_id,
                ClassAttendanceAccess.status == labels.APPROVED,
            )
        ).first()
        is not None
    )


def approved_for(
    session: Session, user: User | None, on_date: date
) -> list[ClassAttendanceAccess]:
    """The approved grants this person holds on one day - what their class list shows."""
    employee_id = _employee_id(session, user)
    if employee_id is None:
        return []
    return list(
        session.exec(
            select(ClassAttendanceAccess).where(
                ClassAttendanceAccess.on_date == on_date,
                ClassAttendanceAccess.delegate_employee_id == employee_id,
                ClassAttendanceAccess.status == labels.APPROVED,
            )
        ).all()
    )
