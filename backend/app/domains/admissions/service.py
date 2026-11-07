"""Admission service - the Operations > Admission workflow.

One learner is one row (`student`, reached through the `AdmissionApplication`
alias) and there is **no draft**: what this module saves is a student the school
has admitted. Four things here are more than plain CRUD:

* `admission_number` is minted server-side (`ADM-2026-0141`) as the row is created,
  so two open forms in two browsers can never claim the same number - and every
  student has one from their first save, because there is no half-made student to
  sit before it.
* Saving the form **is** the admission (see `_admit`): the student row, the guardian
  (a person row of their own, shared with any siblings), the link between the two
  and the logins the form's own emails make are created together. A form missing
  what a student cannot be without is refused (`422`) rather than half-stored -
  which is exactly what lets the directory treat every row it lists as a student.
* The **class-section** the form asked for is created when the school does not have
  it yet, so admitting a student is what puts that classroom on the Classroom screen.
* A **separation** records why and when a student left. The row is then reported as
  Inactive - derived from the separation block itself rather than stored as a second
  flag that could disagree with it.

Logins are **emails only** - the student's own email, and the guardian's. A phone
number is never a login: it is how the school rings the family, not something a
person signs in with. Nothing is generated, so a form that leaves the student's
address out leaves that child without a login of their own (the office can add one
later) and the response says so in its notes. The **guardian's** email, by contrast,
is mandatory: it is the family's only way in. A contact that is **edited later**
moves the login with it (`_sync_logins`), so a student and their account can never
disagree. The first-time password is returned exactly once, on the response that
created it.
"""

from datetime import date
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core import contacts
from app.core.security import generate_temp_password, get_password_hash
from app.core.text import canonical, canonical_phone, phone_problem
from app.domains.academics.models import ClassName, Section
from app.domains.academics.repository import ensure_room, find_classroom, find_section
from app.domains.auth.models import utcnow
from app.domains.auth.roles import set_user_roles
from app.domains.students import repository as students_repository
from app.domains.students.models import Guardian, StudentGuardianRelationship
from app.domains.users.models import User

from . import repository
from .models import AdmissionApplication
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionApplicationUpdate,
    LoginCredential,
    PasswordResetRead,
    SeparationRecordWrite,
)

# Fields the server owns: a full-row update must never blank them out (neither
# with `null` nor with an empty string).
_SERVER_MANAGED = ("admission_number", "created_on")


def _read(
    application: AdmissionApplication,
    *,
    guardian: Guardian | None = None,
    relation: str | None = None,
    emails: dict[UUID, str] | None = None,
    guardian_emails: dict[UUID, str] | None = None,
) -> AdmissionApplicationRead:
    """ORM row -> response model, with what the row does not store looked up.

    The row **is** the student, so `student_id` is its own id. Nothing about the
    family is copied onto the child: the guardian block comes from the **person**
    the school records first for them (the primary `guardian`, plus the relation
    that belongs to *this* link), and the two logins are looked up - the student's
    from the row's own `user_id`, the guardian's from that person's.
    """
    lookup = emails or {}
    guardians = guardian_emails or {}
    return AdmissionApplicationRead.model_validate(
        {
            **application.model_dump(),
            "separation": application.separation,
            "student_id": application.id,
            "student_login_email": lookup.get(application.user_id),
            "guardian_login_email": guardians.get(application.id),
            "guardian_name": guardian.name if guardian else None,
            "guardian_relation": relation if guardian else None,
            "guardian_phone": guardian.phone if guardian else None,
            "guardian_email": guardian.email if guardian else None,
            "guardian_occupation": guardian.occupation if guardian else None,
            "guardian_address": guardian.address if guardian else None,
        }
    )


def _read_one(
    session: Session, application: AdmissionApplication
) -> AdmissionApplicationRead:
    """`_read` for a single row - the lookups it needs, for one student."""
    family = students_repository.primary_guardian_links(session).get(application.id)
    return _read(
        application,
        guardian=family[0] if family else None,
        relation=family[1] if family else None,
        emails=_login_emails(session),
        guardian_emails=_guardian_login_emails(session),
    )


def _login_emails(session: Session) -> dict[UUID, str]:
    """{user_id: email} - so a list of students can show the logins it made."""
    return {
        user.id: user.email for user in session.exec(select(User)).all() if user.id
    }


