"""What happens when a person stops being part of the school.

One vocabulary for two screens - the Students directory and the Staff Hiring screen -
because the buttons are the same three actions and must mean the same thing:

* **deactivate** - access is switched off and **nothing is deleted**. The roles that are
  the school's business come off the account; what the person *is* to the school as a
  family stays, and the login itself is only switched off when they hold no role at all.
  A teacher whose child studies here keeps signing in as a parent.
* **reactivate** - the roles that were withdrawn on that day come back, exactly as they
  were, and the login is switched on again.
* **delete** - only for a record the school never really had. Anything with history
  behind it (a register, a payslip) refuses the delete with `409`; the answer says
  "deactivate instead", because that is what keeps the history explainable.

The rules themselves live with the rows they touch - `staff/lifecycle.py` and
`academic/classroom/students/lifecycle.py` - since only they know what has to be stamped.

Nothing here imports `contact` rules or the domain models: this module is the wording and
the shape of the answer, so both screens say the same sentence.
"""

from datetime import date

from pydantic import BaseModel

from app.core.text import CanonicalRequest

#: Roles a deactivation leaves alone: being a parent or a student here is a family
#: matter, not employment, and a platform administrator is not this school's employee.
KEEP_ON_DEACTIVATE: tuple[str, ...] = ("guardian", "student", "system_admin")

#: The two things the buttons do.
ACTION_DEACTIVATED = "deactivated"
ACTION_REACTIVATED = "reactivated"


class LifecycleRequest(CanonicalRequest):
    """Body of a deactivate call: the last day they were here, and why.

    Both are optional - the office may simply switch the record off - and both are kept
    so that "why is this person inactive?" has an answer months later.
    """

    left_on: date | None = None
    reason: str | None = None


class LifecycleRead(BaseModel):
    """What the screen needs to say after the button was pressed.

    `kind` is `staff` or `student`; `action` is what just happened. `rolesWithdrawn` and
    `rolesRestored` name the roles, `rolesKept` the ones the action deliberately left
    (`guardian` - they are still that child's parent), and the login flags say whether
    the account was left, switched off or brought back.
    """

    id: str
    kind: str
    name: str
    action: str
    leftOn: str | None = None
    deactivatedAt: str | None = None
    reason: str | None = None
    rolesWithdrawn: list[str] = []
    rolesRestored: list[str] = []
    rolesKept: list[str] = []
    loginKept: bool = True
    loginActive: bool = True
    loginEmail: str | None = None
    message: str = ""


def school_roles(codenames: list[str] | tuple[str, ...]) -> list[str]:
    """The roles a deactivation withdraws - everything the school gave the person."""
    return [name for name in codenames if name not in KEEP_ON_DEACTIVATE]


def kept_roles(codenames: list[str] | tuple[str, ...]) -> list[str]:
    """The roles a deactivation leaves in place (the family side of the person)."""
    return [name for name in codenames if name in KEEP_ON_DEACTIVATE]


def joined(names: list[str]) -> str:
    """`['teacher', 'guardian']` -> `"teacher and guardian"` (for the sentence)."""
    cleaned = [name for name in names if name]
    if not cleaned:
        return "nothing"
    if len(cleaned) == 1:
        return cleaned[0]
    return ", ".join(cleaned[:-1]) + " and " + cleaned[-1]


def release_login(session, user_id, *, withdraw: list[str]) -> bool:
    """Take the named roles off a login, and delete it only if nothing is left.

    The person is leaving one part of the school, not necessarily the school: a parent
    whose child has left is still a parent here, and a teacher who was let go may still
    have a child in Class 6. So the roles that went with the deleted record come off, and
    the login is deleted **only** when nothing remains for it to open.

    Returns `True` when the login itself was removed.
    """
    from app.core.logins import delete_login
    from app.domains.auth.roles import role_codenames, revoke_roles
    from app.domains.admin.users.models import User

    user = session.get(User, user_id) if user_id else None
    if user is None:
        return False
    revoke_roles(session, user, withdraw)
    if role_codenames(session, user.id):
        return False  # they are still somebody here - the login stays
    return delete_login(session, user.id)
