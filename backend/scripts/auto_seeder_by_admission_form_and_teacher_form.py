"""Auto-seed the schools with a full roll - **through the app's own forms**.

This is the seeder that runs when the stack comes up (`docker-entrypoint.sh`, after
the schools exist). It fills a fresh database with a school that looks lived-in:
every class-section has students, every family can sign in, every class-section has
a class teacher.

It is deliberately **not** a bulk INSERT script. Every record is created by the same
code path the screens use:

* a student (and their family) is a submitted **admission form** -
  (`admissions.service.create_application`), which is what the
  Operations > Admission > Application tab's *Submit* button calls. Everything the
  current flow creates comes with it: the `student_admission_form` row, the student's
  login (`user` + `student` role), the guardian's login (`user` + `guardian` role),
  the `studentprofile` the directory lists, the parent-child link, and the
  class-section (`classroom`) the student sits in.
* a student who left is the same form plus the **Separate** action -
  `admissions.service.record_separation()`.
* a teacher (and every other employee) is a submitted **teacher form** -
  `staff.service.create_profile()`, the Staff Hiring screen's *Register & create
  login*. That creates the login, the `employee` row and code, the roles, the
  subjects they can teach and the salary row.
* the class teacher of each class-section is the Classroom screen's assignment -
  `classroom.service.assign_class_teacher()`.
* the register is the Attendance screen's save - `attendance.service.bulk_create_attendance()`.

The two things the app has no form for are written directly, and only because there
is no flow to call: the few **leave requests** the Leave Sync tab reads, and nothing
else.

What the data covers (the point of seeding at all)
--------------------------------------------------
Every branch the product has a case for is present: both logins, a family whose only
address is the parent's, a child with a single name, siblings sharing one parent
login, unknown gender, blank demographics, every dropdown value the form offers,
students who left mid-session, teachers with and without subjects, and a register
with every attendance status.

Rules it follows (the same ones the screens enforce)
----------------------------------------------------
* The **guardian block carries both contacts**: the email is the guardian's login and
  the **10-digit phone** is what the school rings. A student email is optional - some
  children have their own address, some sign in through the parent.
* The father / mother blocks carry **names, occupations and income** only: an address
  typed there is family detail, never a login (`admissions/service.py`).
* A teacher always has **both** an email and a phone (plus the bank name the hire
  form insists on).
* Everything is stored the way a router would store it: lower-case text, phones as
  ten digits (`app/core/text.py`).

Running it
----------
No arguments is the compose behaviour - both schools, sections A-D, 15-25 students
each, teachers, ten days of register:

    python scripts/auto_seeder_by_admission_form_and_teacher_form.py

    --school abc            one school only
    --sections a,b          which sections to fill
    --min 15 --max 25       students per class-section
    --attendance-days 0     skip the register
    --without-teachers      skip the staff
    --reset                 delete what this seeder wrote, then write it again
    --password demo@1234    the password every seeded account gets

**It always runs and only inserts what is missing.** Each planned record has a key
(the student's `admission_number`, the employee's email), so a complete database is left
alone, a half-filled one is completed, and re-running never duplicates. Every
account signs in with one password (hashed once - thousands of bcrypt hashes would
take minutes), and every address it hands out is `@<code>.demo` /
`@<code>.parents.demo` / `@<code>.staff.demo`, so the data it wrote is recognisable
and `--reset` can find it.
"""

