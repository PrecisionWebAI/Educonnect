"""The words the staff screens print about a person's service - one place.

Three screens show the same three states (the directory, the workload matrix and
the summary tiles), and the badge in the table has to agree with the number in
the tile above it. Deriving them once here is what keeps that true.

The states are about the **relationship**, not about a login:

* ``Inactive`` - the school has taken them off the staff roll (a deactivation, or
  a left-on date). Their login may still work for another role.
* ``On Leave`` - on the roll, with an approved leave covering today.
* ``Active`` - on the roll and in today.

A switched-off login is deliberately **not** ``On Leave``: that is what the code
used to say (`"Active" if user.is_active else "On Leave"`), so a suspended
account and a teacher on medical leave were the same badge.
"""

from datetime import date

ACTIVE = "Active"
INACTIVE = "Inactive"
ON_LEAVE = "On Leave"

#: The order the directory's status filter offers, and the value it sends.
STATUSES = (ACTIVE, ON_LEAVE, INACTIVE)

#: The roles that stand in front of a class - i.e. who belongs in the Teachers &
#: Staff directory. A school's principal, vice-principal and HODs teach, so they
#: are teachers by post; an accountant, librarian, transport manager or support
#: staff member is staff but not a teacher, and listing them here would turn the
#: screen into "every employee".
#:
#: One definition, two readers: `people/teachers/repository.py` decides the
#: directory from it and `people/staff/service.py` uses it for the Hired tab's
#: `isTeacher` flag, so a hire cannot appear in one screen and not the other.
TEACHING_ROLES = ("teacher", "hod", "vice_principal", "principal")


def teaches(role_codenames) -> bool:
    """True when any of these roles is a teaching post."""
    return any(role in TEACHING_ROLES for role in role_codenames)


def employee_status(
    *,
    deactivated_at: object | None,
    left_on: date | None,
    on_leave: bool,
) -> str:
    """``Inactive`` / ``On Leave`` / ``Active`` for one employee.

    Off the roll wins over leave: somebody who has left cannot also be away
    today, and showing them as ``On Leave`` would keep them in the staffing
    count for ever.
    """
    if deactivated_at is not None or left_on is not None:
        return INACTIVE
    return ON_LEAVE if on_leave else ACTIVE


def utilisation(periods: int, capacity: int) -> int:
    """``periods`` as a percentage of the week's teaching slots, capped at 100.

    Both numbers come from the timetable (`periods` from the teacher's rows,
    `capacity` from the school's own slot count), so this never compares a real
    load with an invented maximum. No timetable yet means no percentage to show.
    """
    if capacity <= 0 or periods <= 0:
        return 0
    return min(100, round(periods / capacity * 100))
