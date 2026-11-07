"""The student side of a person's life here: on the roll, left, back again.

* **deactivate** (`deactivate_student`) - the child is off the roll. `deactivated_at` and
  `left_on` are stamped and the directory reads them as Inactive. **Their login is never
  switched off**: a child who left is still a family's child, and the account that usually
  signs in is the guardian's anyway. Nothing is deleted either - the registers, the marks
  and the fees of the years they were here stay readable.
* **reactivate** (`reactivate_student`) - the stamps are cleared and the child is on the
  roll again, with everything that was already theirs.

The hard delete is in `service.py`, next to the cascade it owns, because removing a child
really does remove their attendance, marks, fees, homework, diary, leaves and library
issues (and the class-section, when they were the last one in it). It follows the same
login rule as everywhere else (`app/core/lifecycle.py::release_login`) and refuses to run
at all when history has to stay - the office is told to deactivate instead.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.core.lifecycle import (
    ACTION_DEACTIVATED,
    ACTION_REACTIVATED,
    LifecycleRead,
    LifecycleRequest,
    joined,
)
from app.domains.auth.models import utcnow
from app.domains.students import repository
from app.domains.students.models import Student
from app.domains.users.models import User


def _get_or_404(session: Session, student_id: UUID) -> Student:
    student = repository.get_student_by_id(session, student_id=student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _name(session: Session, student: Student) -> str:
    user = session.get(User, student.user_id) if student.user_id else None
    return student.full_name or (user.full_name if user else "Student")


def _login_story(session: Session, student: Student) -> tuple[bool, str]:
    """(has a login, the sentence about it) - the student's login is never switched off."""
    user = session.get(User, student.user_id) if student.user_id else None
    if user is None:
        return False, "They sign in through their guardian's account."
    return True, f"Their own login ({user.email}) is untouched - a child who left the roll is still a child here."


def deactivate_student(
    session: Session, student_id: UUID, payload: LifecycleRequest | None = None
) -> LifecycleRead:
    """Take a child off the roll. Nothing is deleted and no login is switched off."""
    student = _get_or_404(session, student_id)
    if student.deactivated_at is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This student is already off the roll "
                f"({student.deactivated_at:%d %b %Y})."
            ),
        )

    left_on = (payload.left_on if payload else None) or date.today()
    student.deactivated_at = utcnow()
    student.left_on = left_on
    session.add(student)
    session.commit()
    session.refresh(student)

    has_login, story = _login_story(session, student)
    user = session.get(User, student.user_id) if student.user_id else None
    return LifecycleRead(
        id=str(student.id),
        kind="student",
        name=_name(session, student),
        action=ACTION_DEACTIVATED,
        leftOn=left_on.isoformat(),
        deactivatedAt=student.deactivated_at.isoformat(),
        reason=(payload.reason if payload else None),
        rolesWithdrawn=[],
        rolesKept=["student"],
        loginKept=True,
        loginActive=bool(user.is_active) if user is not None else False,
        loginEmail=user.email if (user is not None and has_login) else None,
        message=(
            f"{_name(session, student)} is off the roll as of {left_on:%d %b %Y}. "
            + story
        ),
    )


def reactivate_student(
    session: Session, student_id: UUID, payload: LifecycleRequest | None = None
) -> LifecycleRead:
    """Put the child back on the roll."""
    student = _get_or_404(session, student_id)
    if student.deactivated_at is None:
        raise HTTPException(
            status_code=409, detail="This student is already on the roll."
        )

    student.deactivated_at = None
    student.left_on = None
    session.add(student)
    session.commit()
    session.refresh(student)

    has_login, _ = _login_story(session, student)
    user = session.get(User, student.user_id) if student.user_id else None
    return LifecycleRead(
        id=str(student.id),
        kind="student",
        name=_name(session, student),
        action=ACTION_REACTIVATED,
        reason=(payload.reason if payload else None),
        rolesKept=["student"],
        loginKept=True,
        loginActive=bool(user.is_active) if user is not None else False,
        loginEmail=user.email if (user is not None and has_login) else None,
        message=f"{_name(session, student)} is back on the roll: {joined(['student'])} access is theirs again.",
    )
