"""One contact, one person - the rule every form that captures a phone or an email obeys.

Why this lives in one place
---------------------------
A phone number and an email address are how the school reaches somebody, so the same
one cannot belong to two people: a second row with the same number means the office
cannot tell who it is ringing, and a login that duplicates an address is two accounts
for one person. Before, each form checked whatever it happened to know about
(`admissions/service.py` looked at logins, `staff/service.py` at employees), so a
guardian could be entered again by the hire form and nobody noticed.

The **database** holds the per-table half of the rule (unique indexes per school on
`user.email`, `guardian.phone`/`email`/`alternate_phone`, `employee.phone`/`email`,
`student.admission_number`/`student_email`). This module holds the
half a database cannot express: **across** tables, the same contact may appear only
when it is the *same person*.

The matrix
----------
    contact found on ...   | another person asks for it        | the same person asks
    -----------------------|-----------------------------------|-------------------
    a login (user)         | refused, naming the login          | allowed
    a guardian             | refused, naming the guardian       | allowed
    a member of staff      | refused, naming them               | allowed
    a candidate            | refused (they may be hired later)  | n/a (no login yet)
    a student's own email  | refused - a student is not a login | allowed via their login

"Same person" means the row carries the same `user_id` (a teacher whose child studies
here is one person with a staff record, a guardian record *and* one login), which is
why `allow_user_id` exists.

What a caller gets
------------------
* `find_contact`      - who already holds this phone/email, or `None`.
* `require_contact_free` - raise `409` unless the contact is free (or theirs).
* `contact_read`      - the payload behind the form's "we already have this person"
  popup: their name, their roles, their children, and the sentence to show.
* `sync_contact`      - after an edit, move every record of that person together, so
  their login, guardian row and staff row can never disagree again.
"""

from dataclasses import dataclass, field
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.text import canonical_phone
from app.domains.auth.roles import role_codenames
from app.domains.admin.users.models import User

#: What a contact already belongs to.
KIND_LOGIN = "login"
KIND_GUARDIAN = "guardian"
KIND_EMPLOYEE = "employee"
KIND_STUDENT = "student"
KIND_CANDIDATE = "candidate"

#: The wording the office sees for each kind, used in the refusal and the popup.
LABELS = {
    KIND_LOGIN: "a login",
    KIND_GUARDIAN: "a guardian",
    KIND_EMPLOYEE: "a member of staff",
    KIND_STUDENT: "a student",
    KIND_CANDIDATE: "a candidate in the hiring pipeline",
}

#: The order the tables are searched in. A login first (it is the strongest claim: an
#: account already signs in with that address), then the people tables.
SEARCH_ORDER = (KIND_LOGIN, KIND_GUARDIAN, KIND_EMPLOYEE, KIND_STUDENT, KIND_CANDIDATE)


@dataclass
class ContactHolder:
    """Who a phone number or an email already belongs to.

    `matched` says which of the two was found, because a form asking about both needs
    to name the field that clashed ("this number already belongs to ...").
    """

    kind: str
    name: str
    matched: str = ""
    value: str = ""
    user_id: UUID | None = None
    guardian_id: UUID | None = None
    employee_id: UUID | None = None
    student_id: UUID | None = None
    candidate_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    roles: list[str] = field(default_factory=list)
    #: The children of a guardian: [{"id", "name", "admissionNumber"}].
    children: list[dict] = field(default_factory=list)

    @property
    def label(self) -> str:
        return LABELS.get(self.kind, "somebody")

    def describe(self) -> str:
        """The sentence an office reads: who holds it, and what that means."""
        who = f"{self.name} ({self.label})"
        if self.roles:
            who = f"{self.name} ({', '.join(self.roles)})"
        if self.matched == "email":
            sentence = f"The email '{self.value}' already belongs to {who}."
        elif self.matched == "phone":
            sentence = f"The phone number '{self.value}' already belongs to {who}."
        else:
            sentence = f"{self.name} ({self.label}) is already on file."
        if self.children:
            listed = ", ".join(
                child["name"] + (f" ({child['admissionNumber']})" if child["admissionNumber"] else "")
                for child in self.children
                if child.get("name")
            )
            if listed:
                sentence += f" Their children here: {listed}."
        return sentence


