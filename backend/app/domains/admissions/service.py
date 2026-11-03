"""Admission service - the Operations > Admission workflow.

Reads and writes `student_admission_form`. Four things here are more than plain
CRUD:

* `application_no` is minted server-side (`ADM-2026-0141`) so two open forms in
  two browsers can never claim the same number.
* A row is either a **draft** (half-filled, still editable) or **registered**.
* **Registering promotes the application into real records** (see
  `_promote`): a student login, a `studentprofile` row the directory lists, a
  guardian login, and the link between the two. That is what makes "Registered"
  and "listed under Students" the same thing - before, the application was
  stamped and the student never appeared. The **class-section** the form asked for
  is created when the school does not have it yet, so registering a student is
  what puts that classroom on the Classroom screen.
* A **separation** records why and when a registered student left. The row is
  then reported as Inactive - derived from the separation block itself rather
  than stored as a second flag that could disagree with it.

Logins are the email the family supplied on the form - the student's own email,
and the guardian's email or phone. Nothing is generated: a form with neither
leaves that person without a login, and the response says so in its notes. A
contact that is **edited later** moves the login with it (`_sync_logins`), so a
registered row and its account can never disagree. The first-time password is
returned exactly once, on the response that created it.
The public `POST /admissions/apply` form still only *stores* an application: it
never creates accounts, because promotion runs from the office screens.
"""

from datetime import date
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.security import generate_temp_password, get_password_hash
from app.domains.academics.models import ClassName, Section
from app.domains.academics.repository import ensure_room, find_classroom, find_section
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

#: A login is an email the family supplied, or their phone when the form gave no
#: email. Nothing is ever generated: a form with neither leaves that person without
#: a login (the office can add one later), because an address nobody owns can never
#: be signed in with - the family never sees mail sent to it.

# Fields the server owns: a full-row update must never blank them out (neither
# with `null` nor with an empty string).
_SERVER_MANAGED = ("application_no", "created_on")


def _read(
    application: AdmissionApplication, emails: dict[UUID, str] | None = None
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


def _login_emails(session: Session) -> dict[UUID, str]:
    """{user_id: email} - so a list of applications can show the logins it made."""
    return {
        user.id: user.email for user in session.exec(select(User)).all() if user.id
    }


def _get_or_404(session: Session, application_id: UUID) -> AdmissionApplication:
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
    application_id: UUID,
    application_in: AdmissionApplicationUpdate,
) -> AdmissionApplicationRead:
    application = _get_or_404(session, application_id)
    for field, value in application_in.model_dump(exclude_unset=True).items():
        if field in _SERVER_MANAGED and not value:
            continue
        setattr(application, field, value)
    application = repository.save_application(session, application)
    # The contact may have changed, so the logins follow it before the row is read
    # back - the response then shows the addresses that are actually in use.
    notes = _sync_logins(session, application)
    read = _read_registered(session, application)
    if notes:
        read.placement_note = " ".join(filter(None, [read.placement_note, *notes]))
    return read


def record_separation(
    session: Session,
    application_id: UUID,
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
    application_id: UUID,
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


def _login_candidate(*values: str | None) -> str | None:
    """The login a person gets: their email, else their phone, else nothing.

    The first value that was actually filled wins, in the order the caller passes
    them - email before phone. `None` means the form carried neither, and the person
    is created without a login rather than with an address nobody owns.
    """
    for value in values:
        cleaned = (value or "").strip()
        if cleaned:
            return cleaned
    return None


def _student_name(application: AdmissionApplication) -> str:
    parts = (
        application.student_first_name,
        application.student_middle_name,
        application.student_last_name,
    )
    name = " ".join(part.strip() for part in parts if part and part.strip())
    return name or "Student"


def _login_taken(session: Session, login: str) -> bool:
    """True when an account already signs in with this email or phone."""
    return (
        session.exec(
            select(User.id).where(func.lower(User.email) == login.strip().lower())
        ).first()
        is not None
    )


def _find_guardian_login(session: Session, login: str | None) -> User | None:
    """The guardian account already using this contact - email or phone - if any.

    A parent's second child shares one login: the form carries the same contact, so
    the existing guardian account is reused and only the parent-child link is added.
    """
    if not login or not login.strip():
        return None
    return session.exec(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.codename == "guardian",
            func.lower(User.email) == login.strip().lower(),
        )
    ).first()


def _guardian_block(application: AdmissionApplication) -> tuple[str, str | None, str]:
    """(name, login, relationship) from whichever block was filled.

    The login is the contact's **email**, or their **phone** when the form gave no
    email - never a generated address. `None` means neither was filled, and no
    guardian login is created.
    """
    if (
        application.guardian_name
        or application.guardian_email
        or application.guardian_phone
    ):
        return (
            application.guardian_name or "",
            _login_candidate(application.guardian_email, application.guardian_phone),
            application.guardian_relation or "Guardian",
        )
    if application.father_name or application.father_email or application.father_phone:
        return (
            application.father_name or "",
            _login_candidate(application.father_email, application.father_phone),
            "Father",
        )
    if application.mother_name or application.mother_email or application.mother_phone:
        return (
            application.mother_name or "",
            _login_candidate(application.mother_email, application.mother_phone),
            "Mother",
        )
    return ("", None, "Guardian")


