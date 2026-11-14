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


#: The roles that may change anybody's profile in the school.
EDIT_ANY_ROLE = frozenset(
    {"system_admin", "school_admin", "principal", "vice_principal"}
)

#: The role that may change a profile **inside its own department** only. An HOD
#: adding a colleague's B.Ed is part of the job; rewriting another department's
#: record is not.
EDIT_DEPARTMENT_ROLE = "hod"


def may_edit_profile(session: Session, user: User | None, employee: Employee) -> bool:
    """Whether this caller may change `employee`'s profile.

    `teachers.update` decides *whether* somebody may edit profiles; this decides
    *whose*, and it is checked on the server for every write. A teacher holds no
    edit right here at all - their own papers are filed through
    `may_upload_documents`, and their own qualifications are the office's record,
    not a self-service form.
    """
    if user is None:
        return False

    held = held_roles(session, user)
    if held & EDIT_ANY_ROLE:
        return True
    if EDIT_DEPARTMENT_ROLE not in held:
        return False

    own = session.exec(
        select(Employee.department).where(Employee.user_id == user.id)
    ).first()
    if not own or not employee.department:
        return False
    return own.strip().lower() == employee.department.strip().lower()


def held_roles(session: Session, user: User | None) -> set[str]:
    """The role codenames this caller holds, lower-case, from the token or the DB."""
    if user is None:
        return set()
    return set(roles_of(user) or set(role_codenames(session, user.id)))


# --- documents -------------------------------------------------------------


def may_read_documents(session: Session, user: User | None, employee: Employee) -> bool:
    """Reading somebody's files is reading their profile, at the same scope.

    A teacher-only account therefore reads its own dossier; a person holding any
    other role reads the school's (see `visible_employee_ids`).
    """
    visible = visible_employee_ids(session, user)
    return visible is None or employee.id in visible


def may_upload_documents(
    session: Session, user: User | None, employee: Employee
) -> bool:
    """The person may file **their own** papers; the office may file anyone's.

    This is the matrix's "own docs only" row, and it is deliberately wider than
    `may_edit_profile`: a teacher who brings a new police-verification certificate
    should not need an administrator to upload it for them. It stays narrow in the
    other direction - a teacher cannot file a paper on a colleague's profile.
    """
    if user is None:
        return False
    if employee.user_id == user.id:
        return True
    return may_edit_profile(session, user, employee)


#: The roles that may see a full Aadhaar, PAN or bank account: the people who run
#: payroll and hold the school's confidential file. The vice-principal runs
#: teaching, not pay, and an HOD runs a department - so neither is here.
KYC_ROLES = frozenset({"system_admin", "school_admin", "principal"})


def may_view_kyc(session: Session, user: User | None) -> bool:
    """Whether this caller may ask for the unmasked KYC values.

    Holding the right is only half of it: `service.kyc_read` also needs the
    request to say `reveal`, and it writes an audit line when the answer is the
    full number.
    """
    return bool(held_roles(session, user) & KYC_ROLES)


# --- workload --------------------------------------------------------------
#
# Who decides the school's week. Setting "a full load is 24 periods" and handing
# out exam or gate duties is the office's decision about the whole school's time,
# not a department's: an HOD may read the matrix for their staff
# (`teachers.view_workload`) but must not reshape the week everybody is measured
# against. The vice-principal is here because they run teaching day to day - the
# same reason Phase 3 stripped KYC and the audit feed from them and nothing else.
WORKLOAD_ROLES = frozenset(
    {"system_admin", "school_admin", "principal", "vice_principal"}
)


def may_manage_workload(session: Session, user: User | None) -> bool:
    """Whether this caller may set the capacity rule or add/remove a duty."""
    return bool(held_roles(session, user) & WORKLOAD_ROLES)


# --- attendance -------------------------------------------------------------
#
# Who fills the daily register. It is the office's book, not a class register: the
# same people who run the staff roll write it, and a department head - who may read
# their department's register - does not get to mark a colleague present. The
# vice-principal is here for the same reason they are in `WORKLOAD_ROLES`: they
# run the day, and the register is how the day is recorded.
#
# `staff_attendance.mark` (today's roll) and `staff_attendance.update` (amending a
# day already marked) are separate codenames so a school can later give marking to
# a coordinator without giving them the right to rewrite history; for now both
# resolve to this one list, and the split costs a line rather than a redesign.
ATTENDANCE_ROLES = frozenset(
    {"system_admin", "school_admin", "principal", "vice_principal"}
)


def may_mark_attendance(session: Session, user: User | None) -> bool:
    """Whether this caller may mark or amend the staff register."""
    return bool(held_roles(session, user) & ATTENDANCE_ROLES)