# ---------------------------------------------------------------------------
# Who holds what
# ---------------------------------------------------------------------------


def _children_of(session: Session, guardian_id: UUID) -> list[dict]:
    """Every child this guardian is linked to, oldest form first."""
    from app.domains.academic.classroom.students.models import Student, StudentGuardianRelationship

    rows = session.exec(
        select(Student)
        .join(
            StudentGuardianRelationship,
            StudentGuardianRelationship.student_id == Student.id,
        )
        .where(StudentGuardianRelationship.guardian_id == guardian_id)
        .order_by(Student.created_on)
    ).all()
    return [
        {
            "id": str(row.id),
            "name": row.full_name or row.student_first_name or "",
            "admissionNumber": row.admission_number or "",
        }
        for row in rows
    ]


def _login_by_email(session: Session, *, phone: str | None, email: str | None):
    if not email:
        return None
    user = session.exec(select(User).where(func.lower(User.email) == email)).first()
    if user is None:
        return None
    return ContactHolder(
        kind=KIND_LOGIN,
        name=user.full_name or user.email,
        matched="email",
        value=user.email,
        user_id=user.id,
        email=user.email,
        roles=role_codenames(session, user.id),
    )


def _guardian_by_contact(session: Session, *, phone: str | None, email: str | None):
    from app.domains.academic.classroom.students.models import Guardian

    if not phone and not email:
        return None
    conditions = []
    if phone:
        conditions.append(
            or_(Guardian.phone == phone, Guardian.alternate_phone == phone)
        )
    if email:
        conditions.append(func.lower(Guardian.email) == email)
    guardian = session.exec(select(Guardian).where(or_(*conditions))).first()
    if guardian is None:
        return None

    matched_phone = bool(phone) and phone in (guardian.phone, guardian.alternate_phone)
    return ContactHolder(
        kind=KIND_GUARDIAN,
        name=guardian.name,
        matched="phone" if matched_phone else "email",
        value=phone if matched_phone else (guardian.email or email or ""),
        user_id=guardian.user_id,
        guardian_id=guardian.id,
        email=guardian.email,
        phone=guardian.phone,
        roles=role_codenames(session, guardian.user_id) if guardian.user_id else [],
        children=_children_of(session, guardian.id),
    )


def _employee_by_contact(session: Session, *, phone: str | None, email: str | None):
    from app.domains.people.staff.models import Employee

    if not phone and not email:
        return None
    conditions = []
    if phone:
        conditions.append(Employee.phone == phone)
    if email:
        conditions.append(func.lower(Employee.email) == email)
    employee = session.exec(select(Employee).where(or_(*conditions))).first()
    if employee is None:
        return None

    matched_phone = bool(phone) and employee.phone == phone
    user = session.get(User, employee.user_id) if employee.user_id else None
    return ContactHolder(
        kind=KIND_EMPLOYEE,
        name=(user.full_name if user else None) or employee.employee_code,
        matched="phone" if matched_phone else "email",
        value=phone if matched_phone else (employee.email or email or ""),
        user_id=employee.user_id,
        employee_id=employee.id,
        email=employee.email,
        phone=employee.phone,
        roles=role_codenames(session, employee.user_id) if employee.user_id else [],
    )


def _student_by_contact(session: Session, *, phone: str | None, email: str | None):
    """A student's **own** email. Students have no phone of their own in this schema."""
    from app.domains.academic.classroom.students.models import Student

    if not email:
        return None
    student = session.exec(
        select(Student).where(func.lower(Student.student_email) == email)
    ).first()
    if student is None:
        return None
    return ContactHolder(
        kind=KIND_STUDENT,
        name=student.full_name or student.student_first_name or "a student",
        matched="email",
        value=student.student_email or email,
        user_id=student.user_id,
        student_id=student.id,
        email=student.student_email,
        roles=role_codenames(session, student.user_id) if student.user_id else [],
    )


