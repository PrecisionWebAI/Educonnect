from datetime import date
from uuid import UUID
from pydantic import BaseModel

from app.core import lifecycle
from app.core.text import CanonicalRequest
from .models import StudentBase



class StudentCreate(CanonicalRequest, StudentBase):
    pass


class StudentRead(StudentBase):
    """One row of the student directory.

    Every form field comes along (the row holds the whole record now), plus the
    display values the screen needs: the class and the section letter behind
    `classroom_id`, the roll status, and the guardian the school records first for
    this child - their name, their login, and the name the directory shows.
    """

    id: UUID
    name: str | None = None
    admissionNo: str | None = None
    className: str | None = None
    section: str | None = None
    gender: str = "Male"
    #: The guardian's name - the directory's Guardian column.
    guardian_name: str | None = None
    guardian: str | None = None
    phone: str | None = None
    email: str | None = None
    #: "Active" / "Inactive" for the **roll**, read from the lifecycle columns
    #: (`students/lifecycle.py`): a child who has left is Inactive, whatever their
    #: login is doing - a student's login is never switched off.
    status: str = "Active"
    #: When the child left the roll (`students/lifecycle.py`): `leftOn` is the day the
    #: office recorded, `deactivatedAt` when the button was pressed. Both `None` while
    #: they are on the roll; the directory shows the "Inactive" badge from `status`.
    leftOn: str | None = None
    deactivatedAt: str | None = None
    #: The guardian's login (through `student_guardian_relationship`), when they
    #: have one. The directory counts these to show how many parents actually have
    #: an account, and shows the address so the office can hand it over.
    guardianEmail: str | None = None
    guardianUserId: UUID | None = None


class StudentUpdate(CanonicalRequest):
    """What a student edit may change (guardians have their own API)."""

    date_of_birth: date | None = None
    section_id: UUID | None = None


class GuardianLinkRead(BaseModel):
    """One guardian of one student, as the card on their screen shows them.

    `phone`/`email` are the **person's** contact (the same row serves every child of the
    family); `relation` and `isPrimary` belong to the *link*, because a parent can be
    "father" for one child and simply the guardian for another.
    """

    linkId: UUID
    guardianId: UUID
    name: str
    relation: str
    isPrimary: bool
    phone: str
    email: str | None = None
    alternatePhone: str | None = None
    occupation: str | None = None
    address: str | None = None
    #: The login they sign in with, when they have one.
    loginEmail: str | None = None
    #: The first-time password, present **only** on the response that created the
    #: account - the same promise the admission register makes.
    password: str | None = None


class GuardianWrite(CanonicalRequest):
    """Body of the guardian add/edit endpoints (the card's form)."""

    name: str
    phone: str
    relation: str | None = None
    email: str | None = None
    alternate_phone: str | None = None
    occupation: str | None = None
    address: str | None = None
    #: The guardian the school records first for this child. The first guardian of a
    #: student is primary whether or not the form says so.
    is_primary: bool = False


class GuardianRemoveResult(BaseModel):
    """What removing a guardian actually did.

    The **link** goes; the person does not. Their login, their phone number and their
    other children are untouched - a parent outlives one child's record.
    """

    removed: bool = True
    guardianId: UUID
    #: True when the person has no other child here any more (they still exist, but
    #: nothing links them to the school).
    personKept: bool = True
    #: True when the removal handed `is_primary` to another guardian.
    primaryMovedTo: str | None = None


class StudentDeleteResult(BaseModel):
    """What deleting a student actually removed.

    A class-section exists because students sit in it, so when the **last** one
    goes the class-section goes with them - and `classroomRemoved` names it
    ("Class 10-A"), which is what the screen tells the operator. `None` means the
    student's class-section is still in use (or they had none).
    """

    deleted: bool = True
    id: UUID
    classroomRemoved: str | None = None
    #: True when the child's login was removed with them. `False` means it is still
    #: there, because the same person signs in as something else (a parent, staff) -
    #: a login only ever goes when it opened nothing else.
    loginRemoved: bool = False


#: The lifecycle vocabulary - the request body and the answer the button gets - is shared
#: with the Staff Hiring screen (`app/core/lifecycle.py`), so both screens mean the same
#: thing by deactivate, reactivate and the same thing by the sentence they show.
LifecycleRequest = lifecycle.LifecycleRequest
StudentLifecycleRead = lifecycle.LifecycleRead
