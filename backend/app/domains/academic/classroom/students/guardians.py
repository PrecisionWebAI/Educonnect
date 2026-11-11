"""The guardians of a student - what the card on their screen reads and writes.

A guardian is one **person** (`guardian`, shared by every child of that family) linked
to each child through `student_guardian_relationship`. Before this there was no way to
correct a family from a student's screen: the guardian existed only as text on the
admission form, so a wrong number meant re-registering - and a second child quietly
became a second parent.

The rules are the shared ones (`app/core/contacts.py`), applied here:

* a phone number or an email that belongs to **somebody else** is refused (`409`) - and
  the refusal names them, so the office knows who to ring instead;
* a family's second child finds the guardian already on file and only adds a **link**;
* the login is the guardian's email, created once and reused for every child;
* removing a guardian removes the **link**, never the person: their login, their number
  and their other children stay exactly as they were.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core import contacts
from app.core.security import generate_temp_password, get_password_hash
from app.core.text import canonical_phone
from app.domains.auth.roles import set_user_roles
from app.domains.admin.users import repository as user_repository
from app.domains.admin.users.models import User

from .models import Guardian, Student, StudentGuardianRelationship
from .schemas import GuardianLinkRead, GuardianRemoveResult, GuardianWrite


def _student_or_404(session: Session, student_id: UUID) -> Student:
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _find_guardian(
    session: Session, *, email: str | None, phone: str | None
) -> Guardian | None:
    """The guardian already on file for this contact, if it is really them.

    The **email** identifies the person - it is the address they sign in with - so it is
    tried first and wins outright: a sibling's form carries the same one.

    A **number on its own** also identifies a guardian (the card may carry no email). But
    a form that gives an email nobody has *and* a number somebody else holds is a
    mistyped record, not a person: returning `None` there lets
    `require_contact_free` refuse it and name the family that holds the number, instead
    of quietly handing that family a second login.
    """
    if email:
        guardian = session.exec(select(Guardian).where(Guardian.email == email)).first()
        return guardian
    if phone:
        return session.exec(
            select(Guardian).where(
                (Guardian.phone == phone) | (Guardian.alternate_phone == phone)
            )
        ).first()
    return None


def _login_email_of(session: Session, guardian: Guardian) -> str | None:
    if guardian.user_id is None:
        return None
    user = session.get(User, guardian.user_id)
    return user.email if user else None


def _link_read(
    session: Session,
    link: StudentGuardianRelationship,
    guardian: Guardian,
    *,
    password: str | None = None,
) -> GuardianLinkRead:
    return GuardianLinkRead(
        linkId=link.id,
        guardianId=guardian.id,
        name=guardian.name,
        relation=link.relationship_type,
        isPrimary=link.is_primary,
        phone=guardian.phone,
        email=guardian.email,
        alternatePhone=guardian.alternate_phone,
        occupation=guardian.occupation,
        address=guardian.address,
        loginEmail=_login_email_of(session, guardian),
        password=password,
    )


def list_guardians(session: Session, student_id: UUID) -> list[GuardianLinkRead]:
    """Every guardian of one student, the primary one first."""
    _student_or_404(session, student_id)
    rows = session.exec(
        select(StudentGuardianRelationship, Guardian)
        .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
        .where(StudentGuardianRelationship.student_id == student_id)
        .order_by(
            StudentGuardianRelationship.is_primary.desc(), Guardian.created_at
        )
    ).all()
    return [_link_read(session, link, guardian) for link, guardian in rows]


def _links_of(session: Session, student_id: UUID) -> list[StudentGuardianRelationship]:
    return list(
        session.exec(
            select(StudentGuardianRelationship)
            .where(StudentGuardianRelationship.student_id == student_id)
            .order_by(StudentGuardianRelationship.is_primary.desc())
        ).all()
    )


def add_guardian(
    session: Session, student_id: UUID, payload: GuardianWrite
) -> GuardianLinkRead:
    """Add a guardian to a student - or link one the school already has.

    A contact that matches a guardian on file **is** that person: the office is adding
    a family's second child, so only the link is written and their login is reused. A
    contact that belongs to somebody else is refused, naming them.
    """
    student = _student_or_404(session, student_id)
    email = (payload.email or "").strip().lower() or None
    phone = canonical_phone(payload.phone) or ""

    guardian = _find_guardian(session, email=email, phone=phone)
    password: str | None = None

    if guardian is None:
        # Nobody by that contact: it has to be free before a person is created for it.
        contacts.require_contact_free(
            session,
            who="The guardian",
            phone=phone,
            email=email,
            allow_student_id=student.id,
        )
        guardian = Guardian(
            name=payload.name,
            phone=phone,
            email=email,
            alternate_phone=canonical_phone(payload.alternate_phone),
            occupation=payload.occupation or None,
            address=payload.address or None,
        )
        session.add(guardian)
        session.commit()
        session.refresh(guardian)
    elif payload.name and guardian.name != payload.name:
        guardian.name = payload.name
        session.add(guardian)
        session.commit()
        session.refresh(guardian)

    # Their login: the email is the address they sign in with, created once.
    if (
        email
        and guardian.user_id is None
        and user_repository.get_user_by_email(session, email=email) is None
    ):
        password = generate_temp_password()
        account = User(
            email=email,
            full_name=guardian.name,
            hashed_password=get_password_hash(password),
            is_active=True,
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        set_user_roles(session, account, ["guardian"])
        guardian.user_id = account.id
        session.add(guardian)
        session.commit()
        session.refresh(guardian)

    links = _links_of(session, student.id)
    # The first guardian of a student is the primary one, whether or not the card says
    # so: the school has to know who it rings first.
    primary = bool(payload.is_primary) or not links
    if primary:
        for other in links:
            if other.is_primary:
                other.is_primary = False
                session.add(other)
        session.commit()

    link = next((row for row in links if row.guardian_id == guardian.id), None)
    if link is None:
        link = StudentGuardianRelationship(
            student_id=student.id,
            guardian_id=guardian.id,
            relationship_type=payload.relation or "guardian",
            is_primary=primary,
        )
        session.add(link)
    else:
        link.relationship_type = payload.relation or link.relationship_type
        link.is_primary = primary
        session.add(link)
    session.commit()
    session.refresh(link)
    return _link_read(session, link, guardian, password=password)


def update_guardian(
    session: Session,
    student_id: UUID,
    guardian_id: UUID,
    payload: GuardianWrite,
) -> GuardianLinkRead:
    """Edit a guardian: the person (name, contact, address) **and** this child's link.

    The contact moves every record of that person together (`contacts.sync_contact`), so
    the login, the guardian row and - when they also work here - the staff row never
    disagree about how to reach them. Somebody else's contact is refused, never taken.
    """
    student = _student_or_404(session, student_id)
    guardian = session.get(Guardian, guardian_id)
    link = session.exec(
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.student_id == student.id,
            StudentGuardianRelationship.guardian_id == guardian_id,
        )
    ).first()
    if guardian is None or link is None:
        raise HTTPException(status_code=404, detail="This student has no such guardian")

    email = (payload.email or "").strip().lower() or None
    phone = canonical_phone(payload.phone) or ""
    # The same person keeps their own contact; a value somebody else holds is refused.
    contacts.require_contact_free(
        session,
        who="The guardian",
        phone=phone,
        email=email,
        allow_user_id=guardian.user_id,
        allow_guardian_id=guardian.id,
    )

    contacts.sync_contact(
        session, guardian_id=guardian.id, email=email, phone=phone
    )
    session.refresh(guardian)
    if payload.name:
        guardian.name = payload.name
    guardian.alternate_phone = canonical_phone(payload.alternate_phone)
    guardian.occupation = payload.occupation or None
    guardian.address = payload.address or None
    session.add(guardian)

    if payload.is_primary and not link.is_primary:
        for other in _links_of(session, student.id):
            other.is_primary = other.guardian_id == guardian.id
            session.add(other)
    link.relationship_type = payload.relation or link.relationship_type
    session.add(link)
    session.commit()
    session.refresh(link)
    session.refresh(guardian)
    return _link_read(session, link, guardian)


def remove_guardian(
    session: Session, student_id: UUID, guardian_id: UUID
) -> GuardianRemoveResult:
    """Unlink a guardian from this student. The **person** stays.

    Their login, their number and their other children keep working - only this child's
    link goes. If they were the primary contact, the guardian left on file takes over,
    because a student always has somebody to ring.
    """
    student = _student_or_404(session, student_id)
    link = session.exec(
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.student_id == student.id,
            StudentGuardianRelationship.guardian_id == guardian_id,
        )
    ).first()
    if link is None:
        raise HTTPException(status_code=404, detail="This student has no such guardian")

    was_primary = link.is_primary
    session.delete(link)
    session.commit()

    remaining = _links_of(session, student.id)
    promoted: str | None = None
    if was_primary and remaining:
        keeper = remaining[0]
        keeper.is_primary = True
        session.add(keeper)
        session.commit()
        keeper_guardian = session.get(Guardian, keeper.guardian_id)
        promoted = keeper_guardian.name if keeper_guardian else None

    # Is this person still somebody's guardian here?
    still_linked = session.exec(
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.guardian_id == guardian_id
        )
    ).first()
    return GuardianRemoveResult(
        removed=True,
        guardianId=guardian_id,
        personKept=still_linked is None,
        primaryMovedTo=promoted,
    )