def _candidate_by_contact(session: Session, *, phone: str | None, email: str | None):
    """Somebody still in the hiring pipeline - they may be hired later."""
    try:
        from app.domains.operations.staff_hiring.models import HiringCandidate
    except Exception:  # pragma: no cover - the domain is always present
        return None

    if not phone and not email:
        return None
    conditions = []
    if phone:
        conditions.append(HiringCandidate.phone == phone)
    if email:
        conditions.append(func.lower(HiringCandidate.email) == email)
    candidate = session.exec(select(HiringCandidate).where(or_(*conditions))).first()
    if candidate is None:
        return None

    matched_phone = bool(phone) and candidate.phone == phone
    return ContactHolder(
        kind=KIND_CANDIDATE,
        name=candidate.candidate_name,
        matched="phone" if matched_phone else "email",
        value=phone if matched_phone else (candidate.email or email or ""),
        candidate_id=candidate.id,
        email=candidate.email,
        phone=candidate.phone,
    )


#: One finder per kind, in the order `find_contact` walks them.
_FINDERS = {
    KIND_LOGIN: _login_by_email,
    KIND_GUARDIAN: _guardian_by_contact,
    KIND_EMPLOYEE: _employee_by_contact,
    KIND_STUDENT: _student_by_contact,
    KIND_CANDIDATE: _candidate_by_contact,
}


def find_contact(
    session: Session, *, phone: str | None = None, email: str | None = None
) -> ContactHolder | None:
    """Who already holds this phone number or email - or `None` when nobody does.

    Both values are normalised first (a number to its ten digits, an address to
    lower-case), because that is how they are stored: `+91 98765 43210` and
    `9876543210` are the **same** number and must find the same guardian.
    """
    phone = canonical_phone(phone)
    email = (email or "").strip().lower() or None
    if not phone and not email:
        return None
    for kind in SEARCH_ORDER:
        holder = _FINDERS[kind](session, phone=phone, email=email)
        if holder is not None:
            return holder
    return None


def allow_ids_for_user(session: Session, user_id: UUID | None) -> dict:
    """The `allow_*` ids of a person who is **already** on file.

    Every form that names a contact hits the same question: "is this somebody we
    already have, or somebody else?". A person who is already here holds their own
    contact, so their records are passed along as allowed - a teacher who is also a
    parent fills the hire form with the number their guardian row already carries, and
    that is not a clash. Somebody **else's** contact still is.
    """
    from app.domains.people.staff.models import Employee
    from app.domains.academic.classroom.students.models import Guardian

    if user_id is None:
        return {"allow_user_id": None, "allow_guardian_id": None, "allow_employee_id": None}
    guardian = session.exec(select(Guardian).where(Guardian.user_id == user_id)).first()
    employee = session.exec(select(Employee).where(Employee.user_id == user_id)).first()
    return {
        "allow_user_id": user_id,
        "allow_guardian_id": guardian.id if guardian is not None else None,
        "allow_employee_id": employee.id if employee is not None else None,
    }


def _same_person(
    holder: ContactHolder,
    *,
    allow_user_id: UUID | None = None,
    allow_guardian_id: UUID | None = None,
    allow_employee_id: UUID | None = None,
    allow_student_id: UUID | None = None,
) -> bool:
    """True when the holder is the very person the caller is editing."""
    return any(
        [
            allow_user_id is not None and holder.user_id == allow_user_id,
            allow_guardian_id is not None and holder.guardian_id == allow_guardian_id,
            allow_employee_id is not None and holder.employee_id == allow_employee_id,
            allow_student_id is not None and holder.student_id == allow_student_id,
        ]
    )


def conflicts(
    session: Session,
    *,
    phone: str | None = None,
    email: str | None = None,
    allow_user_id: UUID | None = None,
    allow_guardian_id: UUID | None = None,
    allow_employee_id: UUID | None = None,
    allow_student_id: UUID | None = None,
) -> list[ContactHolder]:
    """Every held contact among `phone` / `email` that is **not** this same person.

    Both fields are checked, because a form usually carries the pair and the clash
    can be on either one.
    """
    found: list[ContactHolder] = []
    for holder in (
        find_contact(session, phone=phone) if phone else None,
        find_contact(session, email=email) if email else None,
    ):
        if holder is None:
            continue
        if _same_person(
            holder,
            allow_user_id=allow_user_id,
            allow_guardian_id=allow_guardian_id,
            allow_employee_id=allow_employee_id,
            allow_student_id=allow_student_id,
        ):
            continue
        if holder not in found:
            found.append(holder)
    return found


