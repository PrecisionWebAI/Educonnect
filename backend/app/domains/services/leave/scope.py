"""Who may decide a leave, and who may shape the school's policy.

The route guards (`RequirePermission`) decide *whether* somebody reaches the
workflow; this module decides *whose* request they may touch and *which* decision
is theirs. That second question is not a permission: two people can hold
`leave.approve` and only one of them may approve a given request (nobody approves
their own), so the rule has to live where the row is, not on the route.

The roles are compared as **codenames**, the same way `people/teachers/scope.py`
does it, rather than through the permission tables: a service called by a script or
a test then has one, predictable answer, and the matrix in `permissions.py` remains
the single place a school's rights are actually granted.
"""

from sqlmodel import Session

from app.domains.admin.users.models import User
from app.domains.auth.roles import role_codenames, roles_of

#: The roles that approve, reject and cancel on somebody else's behalf. This is the
#: same set `permissions.py` gives `leave.approve` to (director, school admin,
#: principal, vice-principal, HOD) - a department head decides their department's
#: leave, the office decides the school's.
DECIDE_ROLES = frozenset(
    {"system_admin", "director", "school_admin", "principal", "vice_principal", "hod"}
)

#: The roles that write the school's leave policy. Narrower than `DECIDE_ROLES` on
#: purpose: granting days is an entitlement decision about every contract in the
#: school, not a decision about one Tuesday.
POLICY_ROLES = frozenset({"system_admin", "director", "school_admin", "principal"})


def held_roles(session: Session, user: User | None) -> set[str]:
    """The codenames this caller holds, from the token or (if absent) the database."""
    if user is None:
        return set()
    return set(roles_of(user) or role_codenames(session, user.id))


def may_decide(session: Session, user: User | None) -> bool:
    """Whether this caller may approve, reject or cancel somebody else's leave."""
    return bool(held_roles(session, user) & DECIDE_ROLES)


def may_manage_policy(session: Session, user: User | None) -> bool:
    """Whether this caller may set the school's leave types and their grants."""
    return bool(held_roles(session, user) & POLICY_ROLES)
