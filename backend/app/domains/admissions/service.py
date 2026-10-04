"""Admission service - the Operations > Admission workflow.

Reads and writes `admissionapplication`. Four things here are more than plain
CRUD:

* `application_no` is minted server-side (`ADM-2026-0141`) so two open forms in
  two browsers can never claim the same number.
* A row is either a **draft** (half-filled, still editable) or **registered**.
* **Registering promotes the application into real records** (see
  `_promote`): a student login, a `studentprofile` row the directory lists, a
  guardian login, and the link between the two. That is what makes "Registered"
  and "listed under Students" the same thing - before, the application was
  stamped and the student never appeared.
* A **separation** records why and when a registered student left. The row is
  then reported as Inactive - derived from the separation block itself rather
  than stored as a second flag that could disagree with it.

Logins are generated (`stu.<name>.<class-section>`, `gau.<name>.p1`) and their
first-time password is returned exactly once, on the response that created them.
The public `POST /admissions/apply` form still only *stores* an application: it
never creates accounts, because promotion runs from the office screens.
"""

import re
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.security import generate_temp_password, get_password_hash
from app.domains.academics.models import Classroom
from app.domains.academics.repository import find_classroom, get_section
from app.domains.auth.models import Role, UserRole, utcnow
from app.domains.auth.roles import set_user_roles
from app.domains.students.models import StudentParentRelationship, StudentProfile
from app.domains.users.models import User

from . import repository
from .models import STATUS_REGISTERED, AdmissionApplication
from .schemas import (
    AdmissionApplicationCreate,
    AdmissionApplicationRead,
    AdmissionApplicationUpdate,
    AdmissionStatusUpdate,
    LoginCredential,
    PasswordResetRead,
    SeparationRecordWrite,
)

#: School logins are generated, never typed: `stu.<name>.<class-section>` for a
#: student and `gau.<name>.p1` for a guardian, on the school's own domain.
STUDENT_EMAIL_PREFIX = "stu"
GUARDIAN_EMAIL_PREFIX = "gau"
SCHOOL_EMAIL_DOMAIN = "educonnect.com"

# Fields the server owns: a full-row update must never blank them out (neither
# with `null` nor with an empty string).
_SERVER_MANAGED = ("application_no", "created_on")


def _read(
    application: AdmissionApplication, emails: dict[int, str] | None = None
) -> AdmissionApplicationRead:
    """ORM row -> response model, folding the four separation columns together."""
    lookup = emails or {}
    read = AdmissionApplicationRead.model_validate(
        {
            **application.model_dump(),
            "separation": application.separation,
            "student_login_email": (
                lookup.get(application.student_user_id)
                if application.student_user_id
                else None
            ),
            "guardian_login_email": (
                lookup.get(application.guardian_user_id)
                if application.guardian_user_id
                else None
            ),
        }
    )
    return read


def _login_emails(session: Session) -> dict[int, str]:
    """{user_id: email} - so a list of applications can show the logins it made."""
    return {
        int(user.id): user.email for user in session.exec(select(User)).all() if user.id
    }


