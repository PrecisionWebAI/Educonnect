"""The staff side of a person's life here: hired, let go, re-hired, removed.

The hire itself lives in `service.py` (the form writes the record). This module is what
happens afterwards, and the three actions are deliberately different:

* **deactivate** (`deactivate_profile`) - the person stops working here. Their staff roles
  come off the account (`user_role`, remembered in `employee.deactivated_roles`), the day
  they left is stamped, and their staff access is gone on the next request because the
  roles are reloaded per request. **Nothing is deleted**, so the salary register, the
  timetable of last term and the payslips still explain themselves. Their login is only
  switched off when they hold no other role - a teacher whose child studies here keeps
  signing in as a parent.
* **reactivate** (`reactivate_profile`) - the roles that were withdrawn that day come back
  exactly as they were, and the login signs in again.
* **delete** (`delete_profile`) - only for a row the school never really had. It removes
  that person's **own** rows (staff record, salary, subjects, staff roles); a login that
  still opens something else (their children, for instance) stays. Anything with history
  behind it refuses the delete with `409`: deactivate instead.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.lifecycle import (
    ACTION_DEACTIVATED,
    ACTION_REACTIVATED,
    LifecycleRead,
    LifecycleRequest,
    joined,
    kept_roles,
    release_login,
    school_roles,
)
from app.domains.admin.users.models import User
from app.domains.auth.models import utcnow
from app.domains.auth.roles import (
    ensure_primary,
    grant_role,
    revoke_roles,
    role_codenames,
)
from app.domains.operations.salary.models import EmployeeSalary
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.models import TeacherSubject


def _get_or_404(session: Session, profile_id: UUID) -> Employee:
    profile = session.get(Employee, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return profile


def _login_story(*, user: User | None, kept: list[str], switched_off: bool) -> str:
    """One sentence about what happened to the login (or why there is none)."""
    if user is None:
        return "They have no login of their own."
    if switched_off:
        return f"Their login ({user.email}) is switched off - it opened nothing else."
    return (
        f"They keep signing in as {joined(kept)} on {user.email}: the login stays, "
        "their staff access does not."
    )


def deactivate_profile(
    session: Session, profile_id: UUID, payload: LifecycleRequest | None = None
) -> LifecycleRead:
    """Switch the staff side of this person off. Nothing is deleted."""
    profile = _get_or_404(session, profile_id)
    if profile.deactivated_at is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This person's staff access is already off "
                f"({profile.deactivated_at:%d %b %Y})."
            ),
        )

    user = session.get(User, profile.user_id) if profile.user_id else None
    held = role_codenames(session, user.id) if user is not None else []
    withdrawn = school_roles(held)
    kept = kept_roles(held)

    if user is not None:
        revoke_roles(session, user, withdrawn)
        switched_off = not role_codenames(session, user.id)
        if switched_off:
            user.is_active = False
            session.add(user)
            session.commit()
    else:
        switched_off = False

    left_on = (payload.left_on if payload else None) or date.today()
    profile.left_on = left_on
    profile.deactivated_at = utcnow()
    profile.deactivated_roles = ", ".join(withdrawn) or None
    session.add(profile)
    session.commit()
    session.refresh(profile)

    story = _login_story(user=user, kept=kept, switched_off=switched_off)
    return LifecycleRead(
        id=str(profile.id),
        kind="staff",
        name=user.full_name
        if user is not None
        else (profile.email or profile.employee_code),
        action=ACTION_DEACTIVATED,
        leftOn=left_on.isoformat(),
        deactivatedAt=profile.deactivated_at.isoformat(),
        reason=(payload.reason if payload else None),
        rolesWithdrawn=withdrawn,
        rolesKept=kept,
        loginKept=not switched_off,
        loginActive=bool(user.is_active) if user is not None else False,
        loginEmail=user.email if user is not None else None,
        message=(
            f"{profile.employee_code} is off the staff roll"
            + (f" as of {left_on:%d %b %Y}" if left_on else "")
            + (f": {joined(withdrawn)} access removed. " if withdrawn else ". ")
            + story
        ),
    )


def reactivate_profile(
    session: Session, profile_id: UUID, payload: LifecycleRequest | None = None
) -> LifecycleRead:
    """Put the person back on the staff roll, with exactly the roles they had."""
    profile = _get_or_404(session, profile_id)
    if profile.deactivated_at is None:
        raise HTTPException(
            status_code=409, detail="This person's staff access is already on."
        )

    wanted = [
        name.strip()
        for name in (profile.deactivated_roles or "").split(",")
        if name.strip()
    ]
    user = session.get(User, profile.user_id) if profile.user_id else None
    restored: list[str] = []
    if user is not None:
        restored = [name for name in wanted if grant_role(session, user, name)]
        if not user.is_active:
            user.is_active = True
            session.add(user)
            session.commit()
        # If the withdrawn roles had been all they had, the account holds roles again and
        # needs a primary one to land on (`auth/roles.py::ensure_primary`).
        ensure_primary(session, user)

    profile.deactivated_at = None
    profile.left_on = None
    profile.deactivated_roles = None
    session.add(profile)
    session.commit()
    session.refresh(profile)

    held = role_codenames(session, user.id) if user is not None else []
    return LifecycleRead(
        id=str(profile.id),
        kind="staff",
        name=user.full_name
        if user is not None
        else (profile.email or profile.employee_code),
        action=ACTION_REACTIVATED,
        reason=(payload.reason if payload else None),
        rolesRestored=restored or wanted,
        rolesKept=kept_roles(held),
        loginKept=True,
        loginActive=bool(user.is_active) if user is not None else False,
        loginEmail=user.email if user is not None else None,
        message=(
            f"{profile.employee_code} is back on the staff roll"
            + (
                f": {joined(restored or wanted)} restored. "
                if (restored or wanted)
                else ". "
            )
            + (
                f"They sign in again on {user.email}."
                if user is not None
                else "They have no login of their own."
            )
        ),
    )


def delete_profile(session: Session, profile_id: UUID) -> None:
    """Remove an employee the school never really had (a hire entered by mistake).

    Only this person's **own** rows go: the staff record, their salary, their subjects and
    the staff roles. If they are still somebody here the login stays with the roles that
    are theirs - a teacher who was also a parent remains a parent, one login, no second
    account. The login itself is removed only when it was all they had.

    Anything else pointing at the person - timetable periods, homework, attendance, salary
    payments - refuses the delete (`409`) rather than being silently orphaned: that record
    is the only explanation of those registers, so the answer says to deactivate instead.
    """
    profile = _get_or_404(session, profile_id)
    user_id = profile.user_id

    for row in session.exec(
        select(EmployeeSalary).where(EmployeeSalary.employee_id == profile.id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(TeacherSubject).where(TeacherSubject.teacher_id == profile.id)
    ).all():
        session.delete(row)

    session.delete(profile)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "This employee still has timetable, homework, attendance or salary "
                "records pointing at them. Deactivate them instead - that keeps the "
                "register and the payslips explainable."
            ),
        ) from exc

    if user_id is None:
        return
    # The row is gone: the staff roles go with it, and the login too **only** if it
    # opened nothing else (`app/core/lifecycle.py::release_login`).
    release_login(
        session,
        user_id,
        withdraw=school_roles(role_codenames(session, user_id)),
    )
