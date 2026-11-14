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

from datetime import date, time

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


def serves_read_only(*, deactivated_at: object | None, left_on: date | None) -> bool:
    """True when this person's record is history and may not be edited.

    A leaver's profile stays readable - the office still needs to answer "when did
    they join, what did they teach" - but writing to it would change a record the
    school has already closed. Reactivating them is the way back in, which is a
    decision on the staff screen, not a qualification edit.
    """
    return deactivated_at is not None or left_on is not None


def differs(before: str | None, after: str | None) -> bool:
    """True when two spellings of the same fact are actually different.

    Compared case- and space-insensitively, because canonical text lower-cases
    what is stored while a form may send "Senior Teacher": that must not read as
    a promotion and append a history row.
    """
    return (before or "").strip().lower() != (after or "").strip().lower()


def utilisation(periods: int, capacity: int) -> int:
    """``periods`` as a percentage of the week's teaching slots, capped at 100.

    Both numbers come from the timetable (`periods` from the teacher's rows,
    `capacity` from the school's own slot count), so this never compares a real
    load with an invented maximum. No timetable yet means no percentage to show.
    """
    if capacity <= 0 or periods <= 0:
        return 0
    return min(100, round(periods / capacity * 100))


# --- documents -------------------------------------------------------------

#: The document types a staff file is filed under. A closed list, because
#: "aadhaar" and "degree" are different asks - one proves identity, the other a
#: qualification - and a free-text type would let the same paper arrive under
#: three spellings.
DOC_TYPES = (
    "aadhaar",
    "pan",
    "bank_proof",
    "degree",
    "certificate",
    "experience_letter",
    "medical",
    "contract",
    "photo",
    "other",
)

#: The screen's words for those types (the API sends the key, the drawer prints
#: this). Kept here so a new type cannot arrive without something to call it.
DOC_TYPE_LABELS = {
    "aadhaar": "Aadhaar Card",
    "pan": "PAN Card",
    "bank_proof": "Bank Proof",
    "degree": "Degree",
    "certificate": "Certificate",
    "experience_letter": "Experience Letter",
    "medical": "Medical Record",
    "contract": "Contract",
    "photo": "Photograph",
    "other": "Other",
}

#: The extensions a staff document may carry - the hiring-resume list, unchanged.
#: An allow-list, not a deny-list: the server has to be able to say what it will
#: ever open, and a `.exe` in a dossier folder is a mistake at best.
DOC_EXTENSIONS = (".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png")

#: The two words a substitution assignment may hold. `Assigned` is the office
#: arranging cover, `Approved` is the principal standing behind it. There is no
#: `Cancelled` word on purpose: a withdrawal has to **free** the slot, and the slot
#: is held by `UNIQUE(school_id, period_id, on_date)` - so a withdrawn cover is
#: deleted and the trail keeps the record. "Cancelled" would either block a new
#: cover for that period or force the unique key to be partial.
ASSIGNED = "Assigned"
APPROVED = "Approved"

#: The order the status chips are listed in, and the only two words stored.
SUBSTITUTION_STATUSES = (ASSIGNED, APPROVED)

# --- appraisal (Phase 8) ---------------------------------------------------
#
# A cycle is a **window**, an appraisal is **one person inside one window**, and a
# goal is a measurable line inside that appraisal. Four words per appraisal, in the
# order a school uses them: the person drafts it with their own rating, submits it,
# their reviewer records a rating and a note, and the office finalises it - after
# which nothing may change, because the number has been told to somebody.

CYCLE_DRAFT = "Draft"
CYCLE_OPEN = "Open"
CYCLE_CLOSED = "Closed"

#: What a cycle may be. `Draft` is a window being planned (nobody can fill it in),
#: `Open` is the appraisal season, `Closed` is a finished year.
APPRAISAL_CYCLE_STATUSES = (CYCLE_DRAFT, CYCLE_OPEN, CYCLE_CLOSED)

APPRAISAL_DRAFT = "Draft"
APPRAISAL_SUBMITTED = "Submitted"
APPRAISAL_REVIEWED = "Reviewed"
APPRAISAL_FINALIZED = "Finalized"

#: The appraisal's own states, in order.
APPRAISAL_STATUSES = (
    APPRAISAL_DRAFT,
    APPRAISAL_SUBMITTED,
    APPRAISAL_REVIEWED,
    APPRAISAL_FINALIZED,
)

#: The states a finalized appraisal never leaves: the number has been communicated.
APPRAISAL_LOCKED = (APPRAISAL_FINALIZED,)


