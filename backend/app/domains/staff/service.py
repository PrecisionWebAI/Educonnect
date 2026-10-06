"""Staff registration - hiring that starts at "this person is hired".

Submitting the short registration form on the Staff Hiring screen is the whole
hiring action. The server mints the employee code (EMP-####), creates the
person's login (``stf.*`` for non-teaching roles, ``tea.*`` for the teaching
ones), creates their ``staffprofile`` row - plus a ``teacherprofile`` row for
teaching roles, because the class assignment and timetable screens place
teachers through it - and stamps the registration with those links, the way a
student admission does. The first-time password is returned exactly once and
can be reset from the Hired tab afterwards.

Promotion is idempotent: a registration that already carries its links is left
alone, so pressing submit twice can never make two accounts from one form.

The candidate pipeline (``hiringcandidate``) is a separate funnel of people who
might be hired one day; it does not feed this flow.
"""

import re
from datetime import date

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.security import generate_temp_password, get_password_hash
from app.domains.auth.models import Role, utcnow
from app.domains.auth.roles import set_user_roles
from app.domains.hiring.models import FIRST_EMP_NUMBER
from app.domains.hiring.repository import get_emp_ids
from app.domains.staff.models import StaffProfile, StaffRegistration
from app.domains.staff.schemas import (
    LoginCredential,
    StaffPasswordResetRead,
    StaffProfileRead,
    StaffRegistrationCreate,
    StaffRegistrationRead,
)
from app.domains.teachers.models import TeacherProfile
from app.domains.users.models import User

#: School logins are generated, never typed.
SCHOOL_EMAIL_DOMAIN = "educonnect.com"
TEACHING_EMAIL_PREFIX = "tea"
STAFF_EMAIL_PREFIX = "stf"

#: Roles that also get a `teacherprofile` row (these people take classes).
TEACHING_ROLES = ("teacher", "class_teacher", "subject_teacher")

#: Roles this screen never hires - they are made somewhere else, if at all.
NOT_HIRED_HERE = ("student", "guardian", "system_admin", "owner")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _login_emails(session: Session) -> dict[int, str]:
    """{user_id: email} - so a list of registrations can show the logins it made."""
    return {user.id: user.email for user in session.exec(select(User)).all()}


def _read(
    registration: StaffRegistration, emails: dict[int, str] | None = None
) -> StaffRegistrationRead:
    """ORM row -> response model, with the login email it created (if any)."""
    lookup = emails or {}
    return StaffRegistrationRead.model_validate(
        {
            **registration.model_dump(),
            "login_email": (
                lookup.get(registration.user_id) if registration.user_id else None
            ),
        }
    )


def list_registrations(session: Session) -> list[StaffRegistrationRead]:
    """Every hire-registration, newest first."""
    emails = _login_emails(session)
    rows = session.exec(
        select(StaffRegistration).order_by(StaffRegistration.id.desc())
    ).all()
    return [_read(row, emails) for row in rows]


def list_profiles(session: Session) -> list[StaffProfileRead]:
    """The staff the school actually has - one row per login."""
    users = {user.id: user for user in session.exec(select(User)).all()}
    rows = session.exec(select(StaffProfile).order_by(StaffProfile.id.desc())).all()
    return [
        StaffProfileRead(
            id=profile.id,
            user_id=profile.user_id,
            employee_code=profile.employee_code,
            full_name=users[profile.user_id].full_name
            if profile.user_id in users
            else "Staff",
            email=users[profile.user_id].email if profile.user_id in users else "",
            role_codename=profile.role_codename,
            department=profile.department,
            qualification=profile.qualification,
            experience_years=profile.experience_years,
            joining_date=profile.joining_date,
            is_teacher=_is_teaching(profile.role_codename),
        )
        for profile in rows
    ]


# ---------------------------------------------------------------------------
# Registering (the write path)
# ---------------------------------------------------------------------------


def create_registration(
    session: Session, registration_in: StaffRegistrationCreate
) -> StaffRegistrationRead:
    """Register - and hire - in one step.

    Stores the form and promotes it immediately (login + staff record + employee
    code), returning the logins with their one-time passwords.
    """
    full_name = (registration_in.full_name or "").strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="Full name is required")
    department = (registration_in.department or "").strip()
    if not department:
        raise HTTPException(status_code=422, detail="Department is required")
    _validate_role(session, registration_in.role_codename)

    registration = StaffRegistration(
        full_name=full_name,
        role_codename=registration_in.role_codename,
        department=department,
        qualification=(registration_in.qualification or "").strip() or None,
        experience_years=registration_in.experience_years or 0,
        contact_email=(registration_in.contact_email or "").strip() or None,
        joining_date=registration_in.joining_date or date.today(),
        notes=(registration_in.notes or "").strip() or None,
    )
    session.add(registration)
    session.commit()
    session.refresh(registration)

    credentials = _promote(session, registration)
    read = _read(registration, _login_emails(session))
    read.credentials = credentials or None
    return read