def _get_or_404(session: Session, application_id: int) -> AdmissionApplication:
    application = repository.get_application_by_id(session, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def get_applications(
    session: Session, status: str | None = None, skip: int = 0, limit: int = 500
) -> list[AdmissionApplicationRead]:
    emails = _login_emails(session)
    return [
        _read(row, emails)
        for row in repository.get_applications(session, status, skip, limit)
    ]


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplicationRead:
    if not application_in.application_no:
        application_in.application_no = repository.next_application_no(session)
    application = repository.create_application(session, application_in)
    # A form saved straight as Registered is promoted here, exactly like the
    # "Register" button on an existing row.
    return _read_registered(session, application)


def update_application(
    session: Session,
    application_id: int,
    application_in: AdmissionApplicationUpdate,
) -> AdmissionApplicationRead:
    application = _get_or_404(session, application_id)
    for field, value in application_in.model_dump(exclude_unset=True).items():
        if field in _SERVER_MANAGED and not value:
            continue
        setattr(application, field, value)
    application = repository.save_application(session, application)
    return _read_registered(session, application)


def record_separation(
    session: Session,
    application_id: int,
    separation_in: SeparationRecordWrite,
) -> AdmissionApplicationRead:
    application = _get_or_404(session, application_id)
    application.separation_reason = separation_in.reason
    application.separation_session = separation_in.session
    application.separation_date = separation_in.date
    if separation_in.dropped_class:
        application.separation_dropped_class = separation_in.dropped_class
    return _read(repository.save_application(session, application))


def update_application_status(
    session: Session,
    application_id: int,
    status_update: AdmissionStatusUpdate,
) -> AdmissionApplicationRead:
    """Move a row between Draft and Registered (the Register button's endpoint).

    Registering promotes the application - student + guardian records and their
    logins are created once - and the response carries those logins so the office
    can hand them over.
    """
    application = _get_or_404(session, application_id)
    application.status = status_update.status
    if status_update.notes:
        application.notes = status_update.notes
    application = repository.save_application(session, application)
    return _read_registered(session, application)


def is_registered(application: AdmissionApplication) -> bool:
    return application.status == STATUS_REGISTERED


# ---------------------------------------------------------------------------
# Promotion - an application becoming a real student
#
# The form is a *request*; `studentprofile` is the student. Registering is the
# single moment the two meet, and it happens here so the school can never again
# hold a "registered" applicant who is missing from the directory.
# ---------------------------------------------------------------------------


def _slug(value: str | None, fallback: str = "") -> str:
    """`"Homer Simpson"` -> `"homer.simpson"` (email-safe)."""
    cleaned = re.sub(r"[^a-z0-9]+", ".", (value or "").strip().lower())
    return cleaned.strip(".") or fallback


def _letters(value: str | None) -> str:
    """Keep only letters/digits: `"Class 6"` -> `"class6"`, `"A"` -> `"a"`."""
    return "".join(re.findall(r"[a-z0-9]", (value or "").strip().lower()))


def _student_name(application: AdmissionApplication) -> str:
    parts = (
        application.student_first_name,
        application.student_middle_name,
        application.student_last_name,
    )
    name = " ".join(part.strip() for part in parts if part and part.strip())
    return name or "Student"


def _class_token(application: AdmissionApplication, classroom: Classroom | None) -> str:
    """`"Class 6"` + section `"A"` -> `"6a"`; `"Nursery"` -> `"nursery"`.

    Only the parts that were actually filled are used - an empty section must
    never turn "UKG" into "ukguser".
    """
    section = _letters(application.applied_section_preference)
    source = (
        classroom.name if classroom is not None else application.applied_for_class_level
    )
    digits = "".join(char for char in (source or "") if char.isdigit())
    token = digits or _letters(source)
    return f"{token}{section}" if token else (section or "x")


def _free_student_email(session: Session, local_part: str) -> str:
    """`local@domain`, with `.2`, `.3` appended until the address is unused."""
    candidate = f"{local_part}@{SCHOOL_EMAIL_DOMAIN}"
    suffix = 1
    while session.exec(select(User).where(User.email == candidate)).first():
        suffix += 1
        candidate = f"{local_part}.{suffix}@{SCHOOL_EMAIL_DOMAIN}"
    return candidate


def _free_guardian_email(session: Session, name_slug: str) -> str:
    """`gau.<name>.p1@`, then `.p2`, `.p3` - two parents of the same name."""
    index = 1
    while True:
        candidate = (
            f"{GUARDIAN_EMAIL_PREFIX}.{name_slug}.p{index}@{SCHOOL_EMAIL_DOMAIN}"
        )
        if not session.exec(select(User).where(User.email == candidate)).first():
            return candidate
        index += 1


def _find_guardian_by_contact(
    session: Session, contact_email: str | None
) -> User | None:
    """The guardian login already on file for this real-world email, if any.

    This is what makes a parent's **second** child share one login: the form
    carries the same contact email, so the existing account is reused and only
    the parent-child link is added.
    """
    if not contact_email or not contact_email.strip():
        return None
    return session.exec(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.codename == "guardian",
            func.lower(User.contact_email) == contact_email.strip().lower(),
        )
    ).first()


def _guardian_block(application: AdmissionApplication) -> tuple[str, str | None, str]:
    """(name, contact email, relationship) from whichever block was filled."""
    if application.guardian_name or application.guardian_email:
        return (
            application.guardian_name or "",
            application.guardian_email,
            application.guardian_relation or "Guardian",
        )
    if application.father_name or application.father_email:
        return (
            application.father_name or "",
            application.father_email,
            "Father",
        )
    if application.mother_name or application.mother_email:
        return (
            application.mother_name or "",
            application.mother_email,
            "Mother",
        )
    return ("", None, "Guardian")