def require_contact_free(
    session: Session,
    *,
    who: str,
    phone: str | None = None,
    email: str | None = None,
    allow_user_id: UUID | None = None,
    allow_guardian_id: UUID | None = None,
    allow_employee_id: UUID | None = None,
    allow_student_id: UUID | None = None,
) -> None:
    """Refuse a contact another person already holds (`409`).

    Every form that captures a contact calls this **before** it writes anything, so
    the office is told "this number belongs to Rakesh" instead of getting a database
    error - or, worse, quietly creating a second person for the same parent.

    `allow_*_id` carries the record being edited: a teacher who is also a guardian
    keeps their own number, because the contact and the person are the same.
    """
    found = conflicts(
        session,
        phone=phone,
        email=email,
        allow_user_id=allow_user_id,
        allow_guardian_id=allow_guardian_id,
        allow_employee_id=allow_employee_id,
        allow_student_id=allow_student_id,
    )
    if not found:
        return
    raise HTTPException(
        status_code=409,
        detail=" ".join(holder.describe() for holder in found)
        + f" {who} cannot use it as well - edit that record, or use a different"
        " contact.",
    )


def contact_read(
    session: Session, *, phone: str | None = None, email: str | None = None
) -> dict:
    """The payload behind the form's "we already have this person" popup.

    The frontend shows the sentence, offers to fill the guardian block in, and names
    the children already linked - which is what makes a family's second child one
    guardian instead of two.
    """
    holder = find_contact(session, phone=phone, email=email)
    if holder is None:
        return {
            "found": False,
            "kind": None,
            "name": None,
            "email": None,
            "phone": None,
            "userId": None,
            "guardianId": None,
            "employeeId": None,
            "studentId": None,
            "roles": [],
            "children": [],
            "message": "Nobody on file uses this contact yet.",
        }

    # The match found the person's login first (an email lookup lands there), but they
    # may also be a guardian on file. One contact = one person: the popup shows the same
    # thing whichever key the form typed, so the family side of them is completed here.
    guardian_id = holder.guardian_id
    children = holder.children
    if guardian_id is None and holder.user_id is not None:
        from app.domains.academic.classroom.students.models import Guardian

        guardian = session.exec(
            select(Guardian).where(Guardian.user_id == holder.user_id)
        ).first()
        if guardian is not None:
            guardian_id = guardian.id
            children = _children_of(session, guardian.id)

    return {
        "found": True,
        "kind": holder.kind,
        "name": holder.name,
        "email": holder.email,
        "phone": holder.phone,
        "userId": str(holder.user_id) if holder.user_id else None,
        "guardianId": str(guardian_id) if guardian_id else None,
        "employeeId": str(holder.employee_id) if holder.employee_id else None,
        "studentId": str(holder.student_id) if holder.student_id else None,
        "roles": holder.roles,
        "children": children,
        "message": holder.describe()
        + " Their details can be filled in, and the new child linked to them.",
    }