#: The sections `staffauditlog` records, i.e. every part of a profile that can be
#: written. `kyc` is a read, not a write - unmasking an Aadhaar is the event.
AUDIT_SECTIONS = (
    "employment",
    "subjects",
    "qualification",
    "experience",
    "certification",
    "document",
    "duty",
    "attendance",
    #: A leave filed, approved, rejected or cancelled for this person. The row itself
    #: lives in `services/leave`; the trail is here because the profile's activity
    #: feed is where somebody asks "what happened to this teacher's file".
    "leave",
    #: Somebody stood in for this person's period (Phase 7). A cover is a fact about
    #: the person who was away, so the trail lands on their profile.
    "substitution",
    "kyc",
)

#: What happened to a row.
AUDIT_ACTIONS = (
    "created",
    "updated",
    "deleted",
    "uploaded",
    "verified",
    "downloaded",
    "revealed",
)


# --- masking ---------------------------------------------------------------
#
# Aadhaar, PAN and the bank account are the three fields that must not sit in a
# screenshot, a browser history or a shoulder-surfed screen. They are masked in
# **every** profile read and shown in full only to the roles that run payroll,
# on an explicit request, and that request is itself audited. The masks keep the
# last four characters because that is what a human uses to tell two records
# apart ("the one ending 9012"); everything else becomes X.


def _compact(value: str | None) -> str:
    """The value without the spaces people type into it."""
    return "".join((value or "").split())


def mask_aadhaar(value: str | None) -> str | None:
    """``1234 5678 9012`` -> ``XXXX XXXX 9012``; ``None`` when there is nothing."""
    text = _compact(value)
    if not text:
        return None
    if len(text) <= 4:
        return "X" * len(text)
    return f"XXXX XXXX {text[-4:]}"


def mask_pan(value: str | None) -> str | None:
    """``ABCDE1234F`` -> ``XXXXX1234F`` (the last five are the telling part)."""
    text = _compact(value).upper()
    if not text:
        return None
    if len(text) <= 5:
        return "X" * len(text)
    return "X" * (len(text) - 5) + text[-5:]


def mask_account(value: str | None) -> str | None:
    """``50100123456789`` -> ``XXXX 6789``."""
    text = _compact(value)
    if not text:
        return None
    if len(text) <= 4:
        return "X" * len(text)
    return f"XXXX {text[-4:]}"


# --- workload --------------------------------------------------------------
#
# The week a teacher actually works, and the week the school says a full load is.
# These words are shared by the matrix (a table), the tiles above it and the
# badges in between, so the number and the word next to it cannot disagree.

OVERLOADED = "Overloaded"
STEADY = "Steady"
LIGHT = "Light"
UNASSIGNED = "Unassigned"

#: The bands, in the order the analytics tiles list them.
BANDS = (OVERLOADED, STEADY, LIGHT, UNASSIGNED)


def workload_band(
    periods: int,
    capacity: int,
    *,
    overload_percent: int = 100,
    underload_percent: int = 60,
) -> str:
    """``Overloaded`` / ``Steady`` / ``Light`` for one person's load.

    Two thresholds, three words - the school's rule states exactly two, and a
    fourth band would need a third threshold nobody agreed to. Compared as
    integers (`periods * 100` against `capacity * percent`) so 18/24 cannot read
    as 74% on one machine and 75% on the next.

    ``Unassigned`` when the capacity is zero: a percentage against nothing is
    either a division by zero or a lie, and "we have not said what a full week is
    yet" is the honest answer.
    """
    if capacity <= 0:
        return UNASSIGNED
    load = periods * 100
    if load > capacity * overload_percent:
        return OVERLOADED
    if load < capacity * underload_percent:
        return LIGHT
    return STEADY


def period_label(start: time, end: time) -> str:
    """``09:00-09:45`` - one spelling of a slot, used by the API and the grid."""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def hours_between(start: time | None, end: time | None) -> float:
    """The length of a slot in hours, ``0.0`` when either end is missing.

    A duty with no times is a responsibility, not a slot ("library in-charge"),
    and counting it as some default number of hours would invent the very figure
    the analytics tab reports.
    """
    if start is None or end is None:
        return 0.0
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    return round(max(minutes, 0) / 60, 2)


#: The days a timetable week runs, in the order a grid draws them. Chronology,
#: not alphabet ("Friday" first would be a calendar nobody reads), which is the
#: same exception the audit feed takes for its newest-first order.
WEEK_DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

#: The screen's word for each day (`Monday`), so the API can send the key.
DAY_LABELS = {day: day.capitalize() for day in WEEK_DAYS}


def day_label(day: str | None) -> str | None:
    """``monday`` -> ``Monday``; ``None`` stays ``None`` (a dated duty has no day)."""
    if day is None:
        return None
    return DAY_LABELS.get(day, day)


#: What a duty is. A closed list for the same reason `DOC_TYPES` is: "gate_duty"
#: and "gate" are the same job, and a free-text type would file them apart.
DUTY_TYPES = (
    "exam_duty",
    "gate_duty",
    "assembly",
    "library",
    "bus_escort",
    "club",
    "sports",
    "other",
)