import argparse
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine  # noqa: E402
from app.core.security import get_password_hash, pwd_context  # noqa: E402
from app.core.tenancy import SKIP_SCHOOL, bound_to  # noqa: E402
from app.domains.academics.models import (  # noqa: E402
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.academics.repository import delete_room_if_unused  # noqa: F401,E402
from app.domains.admissions import service as admissions  # noqa: E402
from app.domains.admissions.models import AdmissionApplication  # noqa: E402
from app.domains.admissions.schemas import (  # noqa: E402
    AdmissionApplicationCreate,
    SeparationRecordWrite,
)
from app.domains.attendance import service as attendance  # noqa: E402
from app.domains.attendance.models import AttendanceRecord  # noqa: E402
from app.domains.attendance.schemas import AttendanceBulkCreate  # noqa: E402
from app.domains.auth.models import UserRole  # noqa: E402
from app.domains.classroom import service as classroom  # noqa: E402
from app.domains.operations.models import LeaveRequest  # noqa: E402
from app.domains.salary.models import EmployeeSalary  # noqa: E402
from app.domains.schools.models import School  # noqa: E402
from app.domains.staff import service as staff  # noqa: E402
from app.domains.staff.models import Employee  # noqa: E402
from app.domains.staff.schemas import StaffProfileCreate  # noqa: E402
from app.domains.students.models import (  # noqa: E402
    StudentParentRelationship,
    StudentProfile,
)
from app.domains.teachers.models import TeacherSubject  # noqa: E402
from app.domains.users.models import User  # noqa: E402

# The engine echoes every statement for the app's own debugging; a seeder writing
# tens of thousands of rows does not want that in its output.
engine.echo = False

# ---------------------------------------------------------------------------
# The shape of the roll
# ---------------------------------------------------------------------------

#: Sections the school runs for this data. The catalog holds A-J; a school that
#: runs four is the common case and keeps the demo readable.
SECTIONS: tuple[str, ...] = ("a", "b", "c", "d")

#: Students per class-section - drawn per section, because a real class varies.
MIN_PER_SECTION = 15
MAX_PER_SECTION = 25

#: Weekdays of register written per class-section (`--attendance-days`).
ATTENDANCE_DAYS = 10

#: One password for every seeded account. It is hashed **once** and shared: the
#: point of this data is that anybody can sign in, and thousands of bcrypt hashes
#: would take minutes. Demo data with a published password, hence the low cost
#: factor the run sets below.
DEMO_PASSWORD = "demo@1234"

#: Every address this seeder hands out ends in one of these, so what it wrote is
#: recognisable and `--reset` can find it.
STUDENT_DOMAIN = "demo"
GUARDIAN_DOMAIN = "parents.demo"
STAFF_DOMAIN = "staff.demo"

#: The option lists the forms offer (lower-cased, as a router would store them).
RELIGIONS = (
    "hindu", "muslim", "christian", "sikh", "buddhist", "jain", "parsi",
    "jewish", "other",
)
TONGUES = (
    "hindi", "english", "bengali", "marathi", "telugu", "tamil", "gujarati",
    "urdu", "kannada", "odia", "malayalam", "punjabi", "assamese", "maithili",
    "sanskrit", "other",
)
BLOOD_GROUPS = ("a+", "a-", "b+", "b-", "ab+", "ab-", "o+", "o-")
CATEGORIES = ("general", "obc", "sc", "st", "ews", "other")
BOARDS = ("cbse", "icse", "state board", "ib", "igcse", "other")
OCCUPATIONS = (
    "business", "government service", "private service", "self employed",
    "professional", "farmer", "homemaker", "retired", "others",
)
INCOMES = ("0 â€“ 5l", "5l â€“ 10l", "10l â€“ 15l", "15l â€“ 20l", "20l +")
RELATIONS = ("father", "mother", "uncle", "aunt", "grandparent", "legal guardian")
STREETS = (
    "mathri layout", "khariar road", "basant nagar", "sector 12", "green park",
    "nehru colony", "gandhi marg", "shanti vihar", "laxmi nagar", "rajaji street",
)
ROUTES = (
    "route 1 â€“ north", "route 2 â€“ east", "route 3 â€“ west", "route 4 â€“ south",
)
QUALIFICATIONS = ("b.ed", "m.a. b.ed", "m.sc, b.ed", "b.sc, b.ed", "m.com", "b.a.")
BANKS = (
    "state bank of india", "hdfc bank", "icici bank", "punjab national bank",
    "axis bank", "bank of baroda",
)
DEPARTMENTS = ("science", "mathematics", "languages", "social science", "sports", "arts")

BOYS = (
    "aarav", "aditya", "advait", "arjun", "aryan", "atharv", "ayaan", "devansh",
    "dhruv", "harsh", "ishaan", "kabir", "karthik", "krishna", "manav", "nikhil",
    "om", "pranav", "reyansh", "rohan", "rudra", "sahil", "samar", "shivansh",
    "tanmay", "vihaan", "vivaan", "yash",
)
GIRLS = (
    "aadhya", "aarohi", "aditi", "advika", "ahana", "ananya", "anika", "avni",
    "diya", "esha", "gauri", "ira", "ishita", "juhi", "kavya", "kiara", "mahika",
    "meera", "myra", "navya", "pari", "prisha", "riya", "saanvi", "sara",
    "shreya", "siya", "trisha", "vanya", "zara",
)
SURNAMES = (
    "agarwal", "bansal", "chauhan", "das", "d'souza", "deshmukh", "gupta",
    "iyer", "jain", "joshi", "kapoor", "khan", "kulkarni", "malhotra", "mehta",
    "menon", "mishra", "nair", "patel", "pillai", "rao", "reddy", "saxena",
    "sharma", "singh", "sinha", "tiwari", "verma", "yadav",
)
MIDDLE = ("kumar", "raj", "dev", "prasad", "chandra", "lal")

#: A form's `notes` is prose - stored as typed, so it is written the way the office
#: would type it.
NOTES = (
    "Allergic to peanuts - please inform the class teacher.",
    "Needs a front seat (short sighted).",
    "Speaks only Hindi at home; settling in well.",
    "Asthma inhaler kept with the school nurse.",
)

#: Leave requests (the Leave Sync tab). `reason` is prose too.
LEAVE_REASONS = (
    "Fever, advised rest by the doctor.",
    "Family function out of town.",
    "Dental appointment.",
    "Attending a cousin's wedding.",
    "Recovering from a cold.",
    "Travelling for a family emergency.",
)
LEAVE_TYPES = ("Medical", "Personal", "Casual", "Sick", "Earned", "OD")

#: The separation block, spelled the way the screen offers it (`session` is stored
#: as typed - the Registered tab's filters compare that string).
SEPARATION_REASONS = (
    "Rusticated", "Transfer Certificate Issued", "Long Absence", "Fee Default",
    "Disciplinary Action", "Parent Request", "Relocation", "Others",
)
SEPARATION_SESSIONS = ("Completed Session", "Incomplete Session")

#: Contact shapes, with the weight each is drawn at. **Every one carries a guardian
#: email and a 10-digit guardian phone** - the rule this data follows
#: (`REQUIRED_TO_ADMIT` in `admissions/service.py`) - so every family can sign in:
#: a login is an email, and the number is how the school rings them. The shapes differ
#: in whether the **child** also has an address of their own, and in whether two
#: children share one parent (the sibling branch).
CONTACT_SHAPES: tuple[tuple[str, int], ...] = (
    ("both_emails", 55),          # student + guardian logins
    ("guardian_email_only", 35),  # the parent's address is the family's way in
    ("siblings", 10),             # one parent login, two children
)

#: Which block **names** the guardian, with the weight each is drawn at. The form
#: names both parents, so the guardian block may be left empty and the guardian is
#: named after the father or the mother instead. The contact never moves with it: the
#: login and the number stay in the guardian block on every branch - a father / mother
#: email or phone is family detail, not a way into the app.
GUARDIAN_BLOCKS: tuple[tuple[str, int], ...] = (
    ("guardian", 60),
    ("father", 24),
    ("mother", 16),
)

#: The staff every school has, besides teachers: (role codename, how many).
STAFF_PLAN: tuple[tuple[str, int], ...] = (
    ("principal", 1),
    ("vice_principal", 1),
    ("hod", 2),
    ("accountant", 1),
    ("librarian", 1),
    ("transport", 1),
    ("staff", 2),
)

#: Subjects a teacher is listed against (from the school's own subject catalog).
SUBJECTS_PER_TEACHER = 3


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _cheap_passwords(rounds: int = 4) -> None:
    """Lower bcrypt's cost factor **for this process only**.

    Every seeded account gets the same published demo password, and the forms hash
    it once per login - at the default cost that is minutes of CPU for a full roll.
    The stored hash still verifies normally; only the work factor differs.
    """
    try:
        pwd_context.update(bcrypt__rounds=rounds)
    except Exception:  # pragma: no cover - passlib version without update()
        print("[seed] note: could not lower the password cost - this run will be slower")


def _weighted(rng: random.Random, options: tuple[tuple[str, int], ...]) -> str:
    """One key from a `(key, weight)` list - the weights are relative."""
    return rng.choices(
        [name for name, _ in options], weights=[weight for _, weight in options], k=1
    )[0]


def _unique(factory, taken: set[str]) -> str:
    """A value nobody has used yet (email and phone are unique indexes).

    The factory is deterministic for a given planned record, so a value that is
    already taken (a re-run, or a sibling's parent) would loop forever - hence the
    counter that goes in front of the `@`: the record still gets a free address, and
    it is recognisably the same person's.
    """
    value = factory()
    for _ in range(20):
        if value not in taken:
            taken.add(value)
            return value
        value = factory()
    local, at, domain = value.partition("@")
    for counter in range(1, 1000):
        candidate = f"{local}{counter}{at}{domain}"
        if candidate not in taken:
            taken.add(candidate)
            return candidate
    raise RuntimeError("no unused value left")  # pragma: no cover


def _reserved_logins(session: Session) -> set[str]:
    """The logins already in the database that this seeder must **not** collide with.

    Its own rows are left out on purpose: the plan generates the same address for the
    same slot on every run, and that is exactly how a re-run recognises the person it
    already wrote (the form number is the student's key, the email the employee's).
    Reserving those too made the generator step aside with a counter - a *new* address
    - so a second run hired everybody again.

    Foreign logins (the school's admin, a phone another feature created) are kept out
    of reach, and the read steps outside the tenant filter because the unique index is
    platform-wide.
    """
    own_domains = (f".{STUDENT_DOMAIN}", f".{GUARDIAN_DOMAIN}", f".{STAFF_DOMAIN}")
    return {
        email
        for email in session.exec(
            select(User.email), execution_options={SKIP_SCHOOL: True}
        ).all()
        if not email.endswith(own_domains)
    }


def _phone(rng: random.Random) -> str:
    """A ten-digit number the app accepts: 7/8/9 then nine digits."""
    return rng.choice("789") + "".join(str(rng.randint(0, 9)) for _ in range(9))


def _student_name(rng: random.Random) -> tuple[str, str, str | None]:
    """(full name, first name, last name) - some children have a single name."""
    first = rng.choice(BOYS + GIRLS)
    if rng.random() < 0.04:
        return first, first, None
    last = rng.choice(SURNAMES)
    middle = rng.choice(MIDDLE) if rng.random() < 0.25 else None
    return " ".join(part for part in (first, middle, last) if part), first, last


def _gender(rng: random.Random) -> str | None:
    """Male / Female, plus the edges a real roll has: "other" and "not recorded"."""
    roll = rng.random()
    if roll < 0.47:
        return "male"
    if roll < 0.94:
        return "female"
    if roll < 0.96:
        return "other"
    return None


def _maybe(rng: random.Random, value: str, chance: float = 0.85) -> str | None:
    """The value most of the time, `None` the rest - blanks are real data too."""
    return value if rng.random() < chance else None


def _date_of_birth(rng: random.Random, level: int, today: date) -> date:
    """A birthday that puts the child in the right year for the class."""
    return today - timedelta(days=(level + 4) * 365 + rng.randint(0, 300))


# ---------------------------------------------------------------------------
# The plan: what to write, decided before anything is read from the database
#
# The plan is a pure function of (seed, school code) - the same run always plans
# the same school. That is what makes "insert only what is missing" safe: student
# #37 is the same student on every start, so a half-filled database is completed
# rather than shuffled.
# ---------------------------------------------------------------------------


@dataclass
class StudentPlan:
    """One submitted admission form, ready to hand to the service."""

    section: str
    class_name: str
    payload: dict
    #: The separation to record after registering (a student who left), or None.
    separation: dict | None = None


@dataclass
class StaffPlan:
    """One submitted teacher/hire form, ready to hand to the service."""

    payload: dict
    #: The class-section this person runs as class teacher ("class 9-a"), or None.
    class_teacher_of: str | None = None


@dataclass
class SchoolPlanner:
    """Plans one school's roll. One instance per school, so serials and the
    "who already has this contact" set stay inside that school."""

    rng: random.Random
    code: str
    today: date
    taken: set[str] = field(default_factory=set)
    serial: int = 0
    previous_guardian: str | None = None
    previous_guardian_phone: str | None = None
    previous_surname: str | None = None

    # -- students ----------------------------------------------------------

    def students_for(
        self,
        class_name: str,
        level: int,
        section_name: str,
        class_id: UUID,
        section_id: UUID,
    ) -> list[StudentPlan]:
        """Plan one class-section's roll (15-25 children, drawn per section)."""
        return [
            self._student_plan(class_name, level, section_name, class_id, section_id)
            for _ in range(self.rng.randint(MIN_PER_SECTION, MAX_PER_SECTION))
        ]

    def _student_plan(
        self,
        class_name: str,
        level: int,
        section_name: str,
        class_id: UUID,
        section_id: UUID,
    ) -> StudentPlan:
        """One child's form: contacts first, because they decide the logins."""
        rng = self.rng
        self.serial += 1
        serial = self.serial
        shape = _weighted(rng, CONTACT_SHAPES)
        block = _weighted(rng, GUARDIAN_BLOCKS)

        full_name, first, last = _student_name(rng)
        # A sibling shares the family: same surname, same parent, same login.
        sibling = shape == "siblings" and self.previous_guardian is not None
        if sibling and self.previous_surname:
            last = self.previous_surname
            full_name = " ".join(part for part in (first, last) if part)

        student_email: str | None = None
        if shape == "both_emails":
            student_email = _unique(
                lambda: f"{first}.{last or 'k'}{serial}@{self.code}.{STUDENT_DOMAIN}",
                self.taken,
            )

        # The guardian block always carries **both** contacts: the email is the login
        # and the number is what the school rings, so every seeded family can sign in.
        guardian_email: str | None = None
        guardian_phone: str | None = None
        if sibling:
            guardian_email = self.previous_guardian
            guardian_phone = self.previous_guardian_phone
        else:
            guardian_phone = _unique(lambda: _phone(rng), self.taken)
            guardian_email = _unique(
                lambda: f"{last or first}{serial}@{self.code}.{GUARDIAN_DOMAIN}",
                self.taken,
            )
        self.previous_guardian = guardian_email
        self.previous_guardian_phone = guardian_phone
        self.previous_surname = last

        gender = _gender(rng)
        street = rng.choice(STREETS)
        name_parts = full_name.split(" ")
        payload = {
            # The number the roll will know the child by. The server mints one when
            # a form brings none; the seeder brings its own so the demo data reads
            # `<SCHOOL>-2026-0001` instead of `ADM-2026-0001`.
            "admission_number": f"{self.code.upper()}-2026-{serial:04d}",
            "created_on": self.today - timedelta(days=rng.randint(30, 900)),
            "notes": rng.choice(NOTES) if rng.random() < 0.08 else None,
            "student_first_name": first,
            "student_middle_name": name_parts[1] if len(name_parts) == 3 else None,
            "student_last_name": last,
            "student_email": student_email,
            "date_of_birth": _date_of_birth(rng, level, self.today),
            "gender": gender,
            "blood_group": _maybe(rng, rng.choice(BLOOD_GROUPS), 0.8),
            "religion": _maybe(rng, rng.choice(RELIGIONS), 0.85),
            "category": _maybe(rng, rng.choice(CATEGORIES), 0.8),
            "mother_tongue": _maybe(rng, rng.choice(TONGUES), 0.85),
            "nationality": _maybe(rng, "indian", 0.9),
            "aadhaar_id": _maybe(
                rng, "".join(str(rng.randint(0, 9)) for _ in range(12)), 0.6
            ),
            "address": _maybe(rng, f"{rng.randint(1, 240)}, {street}", 0.85),
            "permanent_address": (
                f"{rng.randint(1, 240)}, {rng.choice(STREETS)}"
                if rng.random() < 0.5
                else None
            ),
            "previous_school_name": _maybe(
                rng, f"{rng.choice(SURNAMES)} public school", 0.45
            ),
            "previous_class_passed": _maybe(rng, f"class {max(0, level - 1)}", 0.5),
            "previous_board": _maybe(rng, rng.choice(BOARDS), 0.5),
            "transfer_certificate_no": _maybe(
                rng, f"tc-{rng.randint(10000, 99999)}", 0.25
            ),
            "old_unique_id": _maybe(rng, f"uid-{rng.randint(1000, 9999)}", 0.15),
            # The father / mother blocks are family **detail** now - names, occupations,
            # income. Their email and phone fields are not written at all: the login and
            # the contact number live in the guardian block (`admissions/service.py`).
            "father_name": self._parent_name(last, rng),
            "father_occupation": _maybe(rng, rng.choice(OCCUPATIONS), 0.9),
            "father_annual_income": _maybe(rng, rng.choice(INCOMES), 0.8),
            "mother_name": self._parent_name(last, rng),
            "mother_occupation": _maybe(rng, rng.choice(OCCUPATIONS), 0.85),
            "mother_annual_income": _maybe(rng, rng.choice(INCOMES), 0.75),
            "guardian_name": self._parent_name(last, rng) if block == "guardian" else None,
            "guardian_relation": (
                _maybe(rng, rng.choice(RELATIONS), 0.9) if block == "guardian" else None
            ),
            "guardian_phone": guardian_phone,
            "guardian_email": guardian_email,
            "guardian_occupation": _maybe(rng, rng.choice(OCCUPATIONS), 0.85),
            "guardian_address": _maybe(rng, f"{rng.randint(1, 240)}, {street}", 0.7),
            "applied_for_class_level": class_name,
            "current_class_or_last_class": class_name,
            "applied_section_preference": section_name,
            "applied_class_id": class_id,
            "applied_section_id": section_id,
            "needs_transport": "Yes" if rng.random() < 0.3 else "No",
            "transport_route": rng.choice(ROUTES) if rng.random() < 0.3 else None,
            "needs_hostel": "Yes" if rng.random() < 0.1 else "No",
        }

        # A few students left the school. The form submit never sets this - it is
        # the Registered tab's separate "Separate" action - so the plan carries it
        # and the apply step records it right after registering.
        separation = None
        if rng.random() < 0.04:
            separation = {
                "reason": rng.choice(SEPARATION_REASONS),
                "session": rng.choice(SEPARATION_SESSIONS),
                "date": self.today - timedelta(days=rng.randint(5, 300)),
                "dropped_class": class_name,
            }

        return StudentPlan(
            section=section_name,
            class_name=class_name,
            payload=payload,
            separation=separation,
        )

    def _parent_name(self, surname: str | None, rng: random.Random) -> str:
        """A parent's name - usually the family surname, sometimes the other side's."""
        return f"{rng.choice(BOYS + GIRLS)} {surname or rng.choice(SURNAMES)}"

    # -- staff -------------------------------------------------------------

    def staff_for(
        self, subject_ids: list[UUID], sections: list[tuple[str, UUID]]
    ) -> list[StaffPlan]:
        """Plan the staff: the office roles, plus one teacher per class-section.

        A teacher per class-section is what the Classroom screen needs - the grid
        shows who runs each section - and it is how a real school is staffed. Every
        person here has an email **and** a phone, which is what the hire form
        insists on.
        """
        plans: list[StaffPlan] = []
        for role, how_many in STAFF_PLAN:
            for _ in range(how_many):
                plans.append(StaffPlan(payload=self._staff_payload(role)))
        for index, (label, _room_id) in enumerate(sections):
            plans.append(
                StaffPlan(
                    payload=self._staff_payload("teacher", subject_ids=subject_ids),
                    class_teacher_of=label,
                )
            )
            del index
        return plans

    def _staff_payload(
        self, role: str, subject_ids: list[UUID] | None = None
    ) -> dict:
        """One hire form, filled the way the office would fill it."""
        rng = self.rng
        self.serial += 1
        serial = self.serial
        full_name, first, last = _student_name(rng)
        email = _unique(
            lambda: f"{first}.{last or 'k'}{serial}@{self.code}.{STAFF_DOMAIN}",
            self.taken,
        )
        phone = _unique(lambda: _phone(rng), self.taken)
        joining = self.today - timedelta(days=rng.randint(60, 3000))
        salary = float(rng.choice((22000, 26000, 31000, 35000, 42000, 48000, 55000)))
        subjects = list(subject_ids or [])
        rng.shuffle(subjects)
        return {
            "full_name": full_name,
            "role_codenames": [role],
            "department": rng.choice(DEPARTMENTS),
            "qualification": rng.choice(QUALIFICATIONS),
            "experience_years": rng.randint(0, 18),
            "contact_email": email,
            "phone": phone,
            "joining_date": joining,
            "subject_ids": subjects[:SUBJECTS_PER_TEACHER],
            "address": f"{rng.randint(1, 240)}, {rng.choice(STREETS)}",
            "emergency_contact": _unique(lambda: _phone(rng), self.taken),
            "aadhaar_no": "".join(str(rng.randint(0, 9)) for _ in range(12)),
            "pan_no": f"{''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(5))}"
            f"{rng.randint(1000, 9999)}{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
            "bank_name": rng.choice(BANKS),
            "bank_account_no": "".join(str(rng.randint(0, 9)) for _ in range(11)),
            "ifsc": f"SBIN0{rng.randint(100000, 999999)}",
            "salary_monthly": salary,
            "previous_employer_monthly_salary": salary * rng.choice((0.8, 0.9, 1.0)),
        }


# ---------------------------------------------------------------------------
# Applying a plan - through the app's own services
# ---------------------------------------------------------------------------


def _share_password(session: Session, user_ids: list[UUID | None], demo_hash: str) -> None:
    """Give the logins a form just created the demo password.

    The form mints a random first-time password per login (that is the point - the
    office shows it once). Seeded accounts are meant to be signed into, so they all
    get the one published password instead.
    """
    touched = False
    for user_id in user_ids:
        if user_id is None:
            continue
        user = session.get(User, user_id)
        if user is None or user.hashed_password == demo_hash:
            continue
        user.hashed_password = demo_hash
        session.add(user)
        touched = True
    if touched:
        session.commit()


def _room_id(session: Session, class_name: str, section_name: str) -> UUID | None:
    """The class-section's `classroom` row - created by its first registered student."""
    classroom = session.exec(
        select(ClassName).where(ClassName.classname == class_name)
    ).first()
    section = session.exec(
        select(Section).where(Section.section_name == section_name)
    ).first()
    if classroom is None or section is None:
        return None
    room = session.exec(
        select(Classroom).where(
            Classroom.class_id == classroom.class_id,
            Classroom.section_id == section.section_id,
        )
    ).first()
    return room.id if room else None


def _apply_students(
    session: Session,
    plans: list[StudentPlan],
    demo_hash: str,
    stats: dict[str, int],
) -> None:
    """Submit each planned admission form, skipping the students already there.

    The key is the admission number (`ABC-2026-0007`): a student already in the
    database is left exactly as they are, so re-running never duplicates and a
    half-finished run is completed on the next start.
    """
    for plan in plans:
        admission_number = plan.payload["admission_number"]
        if session.exec(
            select(AdmissionApplication.id).where(
                AdmissionApplication.admission_number == admission_number
            )
        ).first():
            stats["students_present"] += 1
            continue

        read = admissions.create_application(
            session, AdmissionApplicationCreate(**plan.payload)
        )
        stats["students_added"] += 1
        _share_password(session, [read.student_user_id, read.guardian_user_id], demo_hash)
        if read.student_login_email:
            stats["student_logins"] += 1
        if read.guardian_login_email:
            stats["guardian_logins"] += 1
        if read.placement_note:
            stats["placement_notes"] += 1

        # Registered, then the Separate action - the two steps the office takes.
        if plan.separation:
            admissions.record_separation(
                session, read.id, SeparationRecordWrite(**plan.separation)
            )
            stats["separated"] += 1


def _apply_staff(
    session: Session,
    plans: list[StaffPlan],
    demo_hash: str,
    stats: dict[str, int],
) -> None:
    """Submit each planned hire form, skipping people who are already on the staff.

    The key is the email: the hire flow refuses a second login for an address that
    already exists, so an existing employee is left alone.
    """
    for plan in plans:
        email = plan.payload["contact_email"]
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user is not None:
            stats["staff_present"] += 1
            # Already hired - but their class-section may still need them (an earlier
            # run may have stopped between the hire and the assignment), so the
            # assignment is re-applied rather than skipped with the hire.
            employee = session.exec(
                select(Employee).where(Employee.user_id == existing_user.id)
            ).first()
            if plan.class_teacher_of and employee is not None:
                _assign_class_teacher(session, plan.class_teacher_of, employee.id, stats)
            continue

        created = staff.create_profile(session, StaffProfileCreate(**plan.payload))
        stats["staff_added"] += 1
        _share_password(session, [created.user_id], demo_hash)
        if plan.class_teacher_of:
            _assign_class_teacher(session, plan.class_teacher_of, created.id, stats)


def _assign_class_teacher(
    session: Session, label: str, employee_id: UUID, stats: dict[str, int]
) -> None:
    """Put one teacher in charge of one class-section ("nursery-a").

    The Classroom screen's own action (`classroom.assign_class_teacher`), so the
    grid shows who runs each section.
    """
    class_name, _, section_name = label.rpartition("-")
    room_id = _room_id(session, class_name, section_name)
    if room_id is None:
        stats["class_teacher_missing"] += 1
        return
    classroom.assign_class_teacher(
        session, section_id=room_id, teacher_id=employee_id
    )
    stats["class_teachers"] += 1


# ---------------------------------------------------------------------------
# The register and the leave requests
# ---------------------------------------------------------------------------


def _weekdays(today: date, days: int) -> list[date]:
    """The last `days` weekdays - a register has no Saturday in it."""
    found: list[date] = []
    day = today
    while len(found) < days:
        if day.weekday() < 5:
            found.append(day)
        day -= timedelta(days=1)
    return list(reversed(found))


def _apply_attendance(
    session: Session, days: int, seed: str, stats: dict[str, int]
) -> None:
    """Save the register through the Attendance screen's own service.

    One call per class-section per day - the same call the screen makes. Dates that
    already have rows are skipped, so a register that is already there is left
    alone and a class-section that has none (a fresh one) is filled.

    Almost everyone is present almost every day, and two students per section are
    deliberately often absent: the irregular list reads exactly that (its risk
    levels start at six absences).
    """
    for room in session.exec(select(Classroom)).all():
        students = session.exec(
            select(StudentProfile).where(StudentProfile.classroom_id == room.id)
        ).all()
        if not students:
            continue
        already = set(
            session.exec(
                select(AttendanceRecord.date).where(
                    AttendanceRecord.classroom_id == room.id
                )
            ).all()
        )
        missing = [day for day in _weekdays(date.today(), days) if day not in already]
        if not missing:
            stats["registers_present"] += 1
            continue
        for day in missing:
            # A seed of its own per section and day: the same register every run.
            rng = random.Random(f"{seed}:{room.id}:{day}")
            irregular = {
                profile.id
                for profile in rng.sample(students, k=min(2, len(students)))
            }
            records = []
            for profile in students:
                chance = 0.55 if profile.id in irregular else 0.06
                roll = rng.random()
                if roll < chance:
                    status = "absent"
                elif roll < chance + 0.03:
                    status = "late"
                elif roll < chance + 0.05:
                    status = "leave"
                elif roll < chance + 0.06:
                    status = "half_day"
                else:
                    status = "present"
                records.append(
                    {"student_id": str(profile.id), "status": status, "remarks": None}
                )
            attendance.bulk_create_attendance(
                session,
                AttendanceBulkCreate(section_id=room.id, date=day, records=records),
            )
            stats["attendance_rows"] += len(records)


def _apply_leaves(session: Session, seed: str, stats: dict[str, int]) -> None:
    """File a few leave requests - the Leave Sync tab reads these and nothing else.

    This is the one place the seeder writes a row directly: the app has no "file a
    leave" flow yet (the tab only reads). A request is keyed on the student it is
    for, so a student who already has one is left alone and re-running never adds a
    second.
    """
    links = {
        link.student_id: link.parent_user_id
        for link in session.exec(select(StudentParentRelationship)).all()
    }
    already = {
        request.student_id
        for request in session.exec(select(LeaveRequest)).all()
        if request.student_id is not None
    }
    candidates = [
        (profile.id, links.get(profile.id) or profile.user_id)
        for profile in session.exec(select(StudentProfile)).all()
        if (links.get(profile.id) or profile.user_id) and profile.id not in already
    ]
    if not candidates:
        stats["leaves_present"] += 1
        return
    rng = random.Random(f"{seed}:leaves")
    for student_id, requester_id in rng.sample(candidates, k=min(8, len(candidates))):
        start = date.today() - timedelta(days=rng.randint(1, 20))
        length = rng.randint(1, 4)
        session.add(
            LeaveRequest(
                student_id=student_id,
                requester_user_id=requester_id,
                leave_type=rng.choice(LEAVE_TYPES),
                from_date=start,
                to_date=start + timedelta(days=length - 1),
                days=length,
                reason=rng.choice(LEAVE_REASONS),
                # Approved ones are what the register syncs; a couple stay pending so
                # the tab shows both states.
                status=rng.choice(("Pending", "Approved", "Approved", "Rejected")),
            )
        )
        stats["leave_requests"] += 1
    session.commit()


# ---------------------------------------------------------------------------
# Undoing it
# ---------------------------------------------------------------------------


def _reset(session: Session, school: School) -> None:
    """Delete everything this seeder wrote for one school.

    Found by what it wrote, not by a marker column: the students by their
    admission-number prefix (`ABC-...`, which also covers the earlier direct-write
    format), their rows through the ids that point at them, the logins through the
    parent-child links plus the `@<code>.demo` addresses, and the staff through the
    `@<code>.staff.demo` addresses. The **schools, their admins and the catalogs are
    never touched** - they come from their own seed.

    A class-section is **left in place**: it is the school's structure, not the data
    this seeder wrote, and the next fill reuses it. (The app deletes an empty
    class-section when its last student is deleted through the Students screen; a
    re-seed wants the section to stay, so it is not removed here.)
    """
    bound_to(session, school.id)
    code = school.code.lower()
    prefix = f"{code}-"
    # The logins this seeder owns: its own domains, plus any student of this school
    # whose form number carries the school prefix.
    demo_user_ids = {
        user.id
        for user in session.exec(select(User)).all()
        if user.email.endswith(f"@{code}.{STUDENT_DOMAIN}")
        or user.email.endswith(f"@{code}.{GUARDIAN_DOMAIN}")
        or user.email.endswith(f"@{code}.{STAFF_DOMAIN}")
    }
    students = [
        profile
        for profile in session.exec(select(StudentProfile)).all()
        if (profile.admission_number or "").lower().startswith(prefix)
        # A student made by an older script or by hand keeps a form number without
        # the prefix, but holds a login this reset is about to delete - so it goes
        # with it instead of blocking the delete.
        or (profile.user_id is not None and profile.user_id in demo_user_ids)
    ]
    student_ids = {profile.id for profile in students}
    user_ids = {profile.user_id for profile in students if profile.user_id}

    for record in session.exec(select(AttendanceRecord)).all():
        if record.student_id in student_ids:
            session.delete(record)
    for request in session.exec(select(LeaveRequest)).all():
        if request.student_id in student_ids:
            session.delete(request)
    for application in session.exec(select(AdmissionApplication)).all():
        if application.student_id in student_ids:
            session.delete(application)
    for link in session.exec(select(StudentParentRelationship)).all():
        if link.student_id in student_ids:
            user_ids.add(link.parent_user_id)
            session.delete(link)
    session.commit()

    for profile in students:
        session.delete(profile)
    session.commit()

    # The staff this seeder hired, plus any login it created that is still around.
    staff_user_ids = demo_user_ids
    user_ids |= staff_user_ids

    # `classroom.class_teacher_id` points at an employee, so it is cleared first.
    for room in session.exec(select(Classroom)).all():
        employee = (
            session.get(Employee, room.class_teacher_id)
            if room.class_teacher_id
            else None
        )
        if employee is not None and employee.user_id in staff_user_ids:
            room.class_teacher_id = None
            session.add(room)
    session.commit()

    for employee in session.exec(select(Employee)).all():
        if employee.user_id not in staff_user_ids:
            continue
        for row in session.exec(
            select(TeacherSubject).where(TeacherSubject.teacher_id == employee.id)
        ).all():
            session.delete(row)
        for row in session.exec(
            select(EmployeeSalary).where(EmployeeSalary.employee_id == employee.id)
        ).all():
            session.delete(row)
        for row in session.exec(
            select(SubjectTeacher).where(SubjectTeacher.teacher_id == employee.id)
        ).all():
            session.delete(row)
        session.commit()
        session.delete(employee)
        session.commit()

    for user_id in user_ids:
        user = session.get(User, user_id)
        if user is None:
            continue
        for role in session.exec(
            select(UserRole).where(UserRole.user_id == user_id)
        ).all():
            session.delete(role)
        session.commit()
        session.delete(user)
        session.commit()



# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the schools through the admission and teacher forms."
    )
    parser.add_argument("--school", help="school code (abc); default: every school")
    parser.add_argument("--sections", default=",".join(SECTIONS))
    parser.add_argument("--min", dest="minimum", type=int, default=MIN_PER_SECTION)
    parser.add_argument("--max", dest="maximum", type=int, default=MAX_PER_SECTION)
    parser.add_argument("--attendance-days", type=int, default=ATTENDANCE_DAYS)
    parser.add_argument("--password", default=DEMO_PASSWORD)
    parser.add_argument("--seed", type=int, default=20260401)
    parser.add_argument(
        "--reset", action="store_true", help="delete what this seeder wrote first"
    )
    parser.add_argument(
        "--without-teachers", action="store_true", help="skip the staff and the teachers"
    )
    args = parser.parse_args()

    sections = tuple(
        part.strip().lower() for part in args.sections.split(",") if part.strip()
    )
    if not sections or args.minimum > args.maximum:
        print("[seed] nothing to do - check --sections / --min / --max")
        return 1

    today = date.today()
    _cheap_passwords()
    # One hash for every seeded account: the password is the same, and bcrypt would
    # otherwise run thousands of times.
    demo_hash = get_password_hash(args.password)
    print(
        f"[seed] sections {', '.join(name.upper() for name in sections)}, "
        f"{args.minimum}-{args.maximum} students each, password '{args.password}'"
    )

    with Session(engine) as session:
        schools = list(session.exec(select(School).order_by(School.code)).all())
        if args.school:
            schools = [
                school
                for school in schools
                if school.code.lower() == args.school.lower()
            ]
        if not schools:
            print(f"[seed] no school found ({args.school or 'any'}) - run scripts/seed.py first")
            return 1

        # Read before any school is bound: the logins this run must not collide with
        # belong to every school.
        reserved = _reserved_logins(session)

        for school in schools:
            bound_to(session, school.id)
            if args.reset:
                # A session of its own: the seeding below then starts from a clean
                # identity map instead of reusing instances the reset deleted.
                with Session(engine) as reset_session:
                    bound_to(reset_session, school.id)
                    _reset(reset_session, school)
                session.expunge_all()
                # Read again: the logins the reset removed must not stay reserved.
                reserved = _reserved_logins(session)
                print(f"[seed] {school.code}: cleared what an earlier run wrote")

            # A seed of its own per school, so re-running one does not reshuffle the
            # other - and the plan is the same on every start, which is what makes
            # "insert only what is missing" safe.
            planner = SchoolPlanner(
                rng=random.Random(f"{args.seed}:{school.code}"),
                code=school.code.lower(),
                today=today,
                taken=set(reserved),
            )
            stats: dict[str, int] = Counter()
            classes = session.exec(select(ClassName).order_by(ClassName.level)).all()
            section_rows = {
                row.section_name: row for row in session.exec(select(Section)).all()
            }
            subjects = session.exec(select(Subject)).all()
            labels: list[tuple[str, UUID | None]] = []

            for classroom in classes:
                for name in sections:
                    row = section_rows.get(name)
                    if row is None:
                        print(
                            f"[seed] {school.code}: no section '{name}' in the "
                            "catalog - skipped"
                        )
                        continue
                    plans = planner.students_for(
                        classroom.classname,
                        classroom.level,
                        name,
                        classroom.class_id,
                        row.section_id,
                    )
                    _apply_students(session, plans, demo_hash, stats)
                    labels.append(
                        (f"{classroom.classname}-{name}", _room_id(session, classroom.classname, name))
                    )
                    print(f"[seed] {school.code}: {classroom.classname}-{name} -> {len(plans)} students")

            if not args.without_teachers:
                _apply_staff(
                    session,
                    planner.staff_for([subject.id for subject in subjects], labels),
                    demo_hash,
                    stats,
                )
            if args.attendance_days:
                _apply_attendance(
                    session, args.attendance_days, f"{args.seed}:{school.code}", stats
                )
            _apply_leaves(session, f"{args.seed}:{school.code}", stats)

            print(
                f"[seed] {school.code}: {stats['students_added']} students added, "
                f"{stats['students_present']} already there | "
                f"{stats['student_logins']} student logins, "
                f"{stats['guardian_logins']} guardian logins | "
                f"{stats['staff_added']} staff added "
                f"({stats['class_teachers']} class teachers, "
                f"{stats['class_teacher_missing']} unassigned) | "
                f"{stats['attendance_rows']} attendance rows, "
                f"{stats['leave_requests']} leave requests | "
                f"{stats['separated']} separated"
            )
    print(f"[seed] done - every seeded account signs in with '{args.password}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())