def _promote(
    session: Session, application: AdmissionApplication
) -> tuple[list[LoginCredential], str | None]:
    """Create the student (and the guardian) for a Registered application.

    Idempotent: an application that already carries `student_id` is left alone,
    so pressing Register twice can never make two students from one form. Returns
    the logins it created (each with its one-time password) and an optional note
    about anything the office should look at.
    """
    if application.student_id:
        return [], None

    classroom = find_classroom(session, application.applied_for_class_level)
    section = (
        get_section(session, classroom.id, application.applied_section_preference)
        if classroom is not None and classroom.id is not None
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
    if application.date_of_birth is None:
        notes.append(
            "Date of birth was not on the form; today's date was stored instead."
        )

    credentials: list[LoginCredential] = []

    # --- 1. the student: one login + the profile the directory lists ---------
    student_name = _student_name(application)
    student_email = _free_student_email(
        session,
        f"{STUDENT_EMAIL_PREFIX}.{_slug(student_name)}."
        f"{_class_token(application, classroom)}",
    )
    student_password = generate_temp_password()
    student_user = User(
        email=student_email,
        full_name=student_name,
        hashed_password=get_password_hash(student_password),
        is_active=True,
    )
    session.add(student_user)
    session.commit()
    session.refresh(student_user)
    set_user_roles(session, student_user, ["student"])

    guardian_name, guardian_contact, relationship = _guardian_block(application)
    student = StudentProfile(
        user_id=student_user.id,
        # The form number becomes the admission number: one number, traceable
        # back to the application it came from.
        admission_number=application.application_no,
        date_of_birth=application.date_of_birth or date.today(),
        guardian_name=guardian_name,
        gender=application.gender or None,
        classroom_id=classroom.id if classroom else None,
        section_id=section.id if section else None,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    credentials.append(
        LoginCredential(
            role="student",
            full_name=student_name,
            email=student_email,
            password=student_password,
        )
    )

    # --- 2. the guardian: one login per parent, shared by all their children -
    guardian = _find_guardian_by_contact(session, guardian_contact)
    guardian_password: str | None = None
    if guardian is None and guardian_name:
        guardian_password = generate_temp_password()
        guardian = User(
            email=_free_guardian_email(session, _slug(guardian_name)),
            full_name=guardian_name,
            hashed_password=get_password_hash(guardian_password),
            is_active=True,
            contact_email=guardian_contact or None,
        )
        session.add(guardian)
        session.commit()
        session.refresh(guardian)
        set_user_roles(session, guardian, ["guardian"])

    if guardian is not None:
        credentials.append(
            LoginCredential(
                role="guardian",
                full_name=guardian.full_name,
                email=guardian.email,
                password=guardian_password,
                created=guardian_password is not None,
            )
        )
        linked = session.exec(
            select(StudentParentRelationship).where(
                StudentParentRelationship.student_id == student.id,
                StudentParentRelationship.parent_user_id == guardian.id,
            )
        ).first()
        if linked is None:
            session.add(
                StudentParentRelationship(
                    student_id=student.id,
                    parent_user_id=guardian.id,
                    relationship_type=relationship,
                )
            )

    # --- 3. stamp the link, so the two screens can never disagree ------------
    application.student_id = student.id
    application.student_user_id = student_user.id
    application.guardian_user_id = guardian.id if guardian else None
    application.promoted_at = utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)

    return credentials, (" ".join(notes) or None)


def _read_registered(
    session: Session, application: AdmissionApplication
) -> AdmissionApplicationRead:
    """Read a row, promoting it first if it is Registered but has no student yet."""
    credentials: list[LoginCredential] = []
    note: str | None = None
    if application.status == STATUS_REGISTERED:
        credentials, note = _promote(session, application)
    read = _read(application, _login_emails(session))
    read.credentials = credentials or None
    read.placement_note = note
    return read


def register_application(
    session: Session, application_id: int
) -> AdmissionApplicationRead:
    """Register an application from the office screens.

    Creates the student + guardian records (once) and returns the logins with
    their first-time passwords, which the caller shows exactly once.
    """
    application = _get_or_404(session, application_id)
    application.status = STATUS_REGISTERED
    session.add(application)
    session.commit()
    session.refresh(application)
    return _read_registered(session, application)


def reset_login_password(
    session: Session, application_id: int, target: str
) -> PasswordResetRead:
    """Mint a new first-time password for the student or the guardian login."""
    if target not in ("student", "guardian"):
        raise HTTPException(
            status_code=422, detail="target must be 'student' or 'guardian'"
        )
    application = _get_or_404(session, application_id)
    user_id = (
        application.student_user_id
        if target == "student"
        else application.guardian_user_id
    )
    if user_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"This application has no {target} login yet - register it first.",
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