def reset_login_password(session: Session, profile_id: int) -> StaffPasswordResetRead:
    """Mint a new first-time password for a hired staff member's login."""
    profile = session.get(StaffProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Staff member not found")
    user = session.get(User, profile.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="This staff member has no login")

    password = generate_temp_password()
    user.hashed_password = get_password_hash(password)
    session.add(user)
    session.commit()
    return StaffPasswordResetRead(
        full_name=user.full_name, email=user.email, password=password
    )


# ---------------------------------------------------------------------------
# Promotion - a registration becoming a real staff member
# ---------------------------------------------------------------------------


def _is_teaching(role_codename: str) -> bool:
    return role_codename in TEACHING_ROLES


def _email_prefix(role_codename: str) -> str:
    """Teaching roles get `tea.`, everyone else `stf.`."""
    return TEACHING_EMAIL_PREFIX if _is_teaching(role_codename) else STAFF_EMAIL_PREFIX


def _slug(value: str | None, fallback: str = "staff") -> str:
    """`"Meera Iyer"` -> `"meera.iyer"` (email-safe)."""
    cleaned = re.sub(r"[^a-z0-9]+", ".", (value or "").strip().lower())
    return cleaned.strip(".") or fallback


def _tail_number(value: str | None) -> int | None:
    """`EMP-0039` -> 39."""
    if not value:
        return None
    tail = value.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _validate_role(session: Session, codename: str) -> str:
    """The role must exist in the catalog and be one this screen can hire."""
    if codename in NOT_HIRED_HERE:
        raise HTTPException(
            status_code=422,
            detail=f"'{codename}' cannot be hired from this screen.",
        )
    if not session.exec(select(Role).where(Role.codename == codename)).first():
        raise HTTPException(status_code=422, detail=f"Unknown role '{codename}'.")
    return codename


def _free_email(session: Session, local_part: str) -> str:
    """`local@domain`, with `.2`, `.3` appended until the address is unused."""
    candidate = f"{local_part}@{SCHOOL_EMAIL_DOMAIN}"
    suffix = 1
    while session.exec(select(User).where(User.email == candidate)).first():
        suffix += 1
        candidate = f"{local_part}.{suffix}@{SCHOOL_EMAIL_DOMAIN}"
    return candidate


def _next_employee_code(session: Session) -> str:
    """Next EMP-#### - pipeline hires included, so no two people share a code."""
    issued = list(get_emp_ids(session)) + list(
        session.exec(select(StaffProfile.employee_code)).all()
    )
    numbers = [
        number
        for number in (_tail_number(value) for value in issued)
        if number is not None
    ]
    return f"EMP-{max(numbers, default=FIRST_EMP_NUMBER - 1) + 1:04d}"


def _promote(
    session: Session, registration: StaffRegistration
) -> list[LoginCredential]:
    """Create the login and the staff record for a registration (once).

    Idempotent: a row that already carries `staff_profile_id` is left alone, so
    submitting twice can never make two accounts from one form. Returns the login
    it created, with its one-time password.
    """
    if registration.staff_profile_id and registration.user_id:
        return []

    full_name = registration.full_name.strip() or "Staff"
    role_codename = registration.role_codename
    credentials: list[LoginCredential] = []

    # --- 1. the login ---------------------------------------------------
    user = session.get(User, registration.user_id) if registration.user_id else None
    if user is None:
        password = generate_temp_password()
        user = User(
            email=_free_email(
                session, f"{_email_prefix(role_codename)}.{_slug(full_name)}"
            ),
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            contact_email=registration.contact_email,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        set_user_roles(session, user, [role_codename])
        credentials.append(
            LoginCredential(
                role=role_codename,
                full_name=full_name,
                email=user.email,
                password=password,
                created=True,
            )
        )

    # --- 2. the staff record the school actually holds --------------------
    profile = (
        session.get(StaffProfile, registration.staff_profile_id)
        if registration.staff_profile_id
        else None
    )
    if profile is None:
        teacher_profile_id: int | None = None
        if _is_teaching(role_codename):
            # Class assignment and timetable place teachers through
            # `teacherprofile`, so a teaching hire owns both rows.
            teacher = TeacherProfile(
                user_id=user.id,
                department=registration.department,
                qualification=registration.qualification or "",
                joining_date=registration.joining_date,
            )
            session.add(teacher)
            session.commit()
            session.refresh(teacher)
            teacher_profile_id = teacher.id
        profile = StaffProfile(
            user_id=user.id,
            employee_code=_next_employee_code(session),
            role_codename=role_codename,
            department=registration.department,
            qualification=registration.qualification,
            experience_years=registration.experience_years or 0,
            joining_date=registration.joining_date,
            teacher_profile_id=teacher_profile_id,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

    # --- 3. stamp the link, so the two screens can never disagree ---------
    registration.staff_profile_id = profile.id
    registration.user_id = user.id
    registration.promoted_at = registration.promoted_at or utcnow()
    session.add(registration)
    session.commit()
    session.refresh(registration)

    return credentials