def _guardian_login_emails(session: Session) -> dict[UUID, str]:
    """{student_id: the guardian's login email} for every student that has one.

    One query for the whole list, so the table can show the family's login beside
    the child without a read per row.
    """
    rows = session.exec(
        select(StudentGuardianRelationship.student_id, User.email)
        .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
        .join(User, User.id == Guardian.user_id)
    ).all()
    return {
        student_id: email for student_id, email in rows if student_id is not None
    }


def _get_or_404(session: Session, application_id: UUID) -> AdmissionApplication:
    application = repository.get_application_by_id(session, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Student not found")
    return application


def get_applications(
    session: Session, skip: int = 0, limit: int = 500
) -> list[AdmissionApplicationRead]:
    """Every student, newest first - what the admission screen lists."""
    emails = _login_emails(session)
    guardian_emails = _guardian_login_emails(session)
    families = students_repository.primary_guardian_links(session)
    reads: list[AdmissionApplicationRead] = []
    for row in repository.get_applications(session, skip, limit):
        family = families.get(row.id)
        reads.append(
            _read(
                row,
                guardian=family[0] if family else None,
                relation=family[1] if family else None,
                emails=emails,
                guardian_emails=guardian_emails,
            )
        )
    return reads


def contact_lookup(
    session: Session, *, phone: str | None = None, email: str | None = None
) -> dict:
    """Who a phone number or an email already belongs to - the form's popup.

    The admission form calls this as soon as the office leaves the guardian's phone
    or email field: if somebody with that contact is already on file, their name,
    their roles and the children already linked to them come back, so the block can
    be filled in and the new child linked to that family instead of a second row
    being made for the same parent.
    """
    return contacts.contact_read(session, phone=phone, email=email)


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplicationRead:
    """Save the form: the student, their family and their logins, in one go.

    There is no draft, so this is the only way a student enters the product, and the
    checks run **before** anything is written: a refused form leaves nothing behind.
    `admission_number` is minted here (unless the caller brought one) because a row
    with no number is not a student the roll can name.
    """
    if not application_in.admission_number:
        application_in.admission_number = repository.next_admission_number(session)
    _guard_admission(
        session,
        values=_values_of(application_in),
        allow=_allow_ids(session, application_in),
        student_user_id=None,
        student_id=None,
    )
    application = repository.create_application(session, application_in)
    credentials, note = _admit(session, application, _guardian_block(application_in))
    read = _read_one(session, application)
    read.credentials = credentials or None
    read.placement_note = note
    return read


def update_application(
    session: Session,
    application_id: UUID,
    application_in: AdmissionApplicationUpdate,
) -> AdmissionApplicationRead:
    """Write the form back over a student (the office correcting a record).

    The guardian block is written to the **person** the child is linked to
    (`_apply_guardian`), because that is where the contact lives now - the same edit
    made on the guardian card does exactly this. Nothing is half-applied: the
    mandatory fields and the "one contact, one person" rule are checked first, so a
    refused edit leaves the record as it was.
    """
    application = _get_or_404(session, application_id)
    guardian = _primary_guardian(session, application.id)
    patch = _guardian_patch(application_in)
    _guard_admission(
        session,
        values=_values_of(application_in, guardian=guardian, patch=patch),
        allow=_allow_ids(session, application, guardian=guardian),
        student_user_id=application.user_id,
        student_id=application.id,
    )
    for field, value in application_in.model_dump(exclude_unset=True).items():
        # The guardian block is not a student column, so it never lands on the row;
        # the server's own fields (the number, the day the row was written) stay.
        if not hasattr(application, field) or field in _SERVER_MANAGED:
            continue
        setattr(application, field, value)
    application = repository.save_application(session, application)
    notes = _apply_guardian(session, application, guardian, patch)
    # The contact may have changed, so the logins follow it before the row is read
    # back - the response then shows the addresses that are actually in use.
    notes += _sync_logins(session, application)
    read = _read_one(session, application)
    read.placement_note = " ".join(filter(None, notes)) or None
    return read


def record_separation(
    session: Session,
    application_id: UUID,
    separation_in: SeparationRecordWrite,
) -> AdmissionApplicationRead:
    """Record why and when a student left; the row then reports as Inactive."""
    application = _get_or_404(session, application_id)
    application.separation_reason = separation_in.reason
    application.separation_session = separation_in.session
    application.separation_date = separation_in.date
    if separation_in.dropped_class:
        application.separation_dropped_class = separation_in.dropped_class
    application = repository.save_application(session, application)
    # The guardian block and the two logins are looked up with the row - a
    # separation changes none of them, but the answer has to be the same shape.
    return _read_one(session, application)


# ---------------------------------------------------------------------------
# What a student cannot be without
#
# This rule used to be phrased as "what a form needs to be *registered*", because a
# half-filled row could sit in the table as a draft. There is no draft any more, so
# the same list is now the condition of the row existing at all - and it is checked
# on the way in, before anything is written, rather than on the way out.
# ---------------------------------------------------------------------------

#: The fields the admission form cannot be saved without: a label plus every field
#: that can satisfy it (the first one filled wins).
#:
#: The **guardian block is the only contact block**: the email the guardian signs in
#: with and the phone the school rings them on come from there, and the father /
#: mother blocks are family detail (names, occupations, income) that never carry a
#: login. The guardian's email is mandatory because it is the family's way in -
#: without it nobody can sign in for a child who has no address of their own.
#:
#: The student's **last name** is deliberately absent - many children have a single
#: name, and a school admits them every year; the first name is what identifies the
#: child.
REQUIRED_TO_ADMIT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("the student's first name", ("student_first_name",)),
    ("the class applied for", ("applied_for_class_level",)),
    ("the guardian's name", ("guardian_name",)),
    ("the guardian's email", ("guardian_email",)),
    ("the guardian's phone number", ("guardian_phone",)),
)

