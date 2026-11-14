"""The words a leave request may hold - one place, because three readers agree.

`leaverequest` is shared by two screens (student leave and staff leave) and now by
a workflow (apply -> approve / reject / cancel) and a balance register. The
vocabulary therefore cannot live in the screen, and it cannot be a database enum:
a school that decides "we also grant Bereavement leave" would need a migration to
say so.

Four rules, each learned from a number that is wrong in the browser when it is
wrong here:

* **`status` is the exact word the screen prints**, Title Case, because
  `_leave_window` (and every `On Leave` badge in this product) compares it as a
  string. `Cancelled` is a state of its own: deleting the row instead would make
  the day disappear from the register with nothing left to explain it.
* **`days` is inclusive of both ends** - a Friday-to-Monday leave is four days in
  a school office, not three. There is no holiday calendar in this schema yet, so
  a Sunday is counted; the screens say "calendar days" rather than pretending
  otherwise.
* **A leave belongs to the year it starts in.** A request spanning New Year is
  counted once, in the year of its `from_date`. Splitting a range across two
  balances needs a rule about which year's entitlement pays for which day, and no
  school has stated one.
* **`None` is not `0`.** A leave type with no policy and no override has *no
  limit* - it reports `entitled = None`, which prints as "Not tracked", not as
  "0 days left". `0` means something quite different and must stay available.
"""

from datetime import date

PENDING = "Pending"
APPROVED = "Approved"
REJECTED = "Rejected"
CANCELLED = "Cancelled"

#: Every word a request may hold, in the order approval moves through them.
LEAVE_STATUSES = (PENDING, APPROVED, REJECTED, CANCELLED)

#: The states a leave never leaves. A second decision on one of these is either a
#: no-op (same decision again) or a `409` - it is never a silent rewrite.
CLOSED_STATUSES = (REJECTED, CANCELLED)

#: The statuses that make a day `On Leave` in the staff register, i.e. the ones a
#: balance counts as *spent*. `Pending` days are counted separately: they are not
#: spent yet, but they must not be double-promised either (`balance_left`).
COUNTED_STATUSES = (APPROVED,)

#: What a brand-new school gets before anybody visits the policy screen. Three
#: ordinary Indian-school types with ordinary numbers - a starting point the office
#: edits, not a claim about employment law. A school that wants different ones
#: writes them; a school that never opens the screen still has a working form.
DEFAULT_POLICIES: dict[str, int] = {
    "Casual": 12,
    "Sick": 8,
    "Earned": 15,
}

#: The order the policy screen lists types in, so a new school and an old one do
#: not disagree about the first column.
DEFAULT_TYPES = tuple(DEFAULT_POLICIES)

#: The words the **student** leave screen has always offered - a different list from
#: the staff policy on purpose: a child's "OD" (on duty, at a competition) is not an
#: entitlement, and it grants no days, so it has no place in `leavepolicy`.
STUDENT_LEAVE_TYPES = ("Medical", "Personal", "OD", "Event", "Travel")


def days_between(from_date: date, to_date: date) -> int:
    """Calendar days from `from_date` to `to_date`, **both ends included**.

    A same-day leave is one day. A range that ends before it starts is zero, which
    the request schema refuses before it gets here - this function reports, it does
    not judge.
    """
    return (to_date - from_date).days + 1 if to_date >= from_date else 0


def leave_year(on_date: date) -> int:
    """The balance year a request starting on `on_date` belongs to."""
    return on_date.year


def year_bounds(year: int) -> tuple[date, date]:
    """The first and last day of a balance year."""
    return date(year, 1, 1), date(year, 12, 31)


def balance_left(*, entitled: int | None, used: int, pending: int) -> int | None:
    """Days left to ask for: `entitled - used - pending`, or `None` if untracked.

    `pending` is subtracted here rather than added to `used` because the two answer
    different questions: `used` is what payroll and the register stand behind,
    `pending` is what is still on somebody's desk. A teacher looking at "3 days
    left" after filing two must not be able to file five more.

    A negative answer is returned as it is - "-2" is the honest report of an
    override that was lowered after the leaves were approved, and clamping it to 0
    would hide the correction somebody has to make.
    """
    if entitled is None:
        return None
    return entitled - used - pending


def over_limit(*, entitled: int | None, used: int, pending: int, days: int) -> bool:
    """True when `days` more would exceed an entitlement that is actually tracked.

    An untracked type (`entitled is None`) never refuses: a school that has not
    written a policy has not said a limit exists.
    """
    left = balance_left(entitled=entitled, used=used, pending=pending)
    return left is not None and days > left


def type_key(name: str) -> str:
    """The comparison form of a leave type (`Casual`, ` casual ` -> `casual`).

    Used to resolve what a caller typed against the school's own policy rows. The
    **stored** spelling is always the policy's, so "casual" and "Casual" can never
    become two balances for one teacher.
    """
    return (name or "").strip().lower()