#: The screen's words for those duties (Title Case, like every other label).
DUTY_TYPE_LABELS = {
    "exam_duty": "Exam Duty",
    "gate_duty": "Gate Duty",
    "assembly": "Assembly",
    "library": "Library",
    "bus_escort": "Bus Escort",
    "club": "Club",
    "sports": "Sports",
    "other": "Other",
}


# --- attendance -------------------------------------------------------------
#
# The daily staff register. Three markable states, one derived one, and one that
# is not a state at all:
#
# * ``present`` / ``absent`` / ``half_day`` - what the office records;
# * ``on_leave`` - **derived** from an approved `leaverequest` covering that day.
#   It is never stored: a copied row would need rewriting every time a leave is
#   approved, rejected or shortened, and the two copies would eventually disagree.
#   For the same reason the write schemas refuse it - it is not a choice.
# * ``not_marked`` - the *absence of a row*. Nobody has said anything about that
#   day yet, which is not the same as absent, and printing "0% absent" for a month
#   nobody marked would be a lie the school then acts on.
#
# No ``late`` and no ``excused``: a status that changes a salary or a leave balance
# needs a rule the school has agreed to, and no rule has been written yet.

PRESENT = "present"
ABSENT = "absent"
HALF_DAY = "half_day"

#: What a caller may mark. `on_leave` is deliberately not here (see above).
ATTENDANCE_STATUSES = (PRESENT, ABSENT, HALF_DAY)

#: The screen's words for those, Title Case like every other label.
ATTENDANCE_STATUS_LABELS = {
    PRESENT: "Present",
    ABSENT: "Absent",
    HALF_DAY: "Half Day",
}

#: Derived, not markable, and not a `staffattendancerecord.status`.
#:
#: Named with the `ATTENDANCE_` prefix because this module already had an
#: ``ON_LEAVE`` - the directory's badge word ``On Leave``, which is a different
#: vocabulary (the relationship to the school, not a day's register). Reusing the
#: name here silently rewrote that badge to ``on_leave`` and broke every directory
#: read; the prefix is what keeps the two apart.
ATTENDANCE_ON_LEAVE = "on_leave"

#: Derived from a missing row - the honest answer for a day nobody marked.
NOT_MARKED = "not_marked"

ATTENDANCE_STATUS_LABELS[ATTENDANCE_ON_LEAVE] = "On Leave"
ATTENDANCE_STATUS_LABELS[NOT_MARKED] = "Not Marked"

#: Every word the register can show in its status column, in the order the
#: summary line and the filter list them.
ATTENDANCE_VIEW_STATUSES = (*ATTENDANCE_STATUSES, ATTENDANCE_ON_LEAVE, NOT_MARKED)


def attendance_status_label(status: str | None) -> str:
    """``half_day`` -> ``Half Day``; an unknown word comes back as it was typed.

    An unknown status is not possible through the API (the schemas check the
    vocabulary), but a row written by a script or an old import must still print
    something rather than blank the column.
    """
    if status is None:
        return ATTENDANCE_STATUS_LABELS[NOT_MARKED]
    return ATTENDANCE_STATUS_LABELS.get(status, status)


def is_markable(status: str | None) -> bool:
    """True when `status` is something the register may store."""
    return status in ATTENDANCE_STATUSES


def attendance_percent(*, present: int, half_day: int, marked: int) -> int:
    """Days attended as a percentage of the days **somebody marked**.

    A half day is half a day: ``earned = present * 2 + half_day`` out of
    ``marked * 2``, multiplied by 100 and floored - integers all the way, so
    18 present + 1 half day out of 20 marked is 92% on every machine, and never
    92.5 rounded one way here and another way in the browser.

    The denominator is **marked days**, not the days in the month: a month the
    office has not finished marking would otherwise report a teacher as 40%
    present and look like an attendance problem. `not_marked` travels beside the
    percentage so the screen can say which it is.

    Approved leave is **not** counted as absence, and not as attendance either -
    it is in neither side of the fraction.
    """
    if marked <= 0:
        return 0
    earned = present * 2 + half_day
    return min(100, earned * 100 // (marked * 2))


#: The month names the month sheet prints for `2026-11`. Here rather than in the
#: screen so the API and the browser cannot spell November two ways.
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def month_label(month: str) -> str:
    """``2026-11`` -> ``November 2026``.

    A key the database cannot read comes back as it was sent: the caller has
    already been refused with a `422`, and a label is the last place to raise.
    """
    year, _, number = month.partition("-")
    if not year.isdigit() or not number.isdigit():
        return month
    index = int(number)
    if index < 1 or index > 12:
        return month
    return f"{MONTH_NAMES[index - 1]} {year}"


def weekday_label(on_date: date) -> str:
    """``Monday`` for a calendar date - `WeekDayRead`'s label, for a dated row."""
    return DAY_LABELS[WEEK_DAYS[on_date.weekday()]]