#: The phone number the school actually rings, with the name the office knows it by:
#: a guardian number that is not ten digits is refused rather than stored, so a
#: family can never be filed under a number that does not exist. The father / mother
#: numbers are family detail rather than contacts, so the rule does not judge them.
PHONE_FIELDS: tuple[tuple[str, str], ...] = (
    ("guardian_phone", "The guardian's phone number"),
)


def _require_admission_fields(values: dict[str, str | None]) -> None:
    """Refuse a form that is missing a field a student cannot be without.

    Called from every path that writes a student - the admission screen's save, an
    edit of an existing record, the seeder - so the rule cannot be bypassed by using
    one screen instead of another. The message names what is missing, because the
    office has to fill it in on the form in front of them. `422` like any other
    rejected body.
    """
    missing = [
        label
        for label, fields in REQUIRED_TO_ADMIT
        if not any((values.get(field) or "").strip() for field in fields)
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Fill in " + ", ".join(missing) + " before admitting the student",
        )

    # A number that is not ten digits is refused rather than stored: the office
    # would otherwise ring a number that does not exist, and the family would be
    # told their child is absent.
    problems = [
        problem
        for field, label in PHONE_FIELDS
        if (problem := phone_problem(values.get(field), label))
    ]
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))


def _guard_admission(
    session: Session,
    *,
    values: dict[str, str | None],
    allow: dict,
    student_user_id: UUID | None,
    student_id: UUID | None,
) -> None:
    """Everything a form must satisfy to become a student, in one call.

    Called from every path that writes a student - the admission screen's save and
    an edit of an existing record - so the rule cannot be bypassed by using one
    screen instead of another:

    * the mandatory fields and the shape of the number (`_require_admission_fields`);
    * **one contact, one person** (`app/core/contacts.py`): the guardian's phone and
      email and the student's own address must not belong to somebody else. A second
      child of the same family is *not* a clash - their guardian is already theirs -
      which is why the family's own records are passed along as allowed.
    """
    _require_admission_fields(values)
    # The student's own address belongs to the student: it is their login's when they
    # have one, and nobody else may hold it.
    contacts.require_contact_free(
        session,
        who="The student",
        email=values.get("student_email"),
        allow_user_id=student_user_id,
        allow_student_id=student_id,
    )
    contacts.require_contact_free(
        session,
        who="The guardian",
        phone=values.get("guardian_phone"),
        email=values.get("guardian_email"),
        **allow,
    )