def _sync_logins(session: Session, application: AdmissionApplication) -> list[str]:
    """Follow the form: a login **is** the email (or phone) on it, so an edit moves it.

    Only the accounts this application owns are touched, and a login another account
    already uses is never taken over - two people cannot share one login, so the note
    says what was left alone instead of silently locking somebody out.

    Runs on every write to a registered application, so the login can never drift
    away from the contact the office has on file. Editing a *draft* has nothing to
    sync: its logins do not exist yet.
    """
    notes: list[str] = []

    def move(user: User | None, wanted: str | None, who: str) -> None:
        if user is None:
            return
        if not wanted:
            # The contact was cleared on the form. The login is left where it is: an
            # account that already exists is not thrown away by an empty field.
            notes.append(
                f"The form carries no {who} email or phone, so the login is still "
                f"'{user.email}'."
            )
            return
        if wanted.lower() == user.email.lower():
            return
        if _login_taken(session, wanted):
            notes.append(
                f"'{wanted}' already belongs to another login, so the {who} login is "
                f"still '{user.email}'."
            )
            return
        previous = user.email
        user.email = wanted
        session.add(user)
        session.commit()
        notes.append(f"The {who} login changed from '{previous}' to '{wanted}'.")

    if application.student_user_id:
        move(
            session.get(User, application.student_user_id),
            _login_candidate(application.student_email),
            "student",
        )
    if application.guardian_user_id:
        _, guardian_login, _ = _guardian_block(application)
        move(
            session.get(User, application.guardian_user_id),
            guardian_login,
            "guardian",
        )
    return notes


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

    # The class and the section are ids into the two platform catalogs, and the
    # school's class-section row is created the first time it is used: registering
    # a student into "Class 10-A" is what puts that card on the Classroom screen.
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

    # --- 1. the student: one login + the profile the directory lists ---------
    student_name = _student_name(application)
    # The login is the email the family supplied - and nothing else. A form with no
    # student email leaves the student without a login (the office can add one),
    # because an address nobody owns can never be signed in with.
    student_login = _login_candidate(application.student_email)
    student_password: str | None = None
    student_user: User | None = None
    if student_login and _login_taken(session, student_login):
        notes.append(
            f"The email '{student_login}' already belongs to a login, so the student "
            "was created without one."
        )
    elif student_login:
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
    else:
        notes.append(
            "The form carried no student email, so the student was created without "
            "a login."
        )

    guardian_name, guardian_login, relationship = _guardian_block(application)
    student = StudentProfile(
        # The name lives on the profile: a student without a login still has one.
        full_name=student_name,
        user_id=student_user.id if student_user else None,
        # The form number becomes the admission number: one number, traceable
        # back to the application it came from.
        admission_number=application.application_no,
        date_of_birth=application.date_of_birth or date.today(),
        guardian_name=guardian_name,
        gender=application.gender or None,
        # The class-section row this student sits in - the one created just above.
        classroom_id=room.id if room else None,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    if student_user is not None and student_password is not None:
        credentials.append(
            LoginCredential(
                role="student",
                full_name=student_name,
                email=student_login or "",
                password=student_password,
            )
        )

    # --- 2. the guardian: one login per parent, shared by all their children -
    # The login is the contact the form gave - their email, or their phone when no
    # email was filled. No generated address: with neither, no guardian login.
    guardian = _find_guardian_login(session, guardian_login)
    guardian_password: str | None = None
    if guardian is None and guardian_name and guardian_login:
        guardian_password = generate_temp_password()
        guardian = User(
            email=guardian_login,
            full_name=guardian_name,
            hashed_password=get_password_hash(guardian_password),
            is_active=True,
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
    application.student_user_id = student_user.id if student_user else None
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
    session: Session, application_id: UUID
) -> AdmissionApplicationRead:
    """Register an application from the office screens.

    Creates the student + guardian records (once) and returns the logins with
    their first-time passwords, which the caller shows exactly once. Pressing it
    again on a row that is already registered changes nothing, except that the
    logins are brought back in step with the contact on the form.
    """
    application = _get_or_404(session, application_id)
    application.status = STATUS_REGISTERED
    session.add(application)
    session.commit()
    session.refresh(application)
    notes = _sync_logins(session, application)
    read = _read_registered(session, application)
    if notes:
        read.placement_note = " ".join(filter(None, [read.placement_note, *notes]))
    return read


def reset_login_password(
    session: Session, application_id: UUID, target: str
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
            detail=(
                f"This application has no {target} login (the form carried no email"
                + (" or phone" if target == "guardian" else "")
                + "), so there is nothing to reset."
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
