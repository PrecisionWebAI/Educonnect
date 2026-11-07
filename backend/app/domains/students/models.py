"""The student - one row per learner, from admission to the roll.

`student` is the **merged** record. It carries what the admission form collects
(identity, family detail, previous school, the placement the family asked for, the
separation block written when the child leaves) *and* what the school needs once
the child is on the roll (their login, the admission number, the class-section).

Why one table
-------------
One learner used to be two rows: `student_admission_form` (the form) and
`Student` (the student), holding the child's name, date of birth and gender
twice. Registering copied one into the other, so a form edited afterwards could
disagree with the directory.

There is exactly one row per learner now, and there is **no draft**: a row in this
table is a student the school has admitted. "The form" was never a second kind of
thing - the office typing a child's name *is* the office describing a student - so
the half-filled row the screens used to park here (with a `status` of `Draft`) is
gone, and with it the three things it dragged along: a student nobody could find
in the directory, an `application_no` separate from the `admission_number` that
replaced it, and a guardian contact block duplicated onto every child. An
application that is not ready to be a student is simply not saved yet; the
admission screen asks for what a student cannot be without, on the first save.

Who fills what
--------------
* the **admission screen** (`admissions/service.py`) writes the row, its guardian
  link and their logins in one go - a student exists exactly when the form was
  complete;
* the **directory** reads the row and its guardian links.

Where the guardian is
---------------------
The guardian is deliberately **not** a column here. A parent is a person who may
have several children in the school, so they are their own row (`Guardian`, with
their own login, phone and email) joined to the student through
`StudentGuardianRelationship`. That is what makes their phone and email unique per
school without being copied onto every child, and what lets a teacher who leaves
keep their parent access (leaving staff never touches the guardian row).
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class StudentBase(SQLModel):
    """Every column of the student row - the form's fields and the roll's fields."""

    # ---- workflow --------------------------------------------------------
    created_on: date = Field(default_factory=date.today)
    notes: str | None = None

    # ---- identity --------------------------------------------------------
    #: The display name (the directory, marks and the register all show this one).
    full_name: str | None = None
    student_first_name: str | None = None
    student_middle_name: str | None = None
    student_last_name: str | None = None
    #: The student's own address. Optional: a child without one has no login of
    #: their own and signs in through the guardian's account.
    student_email: str | None = None
    #: The date of birth the school recorded. Optional: not every family brings
    #: papers on the day they join, and a blank beats an invented date.
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    religion: str | None = None
    category: str | None = None
    mother_tongue: str | None = None
    nationality: str | None = None
    aadhaar_id: str | None = None
    address: str | None = None
    permanent_address: str | None = None

    # ---- previous school -------------------------------------------------
    previous_school_name: str | None = None
    previous_class_passed: str | None = None
    previous_board: str | None = None
    transfer_certificate_no: str | None = None
    old_unique_id: str | None = None

    # ---- father / mother (family detail; the contact belongs to the guardian) --
    father_name: str | None = None
    father_occupation: str | None = None
    father_annual_income: str | None = None
    mother_name: str | None = None
    mother_occupation: str | None = None
    mother_annual_income: str | None = None

    # ---- placement + logistics -------------------------------------------
    #: What the family asked for ("Class 6"), kept as the wording they wrote.
    applied_for_class_level: str | None = None
    current_class_or_last_class: str | None = None
    applied_section_preference: str | None = None
    needs_transport: str | None = None
    transport_route: str | None = None
    needs_hostel: str | None = None
    applied_class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    applied_section_id: UUID | None = Field(
        default=None, foreign_key="section.section_id", index=True
    )
    current_class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    previous_class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    separation_class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )

    # ---- enrolment (stamped the moment the student is created) ------------
    #: The student's login. `None` means they have no account of their own - the
    #: guardian's login is the family's way in.
    user_id: UUID | None = Field(default=None, foreign_key="user.id", unique=True)
    #: The number the roll knows the child by (`ADM-2026-0141`), minted by the server
    #: from the school's own sequence the moment the student is created - it exists
    #: from the first save, because there is no half-made student to sit before it.
    admission_number: str | None = Field(default=None, index=True)
    classroom_id: UUID | None = Field(
        default=None, foreign_key="classroom.id", index=True
    )

    # ---- lifecycle -------------------------------------------------------
    #: Set when the student joins (or rejoins) the roll.
    activated_at: datetime | None = None
    #: Set when the child leaves. Unlike a teacher's login, a **student's login is
    #: never switched off**: the separation is what says they left, so a returning
    #: family finds everything as they left it.
    #: When the school took them off the roll. `left_on` is the day the office says they
    #: left (it can be back-dated); `deactivated_at` is when the button was pressed.
    #: Their login is **not** switched off by this - see `students/lifecycle.py`.
    deactivated_at: datetime | None = None
    left_on: date | None = None

    # ---- separation (filled in when the student leaves) ------------------
    separation_dropped_class: str | None = None
    separation_reason: str | None = None
    separation_session: str | None = None
    separation_date: date | None = None


class Student(StudentBase, TenantMixin, UUIDMixin, table=True):
    """One learner: the admission form **and** the student record, together.

    The unique rules are **per school** (`school_id` is part of every one of them):
    two schools may each hand out `ADM-2026-0001`, and the same family may use the
    same address at both. The school's other notes on the child (father, mother,
    previous school) are plain columns, so they carry no rule at all.
    """

    __tablename__ = "student"

    __table_args__ = (
        UniqueConstraint(
            "school_id", "admission_number", name="uq_student_school_admission_number"
        ),
        UniqueConstraint("school_id", "student_email", name="uq_student_school_email"),
    )

    @property
    def separation(self) -> dict | None:
        """The separation block as one object, or None while still enrolled.

        Derived (not stored) so the four separation columns stay the single source
        of truth. It lives on the **table** model rather than on the shared base so
        the request/response schemas, which inherit the base, stay plain field
        containers - `AdmissionApplicationRead` declares its own `separation` field
        and validates this dict into it.
        """
        if self.separation_date is None and not self.separation_reason:
            return None
        return {
            "dropped_class": self.separation_dropped_class,
            "reason": self.separation_reason,
            "session": self.separation_session,
            "date": self.separation_date,
        }


class GuardianBase(SQLModel):
    """A parent / guardian: one person, one contact, shared by all their children.

    Their **email is their login** and their **phone is how the school reaches
    them**; both are unique per school (`Guardian`), because the same number or
    address on two rows would mean the school cannot tell who it is calling - and
    a family's second child would quietly create a second parent instead of
    reusing the one already on file.

    A guardian **without an email has no login** (`user_id` stays `None`) and is
    still a real guardian row: the office can add an address later, and the link to
    their children is already in place.
    """

    name: str
    phone: str = Field(index=True)
    email: str | None = Field(default=None, index=True)
    #: A spare number - optional, and unique per school like the main one.
    alternate_phone: str | None = Field(default=None, index=True)
    occupation: str | None = None
    address: str | None = None
    #: The login this guardian signs in with, when they have one.
    user_id: UUID | None = Field(default=None, foreign_key="user.id", unique=True)
    created_at: datetime = Field(default_factory=utcnow)


class Guardian(GuardianBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "guardian"

    __table_args__ = (
        UniqueConstraint("school_id", "phone", name="uq_guardian_school_phone"),
        UniqueConstraint("school_id", "email", name="uq_guardian_school_email"),
        UniqueConstraint(
            "school_id", "alternate_phone", name="uq_guardian_school_alternate_phone"
        ),
    )


class StudentGuardianRelationshipBase(SQLModel):
    """One guardian of one student - what makes "their children" answerable.

    `guardian_id` repeats across students on purpose: a parent with three children
    in the school has three rows here and **one** `guardian` row.
    """

    student_id: UUID = Field(foreign_key="student.id", index=True)
    guardian_id: UUID = Field(foreign_key="guardian.id", index=True)
    #: What the form called them for **this** child: "father", "mother", "guardian".
    relationship_type: str = Field(default="guardian")
    #: The guardian whose contact the school records first for this child.
    is_primary: bool = Field(default=False)


class StudentGuardianRelationship(
    StudentGuardianRelationshipBase, TenantMixin, UUIDMixin, table=True
):
    __tablename__ = "student_guardian_relationship"

    __table_args__ = (
        UniqueConstraint(
            "student_id", "guardian_id", name="uq_student_guardian_student_guardian"
        ),
    )