def _values_of(
    application_in,
    *,
    guardian: Guardian | None = None,
    patch: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """The contact-bearing fields as this write will leave them.

    A create posts the whole form, so the values come straight off it. An edit posts
    the student's fields but only the guardian fields the office actually retyped, so
    an untouched guardian is read from the **person** on file - which is what the
    checks have to judge, not the blank the form left behind.
    """

    def current(field: str, on_file: str | None) -> str | None:
        if patch is None:
            return getattr(application_in, field, None)
        return patch.get(field, on_file)

    return {
        "student_first_name": application_in.student_first_name,
        "student_email": application_in.student_email,
        "applied_for_class_level": application_in.applied_for_class_level,
        "guardian_name": current("guardian_name", guardian.name if guardian else None),
        "guardian_email": current(
            "guardian_email", guardian.email if guardian else None
        ),
        "guardian_phone": current(
            "guardian_phone", guardian.phone if guardian else None
        ),
    }


def _guardian_patch(application_in) -> dict[str, str | None]:
    """The guardian fields **this request carried** (`guardian_*` -> value).

    The request schema defaults the whole block to `None`, so what a body did not
    mention has to be left exactly as the person already has it: that is what makes
    the block optional on an edit without ever blanking a contact nobody touched.
    """
    return {
        field: value
        for field, value in application_in.model_dump(exclude_unset=True).items()
        if field.startswith("guardian_")
    }


def _family_guardian(
    session: Session, application, guardian: Guardian | None = None
) -> Guardian | None:
    """The guardian this form belongs to - the row's own, or a **sibling's** match.

    A second child's form carries the same guardian email as the first child's, and
    that guardian row *is* this family's - so it is theirs to keep, not somebody
    else's to borrow. Reading it here is what lets one parent stay one row, one
    number and one login however many children they have.

    `guardian_email` is read off the **request**: a stored student has no guardian
    columns any more, and this only runs before the row exists.
    """
    if guardian is not None:
        return guardian
    if getattr(application, "id", None):
        own = _primary_guardian(session, application.id)
        if own is not None:
            return own
    return _find_guardian(session, _login_email(getattr(application, "guardian_email", None)))


def _allow_ids(session: Session, application, guardian: Guardian | None = None) -> dict:
    """The guardian-side records of this form's family.

    The **login** is part of it: the guardian's email is the address their account
    signs in with, so a check that sees the login first must recognise it as the
    same person.
    """
    holder = _family_guardian(session, application, guardian)
    return {
        "allow_user_id": holder.user_id if holder is not None else None,
        "allow_guardian_id": holder.id if holder is not None else None,
        "allow_student_id": getattr(application, "id", None),
    }


def _login_email(value: str | None) -> str | None:
    """The login a person gets: **the email on the form, and nothing else**.

    A phone number is deliberately *not* a login. It reads like a user name and one
    number can be shared by a whole family, but it is not an address anybody owns -
    the school can never mail it - and typing "9876543210" as a user name invites
    two people to sign in as one account. `None` means the form left the address
    out, and the person is created without a login rather than with an address
    nobody owns.
    """
    return canonical(value) or None


def _student_name(application: AdmissionApplication) -> str:
    """The child's display name, from the three name columns the form fills."""
    parts = (
        application.student_first_name,
        application.student_middle_name,
        application.student_last_name,
    )
    name = " ".join(part.strip() for part in parts if part and part.strip())
    return name or "Student"


def _login_taken(session: Session, login: str) -> bool:
    """True when an account already signs in with this email."""
    return (
        session.exec(
            select(User.id).where(func.lower(User.email) == login.strip().lower())
        ).first()
        is not None
    )


def _find_guardian(session: Session, email: str | None) -> Guardian | None:
    """The guardian already on file for this email, if any.

    A parent's **second child** shares one guardian row - and one login: the form
    carries the same address, so the office is never asked to type the same parent
    twice and the school ends up with a single contact for the family.
    """
    if not email or not email.strip():
        return None
    return session.exec(
        select(Guardian).where(func.lower(Guardian.email) == email.strip().lower())
    ).first()


def _primary_guardian(session: Session, student_id: UUID) -> Guardian | None:
    """The guardian the school records first for this student.

    `is_primary` decides; two guardians added in the same breath are ordered by
    when their row was written, so the answer is stable rather than random.
    """
    return session.exec(
        select(Guardian)
        .join(
            StudentGuardianRelationship,
            StudentGuardianRelationship.guardian_id == Guardian.id,
        )
        .where(StudentGuardianRelationship.student_id == student_id)
        .order_by(
            StudentGuardianRelationship.is_primary.desc(), Guardian.created_at
        )
    ).first()


def _apply_guardian(
    session: Session,
    application: AdmissionApplication,
    guardian: Guardian | None,
    patch: dict[str, str | None],
) -> list[str]:
    """Write the guardian block a form carried onto the **person**.

    A guardian is a row of their own, shared with any siblings, so the contact the
    office retyped on the admission form belongs to that row - never to the child.
    The phone and the email move the way every other edit of that person moves them
    (`contacts.sync_contact`): their login, their guardian row and - when they also
    work here - their staff row go together, and a contact somebody else holds is
    never taken over (the note says so instead).

    An empty patch means the form said nothing about the guardian, and nothing is
    written: that is what keeps an edit of a student's marks-history from quietly
    rewriting a parent.

    A child who somehow has no guardian on file (a record older than the guardian
    row) gets one here, so a student is never left without someone to ring.
    """
    if not patch:
        return []

    notes: list[str] = []
    if guardian is None:
        guardian = Guardian(
            name=(patch.get("guardian_name") or "").strip() or "Guardian",
            phone=canonical_phone(patch.get("guardian_phone")) or "",
            email=_login_email(patch.get("guardian_email")),
            occupation=patch.get("guardian_occupation") or None,
            address=patch.get("guardian_address") or None,
        )
        session.add(guardian)
        session.commit()
        session.refresh(guardian)
        session.add(
            StudentGuardianRelationship(
                student_id=application.id,
                guardian_id=guardian.id,
                relationship_type=canonical(patch.get("guardian_relation")) or "guardian",
                is_primary=True,
            )
        )
        session.commit()
        notes.append(f"{guardian.name} was added as this child's guardian.")

    name = (patch.get("guardian_name") or "").strip()
    if name and name != guardian.name:
        previous, guardian.name = guardian.name, name
        session.add(guardian)
        session.commit()
        notes.append(f"The guardian's name changed from '{previous}' to '{name}'.")

    for field, label in (
        ("guardian_occupation", "occupation"),
        ("guardian_address", "address"),
    ):
        if field not in patch:
            continue
        column = field.replace("guardian_", "")
        value = (patch.get(field) or "").strip() or None
        if value != getattr(guardian, column):
            setattr(guardian, column, value)
            session.add(guardian)
            session.commit()
            notes.append(f"The guardian's {label} is now '{value or '-'}'.")

    # The contact itself - one person, one phone, one email. This is the same walk
    # the guardian card and the hire form take, so all three agree by construction.
    notes += contacts.sync_contact(
        session,
        guardian_id=guardian.id,
        email=_login_email(patch.get("guardian_email")),
        phone=patch.get("guardian_phone"),
    )

    relation = canonical(patch.get("guardian_relation"))
    if relation:
        link = session.exec(
            select(StudentGuardianRelationship).where(
                StudentGuardianRelationship.student_id == application.id,
                StudentGuardianRelationship.guardian_id == guardian.id,
            )
        ).first()
        if link is not None and link.relationship_type != relation:
            link.relationship_type = relation
            session.add(link)
            session.commit()
            notes.append(
                f"The relationship on this child's record is now '{relation}'."
            )
    return notes


def _guardian_block(application_in) -> dict[str, str | None]:
    """The guardian block exactly as the **form** wrote it.

    A guardian is normally edited on their own card (`students/guardians.py`); the
    admission form is the one place a person is *created* from a block, so this is
    what `_admit` builds the `guardian` row from. Nothing here is a student column -
    the block belongs to the request, and it is gone as soon as the person exists.
    """
    return {
        "guardian_name": getattr(application_in, "guardian_name", None),
        "guardian_phone": getattr(application_in, "guardian_phone", None),
        "guardian_email": getattr(application_in, "guardian_email", None),
        "guardian_relation": getattr(application_in, "guardian_relation", None),
        "guardian_occupation": getattr(application_in, "guardian_occupation", None),
        "guardian_address": getattr(application_in, "guardian_address", None),
    }


def _sync_logins(session: Session, application: AdmissionApplication) -> list[str]:
    """Follow the record: a login **is** the email stored on the row.

    Runs on every write to a student, so a login can never drift away from the
    contact the office has on file. The address a login is moved to is always the
    one **stored** - never the one a request happened to carry - which is what used
    to go wrong: an earlier version pushed whatever the form said, even when the
    write had been refused, and left the account pointing at an address the record
    did not hold.

    The **guardian's** half of the sync lives with the write that changes them
    (`_apply_guardian` -> `contacts.sync_contact`, which moves their login, their
    guardian row and their staff row together), so it happens exactly once, on the
    path that actually edited that person.
    """
    if not application.user_id:
        # A child with no account of their own: the family signs in through the
        # guardian's, so there is nothing of theirs to keep in step.
        return []
    user = session.get(User, application.user_id)
    if user is None:
        return []
    wanted = _login_email(application.student_email)
    if not wanted:
        return [
            f"The record carries no student email, so the login is still "
            f"'{user.email}'."
        ]
    if wanted.lower() == user.email.lower():
        return []
    if _login_taken(session, wanted):
        return [
            f"'{wanted}' already belongs to another login, so the student login is "
            f"still '{user.email}'."
        ]
    previous = user.email
    user.email = wanted
    session.add(user)
    session.commit()
    return [f"The student login changed from '{previous}' to '{wanted}'."]


def _admit(
    session: Session, application: AdmissionApplication, block: dict[str, str | None]
) -> tuple[list[LoginCredential], str | None]:
    """Put a student on the roll: class-section, their login, the guardian, the link.

    The row **is** the student, so there is nothing to copy over: this creates what
    only exists once a child is admitted - their login, the class-section they sit
    in, the guardian (a person row of their own, shared with any siblings) with their
    login, and the link between the two. `block` is the form's guardian block, which
    is *not* a student column: it is what the person is built from.

    Idempotent: every step asks whether it has already been done, so calling it again
    (a retried request, the seeder re-running over a half-finished database) can never
    mint a second login or a second guardian. Returns the logins it created - each
    with its one-time password, the only moment it exists - and an optional note
    about anything the office should look at.
    """
    # The class and the section are ids into the two platform catalogs, and the
    # school's class-section row is created the first time it is used: admitting a
    # student into "Class 10-A" is what puts that card on the Classroom screen.
    classroom = (
        session.get(ClassName, application.applied_class_id)
        if application.applied_class_id
        else find_classroom(session, application.applied_for_class_level)
    )
    named_section = (application.applied_section_preference or "").strip()
    section = (
        session.get(Section, application.applied_section_id)
        if application.applied_section_id
        else find_section(session, named_section)
    )
    if section is None and not named_section:
        # The form named no section at all, so the student goes to the usual "A".
        section = find_section(session, "A")
    room = (
        ensure_room(session, classroom.class_id, section.section_id)
        if classroom is not None and section is not None
        else None
    )

    notes: list[str] = []
    if classroom is None:
        # The student still gets an account and a directory row - only the
        # class/section placement is left for the office to fix.
        notes.append(
            f"Class '{application.applied_for_class_level or '-'}' is not in the "
            "school's class list, so the student was created without a class or "
            "section."
        )
    elif section is None:
        notes.append(
            f"Section '{named_section}' is not one of the school's sections "
            "(A-J), so the student was created without a class-section."
        )
    if application.date_of_birth is None:
        notes.append(
            "Date of birth was not on the form; today's date was stored instead."
        )

    credentials: list[LoginCredential] = []

    # --- 1. the student: the row itself, plus their own login ----------------
    student_name = _student_name(application)
    # The name is kept on the row too: a student without a login still has one.
    application.full_name = student_name
    application.date_of_birth = application.date_of_birth or date.today()
    application.gender = application.gender or None
    # The class-section row this student sits in - the one created just above.
    application.classroom_id = room.id if room else None
    application.activated_at = application.activated_at or utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)

    # The login is the student's own email - and nothing else. A form that leaves it
    # out leaves the student without a login (the office can add one), because an
    # address nobody owns can never be signed in with; the guardian's account is the
    # family's way in.
    student_login = _login_email(application.student_email)
    if student_login and application.user_id is None:
        if _login_taken(session, student_login):
            notes.append(
                f"The email '{student_login}' already belongs to a login, so the "
                "student was created without one."
            )
        else:
            student_password = generate_temp_password()
            student_user = User(
                email=student_login,
                full_name=student_name,
                hashed_password=get_password_hash(student_password),
                is_active=True,
            )
            session.add(student_user)
            session.commit()
            session.refresh(student_user)
            set_user_roles(session, student_user, ["student"])
            application.user_id = student_user.id
            session.add(application)
            session.commit()
            session.refresh(application)
            credentials.append(
                LoginCredential(
                    role="student",
                    full_name=student_name,
                    email=student_login,
                    password=student_password,
                )
            )
    elif not application.user_id and not student_login:
        notes.append(
            "The form carried no student email, so the student was created without "
            "a login of their own."
        )

    # --- 2. the guardian: one person row, shared by all their children -------
    # The guardian block is the only contact block: its email is their login and its
    # phone is the number the school rings. A family's second child finds the same
    # guardian here, so only the child link is added.
    guardian_name = (block.get("guardian_name") or "").strip()
    guardian_email = _login_email(block.get("guardian_email"))
    relationship = canonical(block.get("guardian_relation")) or "guardian"
    guardian = _find_guardian(session, guardian_email)
    # One contact, one person. The guardian already on file for this address is *this*
    # family (a sibling's form), so it is allowed; a number or address that belongs to
    # somebody else is refused here rather than half-written. `_guard_admission` made
    # the same check before anything was saved - this one is the last line of defence,
    # right where the person is written.
    contacts.require_contact_free(
        session,
        who="The guardian",
        phone=block.get("guardian_phone"),
        email=guardian_email,
        allow_user_id=guardian.user_id if guardian is not None else None,
        allow_guardian_id=guardian.id if guardian is not None else None,
        allow_student_id=application.id,
    )
    if guardian is None and guardian_name:
        guardian = Guardian(
            name=guardian_name,
            phone=canonical_phone(block.get("guardian_phone")) or "",
            email=guardian_email,
            occupation=block.get("guardian_occupation") or None,
            address=block.get("guardian_address") or None,
        )
        session.add(guardian)
        session.commit()
        session.refresh(guardian)

    if guardian is not None:
        guardian_password: str | None = None
        if guardian_email and guardian.user_id is None:
            # Their account: one login per parent, whatever the number of children.
            if _login_taken(session, guardian_email):
                notes.append(
                    f"The email '{guardian_email}' already belongs to another login, "
                    "so the guardian was created without one."
                )
            else:
                guardian_password = generate_temp_password()
                guardian_user = User(
                    email=guardian_email,
                    full_name=guardian.name,
                    hashed_password=get_password_hash(guardian_password),
                    is_active=True,
                )
                session.add(guardian_user)
                session.commit()
                session.refresh(guardian_user)
                set_user_roles(session, guardian_user, ["guardian"])
                guardian.user_id = guardian_user.id
                session.add(guardian)
                session.commit()
                session.refresh(guardian)
        if guardian.user_id is not None:
            # A login the family already had is reported too, without a password:
            # the panel shows the address and offers a reset.
            credentials.append(
                LoginCredential(
                    role="guardian",
                    full_name=guardian.name,
                    email=guardian.email or guardian_email or "",
                    password=guardian_password,
                    created=guardian_password is not None,
                )
            )

        # The link is what makes "their children" answerable, and it carries the
        # relation the form wrote for **this** child.
        linked = session.exec(
            select(StudentGuardianRelationship).where(
                StudentGuardianRelationship.student_id == application.id,
                StudentGuardianRelationship.guardian_id == guardian.id,
            )
        ).first()
        if linked is None:
            session.add(
                StudentGuardianRelationship(
                    student_id=application.id,
                    guardian_id=guardian.id,
                    relationship_type=relationship,
                    is_primary=True,
                )
            )
            session.commit()

    return credentials, (" ".join(notes) or None)


def reset_login_password(
    session: Session, application_id: UUID, target: str
) -> PasswordResetRead:
    """Mint a new first-time password for the student or the guardian login."""
    if target not in ("student", "guardian"):
        raise HTTPException(
            status_code=422, detail="target must be 'student' or 'guardian'"
        )
    application = _get_or_404(session, application_id)
    if target == "student":
        # The row is the student, so their login is the row's own `user_id`.
        user_id = application.user_id
    else:
        guardian = _primary_guardian(session, application.id)
        user_id = guardian.user_id if guardian else None
    if user_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"This student has no {target} login (the record carries no email "
                "for them), so there is nothing to reset."
            ),
        )
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"{target} login not found")

    password = generate_temp_password()
    user.hashed_password = get_password_hash(password)
    session.add(user)
    session.commit()
    return PasswordResetRead(
        role=target, full_name=user.full_name, email=user.email, password=password
    )