def sync_contact(
    session: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    user_id: UUID | None = None,
    guardian_id: UUID | None = None,
    employee_id: UUID | None = None,
) -> list[str]:
    """Move every record of **one person** to the contact they were edited with.

    A person stays one person even when the product keeps them in three shapes - a
    login, a guardian row, a staff row - so an edit that touches only one of them
    leaves the others stale: the office rings the old number, or the parent cannot
    sign in with the address the form shows. This walks the person (finding the other
    rows from the `user_id` it was given) and moves them together, reporting what
    moved.

    A value another person already holds is **never taken over**: the note says what
    was left alone instead, which is the same promise `require_contact_free` makes.
    Never call it for a contact that was refused: fix the form instead.
    """
    from app.domains.people.staff.models import Employee
    from app.domains.academic.classroom.students.models import Guardian

    email = (email or "").strip().lower() or None
    phone = canonical_phone(phone)
    notes: list[str] = []

    # --- every row of this person -------------------------------------------
    guardian = session.get(Guardian, guardian_id) if guardian_id else None
    employee = session.get(Employee, employee_id) if employee_id else None
    user = session.get(User, user_id) if user_id else None
    if user is None:
        linked = guardian.user_id if guardian is not None else None
        if linked is None and employee is not None:
            linked = employee.user_id
        user = session.get(User, linked) if linked else None
    if guardian is None and user is not None:
        guardian = session.exec(
            select(Guardian).where(Guardian.user_id == user.id)
        ).first()
    if employee is None and user is not None:
        employee = session.exec(
            select(Employee).where(Employee.user_id == user.id)
        ).first()

    def other_people() -> list:
        """Contacts among this pair that belong to somebody else."""
        return conflicts(
            session,
            phone=phone,
            email=email,
            allow_user_id=user.id if user is not None else None,
            allow_guardian_id=guardian.id if guardian is not None else None,
            allow_employee_id=employee.id if employee is not None else None,
        )

    busy = other_people()
    busy_emails = {holder.value for holder in busy if holder.matched == "email"}
    busy_phones = {holder.value for holder in busy if holder.matched == "phone"}

    # --- the login: the email **is** the address they sign in with ----------
    if user is not None and email and user.email != email:
        if email in busy_emails:
            notes.append(
                f"'{email}' already belongs to another person, so the login is still "
                f"'{user.email}'."
            )
        else:
            previous = user.email
            user.email = email
            session.add(user)
            notes.append(f"The login changed from '{previous}' to '{email}'.")

    # --- the guardian row ---------------------------------------------------
    if guardian is not None:
        if email and (guardian.email or None) != email:
            if email in busy_emails:
                notes.append(
                    f"'{email}' already belongs to another person, so the guardian's "
                    f"email is still '{guardian.email}'."
                )
            else:
                previous = guardian.email
                guardian.email = email
                session.add(guardian)
                notes.append(
                    f"The guardian email changed from '{previous or '-'}' to '{email}'."
                )
        if phone and guardian.phone != phone:
            if phone in busy_phones:
                notes.append(
                    f"'{phone}' already belongs to another person, so the guardian's "
                    f"number is still '{guardian.phone}'."
                )
            else:
                previous = guardian.phone
                guardian.phone = phone
                session.add(guardian)
                notes.append(
                    f"The guardian's number changed from '{previous}' to '{phone}'."
                )

    # --- the staff row ------------------------------------------------------
    if employee is not None:
        if email and (employee.email or None) != email:
            if email in busy_emails:
                notes.append(
                    f"'{email}' already belongs to another person, so the staff email "
                    f"is still '{employee.email}'."
                )
            else:
                employee.email = email
                session.add(employee)
                notes.append(f"The staff email is now '{email}'.")
        if phone and employee.phone != phone:
            if phone in busy_phones:
                notes.append(
                    f"'{phone}' already belongs to another person, so the staff number "
                    f"is still '{employee.phone}'."
                )
            else:
                employee.phone = phone
                session.add(employee)
                notes.append(f"The staff number is now '{phone}'.")

    if notes:
        session.commit()
    return notes


# ---------------------------------------------------------------------------
# The popup payload, as the API hands it over
#
# The shape lives here because this module owns the rule: every form that captures a
# contact shows the same popup, so there is one schema rather than a copy per domain.
# ---------------------------------------------------------------------------


class ContactChildRead(BaseModel):
    """A child already linked to the person a contact belongs to."""

    id: str
    name: str
    admissionNumber: str = ""


class ContactLookupRead(BaseModel):
    """Who a phone number or an email already belongs to, for the form's popup.

    `found` false means nobody on file uses that contact. Otherwise: the person, the
    roles they hold (a teacher who is also a parent), the children already linked to
    them, and the sentence to display.
    """

    found: bool
    kind: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    userId: str | None = None
    guardianId: str | None = None
    employeeId: str | None = None
    studentId: str | None = None
    roles: list[str] = []
    children: list[ContactChildRead] = []
    message: str = ""





