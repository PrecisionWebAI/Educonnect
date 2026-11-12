"""Who the staff directory may show this caller.

`teachers.read` is a permission a lot of people legitimately hold - the front
office needs a teacher's number, the accountant needs to know who to ask about a
bill. What it must **not** mean is "every teacher can page through the whole
roster", which is what it used to do: the list endpoint had no scope check at
all, so a teacher opening the directory read every colleague's phone, email and
class load.

So the permission decides *whether* somebody may read the directory and this
module decides *whose* rows they get:

* a person who holds any other role as well (teacher + accountant, teacher +
  guardian) sees the roster - a second role widens access, never narrows it;
* a teacher and nothing else sees their own record, which is the self-service
  part of the same screen.

The query scope (which school) is not decided here: the tenant listeners in
`app/core/db.py` already bind every read to the session's school.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.admin.users.models import User
from app.domains.auth.roles import role_codenames, roles_of
from app.domains.people.staff.models import Employee

#: The one role whose access is confined to its own record.
SELF_ONLY_ROLES = frozenset({"teacher"})


def visible_employee_ids(session: Session, user: User | None) -> set[UUID] | None:
    """The employee ids this caller may read, or ``None`` for "the whole school".

    ``None`` rather than "all ids gathered" keeps the database doing the
    filtering: the repository turns it into no extra `WHERE` at all instead of a
    thousands-long `IN` list.
    """
    if user is None:
        return None

    held = roles_of(user) or set(role_codenames(session, user.id))
    if held and held <= SELF_ONLY_ROLES:
        own = session.exec(
            select(Employee.id).where(Employee.user_id == user.id)
        ).first()
        return {own} if own is not None else set()
    # Anything else (including a caller whose roles did not load) reads the
    # school's roster: the permission check that already passed is the decision.
    return None
