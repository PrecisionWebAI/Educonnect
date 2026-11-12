"""Staff (employee) flow - hiring that starts at "this person is hired".

Filling the hire form on the Staff Hiring screen is the whole hiring action: the
server mints the employee code (EMP-####), creates the person's login (using the
email the form supplied - exactly like a student / guardian login), and writes
their ``employee`` row directly. The first-time password is returned exactly once
and can be reset from the Hired tab afterwards.

The candidate pipeline (``pipeline_hiring_table``) is a separate funnel of people
who might be hired one day; hiring a candidate calls the same helper below.
"""

from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core import contacts
from app.core.security import generate_temp_password, get_password_hash
from app.core.tenancy import SKIP_SCHOOL
from app.core.text import canonical_phone, phone_problem
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.auth.roles import grant_role, set_user_roles
from app.domains.operations.salary.models import EmployeeSalary
from app.domains.operations.staff_hiring.models import FIRST_EMP_NUMBER
from app.domains.operations.staff_hiring.repository import get_emp_ids
from app.domains.people.staff.models import Employee
from app.domains.people.staff.schemas import (
    LoginCredential,
    StaffPasswordResetRead,
    StaffProfileCreate,
    StaffProfileCreateRead,
    StaffProfileRead,
)
from app.domains.people.teachers import labels
from app.domains.people.teachers.models import TeacherSubject

#: Roles that teach (these people take classes). `class_teacher` and
#: `subject_teacher` are gone: who runs a section and who takes a subject are
#: assignments (`classroom.class_teacher_id`, `subjectteacher`), not roles.
#: The list itself lives in `people/teachers/labels.py`, so the directory and this
#: screen's `isTeacher` flag read one definition and cannot drift apart.
TEACHING_ROLES = labels.TEACHING_ROLES

#: Roles this screen never hires - they are made somewhere else, if at all.
NOT_HIRED_HERE = ("student", "guardian", "system_admin", "school_admin")

#: What the hire form cannot be submitted without: a label plus every field that
#: can satisfy it. The same rule the admission form follows
#: (`admissions/service.py`): the record *is* the person, so a name, a way to
#: reach them, the role their login opens and the bank their salary is paid into
#: are not optional. A hire without them is an employee nobody can contact, a
#: login that opens nothing, or a salary that cannot be paid.
#:
#: Enforced on **create and edit** alike, so a saved hire cannot be left
#: half-identified and "completed" by nobody.
REQUIRED_TO_HIRE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("the full name", ("full_name",)),
    ("the contact email", ("contact_email",)),
    ("the phone number", ("phone",)),
    ("at least one role", ("role_codenames",)),
    ("the bank name", ("bank_name",)),
)

#: Sentinel for "the caller did not load this, go and read it".
_UNSET = object()


def _filled(value: object) -> bool:
    """True when a value counts as answered (text, or a list with an entry)."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return value is not None


def _require_hire_fields(
    *,
    full_name: str | None,
    contact_email: str | None,
    phone: str | None,
    role_codenames: list[str] | tuple[str, ...],
    bank_name: str | None,
) -> None:
    """Refuse a hire that is missing a mandatory field, naming what is missing.

    `422`, like every other rejected body, so the form can say exactly which field
    the office still has to fill instead of failing silently (the hire used to be
    saved with the name "Staff").
    """
    values: dict[str, object] = {
        "full_name": full_name,
        "contact_email": contact_email,
        "phone": phone,
        "role_codenames": list(role_codenames or []),
        "bank_name": bank_name,
    }
    missing = [
        label
        for label, fields in REQUIRED_TO_HIRE
        if not any(_filled(values.get(field)) for field in fields)
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Fill in "
            + ", ".join(missing)
            + " before registering the employee.",
        )

    # The number has to be ringable: exactly ten digits (`app/core/text.py`).
    problem = phone_problem(phone)
    if problem:
        raise HTTPException(status_code=422, detail=problem)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def list_profiles(session: Session) -> list[StaffProfileRead]:
    """The staff the school actually has - one row per login."""
    users = {user.id: user for user in session.exec(select(User)).all()}
    rows = session.exec(select(Employee).order_by(Employee.id.desc())).all()
    roles = _roles_by_user(session, [profile.user_id for profile in rows])
    subjects = _subjects_by_teacher(session, [profile.id for profile in rows])
    salaries = _salaries_by_employee(session, [profile.id for profile in rows])
    return [
        _profile_read(
            session,
            profile,
            user=users.get(profile.user_id),
            roles=roles.get(profile.user_id, []),
            subject_ids=subjects.get(profile.id, []),
            salary_monthly=salaries.get(profile.id),
        )
        for profile in rows
    ]


# ---------------------------------------------------------------------------
# Registering (the write path)
# ---------------------------------------------------------------------------


def create_profile(
    session: Session, profile_in: StaffProfileCreate
) -> StaffProfileCreateRead:
    """Fill the hire form -> write the `staffprofile` row (and its login).

    This is the single hiring action: the login (``tea.*`` / ``stf.*``), the
    employee code and the staff record are all created here, so the form and the
    employee record are one and the same.
    """
    full_name = (profile_in.full_name or "").strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="Full name is required")
    department = (profile_in.department or "").strip()
    if not department:
        raise HTTPException(status_code=422, detail="Department is required")
    roles = _validate_roles(session, _resolve_roles(profile_in))

    profile, credentials = _create_employee(
        session,
        full_name=full_name,
        role_codenames=roles,
        department=department,
        qualification=(profile_in.qualification or "").strip() or None,
        experience_years=profile_in.experience_years or 0,
        contact_email=(profile_in.contact_email or "").strip() or None,
        joining_date=profile_in.joining_date or date.today(),
        phone=(profile_in.phone or "").strip() or None,
        subject_ids=_resolve_subject_ids(profile_in),
        address=(profile_in.address or "").strip() or None,
        emergency_contact=(profile_in.emergency_contact or "").strip() or None,
        aadhaar_no=(profile_in.aadhaar_no or "").strip() or None,
        pan_no=(profile_in.pan_no or "").strip() or None,
        bank_name=(profile_in.bank_name or "").strip() or None,
        bank_account_no=(profile_in.bank_account_no or "").strip() or None,
        ifsc=(profile_in.ifsc or "").strip() or None,
        salary_monthly=profile_in.salary_monthly,
        previous_employer_monthly_salary=profile_in.previous_employer_monthly_salary,
    )
    if profile_in.candidate_id:
        from app.domains.operations.staff_hiring.models import (
            STATUS_HIRED,
            HiringCandidate,
        )

        candidate = session.get(HiringCandidate, profile_in.candidate_id)
        if candidate is not None and candidate.status != STATUS_HIRED:
            candidate.status = STATUS_HIRED
            candidate.emp_id = profile.employee_code
            candidate.decided_at = datetime.utcnow()
            session.add(candidate)
            session.commit()

    return StaffProfileCreateRead.model_validate(
        {
            **_profile_read(session, profile).model_dump(),
            "credentials": credentials or None,
        }
    )


def _profile_read(
    session: Session,
    profile: Employee,
    *,
    user: User | None = None,
    roles: list[str] | None = None,
    subject_ids: list[UUID] | None = None,
    salary_monthly: float | object | None = _UNSET,
) -> StaffProfileRead:
    """ORM profile + its login + roles + subjects + salary -> response model."""
    if user is None:
        user = session.get(User, profile.user_id) if profile.user_id else None
    if roles is None:
        roles = _roles_of_user(session, profile.user_id) if profile.user_id else []
    if subject_ids is None:
        subject_ids = _subjects_by_teacher(session, [profile.id]).get(profile.id, [])
    if salary_monthly is _UNSET:
        salary_monthly = _salaries_by_employee(session, [profile.id]).get(profile.id)
    return StaffProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        employee_code=profile.employee_code,
        full_name=user.full_name if user else "Staff",
        email=user.email if user else "",
        role_codename=roles[0] if roles else "",
        role_codenames=roles,
        department=profile.department,
        qualification=profile.qualification,
        experience_years=profile.experience_years,
        joining_date=profile.joining_date,
        is_teacher=_is_teaching(roles),
        # --- lifecycle ------------------------------------------------------
        # What the Hired tab's badge reads: `isActive` is the staff side, `loginActive`
        # is the account (which a teacher-parent keeps after being let go).
        isActive=profile.deactivated_at is None,
        leftOn=profile.left_on.isoformat() if profile.left_on else None,
        deactivatedAt=(
            profile.deactivated_at.isoformat() if profile.deactivated_at else None
        ),
        deactivatedRoles=[
            name.strip()
            for name in (profile.deactivated_roles or "").split(",")
            if name.strip()
        ],
        loginActive=True if user is None else bool(user.is_active),
        contact_email=profile.email,
        phone=profile.phone,
        subject_ids=subject_ids,
        address=profile.address,
        emergency_contact=profile.emergency_contact,
        aadhaar_no=profile.aadhaar_no,
        pan_no=profile.pan_no,
        bank_name=profile.bank_name,
        bank_account_no=profile.bank_account_no,
        ifsc=profile.ifsc,
        previous_employer_monthly_salary=profile.previous_employer_monthly_salary,
        salary_monthly=salary_monthly,
    )


def update_profile(
    session: Session, profile_id: UUID, profile_in: StaffProfileCreate
) -> StaffProfileRead:
    """Edit an existing employee's record (the Hired tab's Edit action)."""
    profile = session.get(Employee, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    roles = _validate_roles(session, _resolve_roles(profile_in))
    # An employee stays complete: what the hire form insists on cannot be emptied
    # afterwards either (the name, the contact and the role the login opens).
    _require_hire_fields(
        full_name=profile_in.full_name,
        contact_email=profile_in.contact_email,
        phone=profile_in.phone,
        role_codenames=roles,
        bank_name=profile_in.bank_name,
    )

    user = session.get(User, profile.user_id)
    full_name = (profile_in.full_name or "").strip()
    if full_name and user is not None:
        user.full_name = full_name
        session.add(user)

    if user is not None:
        set_user_roles(session, user, roles)

    profile.department = (profile_in.department or "").strip() or profile.department
    profile.qualification = (profile_in.qualification or "").strip() or None
    profile.experience_years = profile_in.experience_years or 0
    profile.joining_date = profile_in.joining_date or profile.joining_date
    # The contact is the person's: it cannot be taken from somebody else, and an edit
    # moves every record of that person together (their login, their guardian row and
    # their staff row) so they never disagree about how to reach them.
    profile_email = (profile_in.contact_email or "").strip().lower() or None
    profile_phone = (profile_in.phone or "").strip() or None
    contacts.require_contact_free(
        session,
        who="The employee",
        phone=profile_phone,
        email=profile_email,
        **contacts.allow_ids_for_user(session, profile.user_id),
    )
    contacts.sync_contact(
        session, user_id=profile.user_id, email=profile_email, phone=profile_phone
    )
    # `sync_contact` moved the whole person; these two lines keep the row it wrote
    # consistent with it (the phone in its canonical ten-digit form).
    profile.email = profile_email or profile.email
    profile.phone = canonical_phone(profile_phone) or profile.phone
    _set_teacher_subjects(session, profile.id, _resolve_subject_ids(profile_in))
    profile.address = (profile_in.address or "").strip() or None
    profile.emergency_contact = (profile_in.emergency_contact or "").strip() or None
    profile.aadhaar_no = (profile_in.aadhaar_no or "").strip() or None
    profile.pan_no = (profile_in.pan_no or "").strip() or None
    profile.bank_name = (profile_in.bank_name or "").strip() or None
    profile.bank_account_no = (profile_in.bank_account_no or "").strip() or None
    profile.ifsc = (profile_in.ifsc or "").strip() or None
    _set_employee_salary(session, profile.id, profile_in.salary_monthly)
    profile.previous_employer_monthly_salary = (
        profile_in.previous_employer_monthly_salary
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _profile_read(session, profile)


def reset_login_password(session: Session, profile_id: UUID) -> StaffPasswordResetRead:
    """Mint a new first-time password for a hired staff member's login."""
    profile = session.get(Employee, profile_id)
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


def delete_profile(session: Session, profile_id: UUID) -> None:
    """Kept as this domain's name for it; the rule lives in `lifecycle.py`.

    Deleting a member of staff is not the same act as deactivating them (nothing is
    deleted there), and the difference - what goes, what stays, and what refuses to go -
    is the whole of `lifecycle.delete_profile`.
    """
    from app.domains.people.staff import lifecycle

    lifecycle.delete_profile(session=session, profile_id=profile_id)


# ---------------------------------------------------------------------------
# Promotion - a registration becoming a real staff member
# ---------------------------------------------------------------------------


def _is_teaching(roles: list[str]) -> bool:
    """True when the person holds at least one teaching role."""
    return any(role in TEACHING_ROLES for role in roles)


def _roles_by_user(session: Session, user_ids: list[UUID]) -> dict[UUID, list[str]]:
    """{user_id: [role codename, ...]} - primary first, then alphabetical.

    One query for the whole Hired tab, so it does not run a query per row.
    """
    unique_ids = list(dict.fromkeys(user_ids))
    if not unique_ids:
        return {}
    rows = session.exec(
        select(UserRole.user_id, Role.codename, UserRole.is_primary)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id.in_(unique_ids))
    ).all()
    grouped: dict[UUID, list[tuple[bool, str]]] = {}
    for user_id, codename, is_primary in rows:
        grouped.setdefault(user_id, []).append((is_primary, codename))
    return {
        user_id: [
            name for _, name in sorted(pairs, key=lambda pair: (not pair[0], pair[1]))
        ]
        for user_id, pairs in grouped.items()
    }


def _roles_of_user(session: Session, user_id: UUID) -> list[str]:
    """The role codenames one user holds (primary first)."""
    return _roles_by_user(session, [user_id]).get(user_id, [])


def _resolve_roles(profile_in: StaffProfileCreate) -> list[str]:
    """The roles a hire asks for: the list, else the single legacy field."""
    roles = [
        codename.strip()
        for codename in (profile_in.role_codenames or [])
        if codename and codename.strip()
    ]
    if not roles and profile_in.role_codename:
        roles = [profile_in.role_codename.strip()]
    if not roles:
        raise HTTPException(status_code=422, detail="At least one role is required.")
    return list(dict.fromkeys(roles))


def _validate_roles(session: Session, codenames: list[str]) -> list[str]:
    """Every role must exist and be one this screen may hire."""
    for codename in codenames:
        _validate_role(session, codename)
    return codenames


def _subjects_by_teacher(
    session: Session, teacher_ids: list[UUID]
) -> dict[UUID, list[UUID]]:
    """{employee_id: [subject_id, ...]} - one query for the whole Hired tab."""
    unique_ids = list(dict.fromkeys(teacher_ids))
    if not unique_ids:
        return {}
    rows = session.exec(
        select(TeacherSubject.teacher_id, TeacherSubject.subject_id)
        .where(TeacherSubject.teacher_id.in_(unique_ids))
        .order_by(TeacherSubject.subject_id)
    ).all()
    grouped: dict[UUID, list[UUID]] = {}
    for teacher_id, subject_id in rows:
        grouped.setdefault(teacher_id, []).append(subject_id)
    return grouped


def _set_teacher_subjects(
    session: Session, teacher_id: UUID, subject_ids: list[UUID]
) -> None:
    """Replace a teacher's subject list with exactly `subject_ids`."""
    existing = session.exec(
        select(TeacherSubject).where(TeacherSubject.teacher_id == teacher_id)
    ).all()
    for row in existing:
        session.delete(row)
    session.flush()
    for subject_id in dict.fromkeys(subject_ids):
        session.add(TeacherSubject(teacher_id=teacher_id, subject_id=subject_id))
    session.commit()


def _resolve_subject_ids(profile_in: StaffProfileCreate) -> list[UUID]:
    """The subjects a hire asks for: the list, else the single legacy field."""
    ids = [UUID(str(value)) for value in (profile_in.subject_ids or []) if value]
    if not ids and profile_in.subject_id:
        ids = [profile_in.subject_id]
    return list(dict.fromkeys(ids))


def _salaries_by_employee(
    session: Session, employee_ids: list[UUID]
) -> dict[UUID, float]:
    """{employee_id: salary_monthly} - one query for the whole Hired tab."""
    unique_ids = list(dict.fromkeys(employee_ids))
    if not unique_ids:
        return {}
    rows = session.exec(
        select(EmployeeSalary.employee_id, EmployeeSalary.salary_monthly).where(
            EmployeeSalary.employee_id.in_(unique_ids)
        )
    ).all()
    return dict(rows)


def _set_employee_salary(
    session: Session, employee_id: UUID, salary_monthly: float | None
) -> None:
    """Write the employee's current salary row, or clear it when there is none."""
    row = session.exec(
        select(EmployeeSalary).where(EmployeeSalary.employee_id == employee_id)
    ).first()
    if salary_monthly is None:
        if row is not None:
            session.delete(row)
            session.commit()
        return
    if row is None:
        row = EmployeeSalary(employee_id=employee_id, salary_monthly=salary_monthly)
    else:
        row.salary_monthly = salary_monthly
    session.add(row)
    session.commit()


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


def _next_employee_code(session: Session) -> str:
    """Next EMP-#### - every school's codes included, so no two people share one.

    `employee_code` is unique across the whole platform, but the session is bound to
    one school - so the read has to step outside the tenant filter. Without this the
    second school minted a code the first one already had, and the hire failed with a
    unique violation.
    """
    issued = list(get_emp_ids(session)) + list(
        session.exec(
            select(Employee.employee_code), execution_options={SKIP_SCHOOL: True}
        ).all()
    )
    numbers = [
        number
        for number in (_tail_number(value) for value in issued)
        if number is not None
    ]
    return f"EMP-{max(numbers, default=FIRST_EMP_NUMBER - 1) + 1:04d}"


def _create_employee(
    session: Session,
    *,
    full_name: str,
    role_codenames: list[str],
    department: str,
    qualification: str | None,
    experience_years: int,
    contact_email: str | None,
    joining_date: date,
    phone: str | None,
    subject_ids: list[UUID],
    address: str | None,
    emergency_contact: str | None,
    aadhaar_no: str | None,
    pan_no: str | None,
    bank_name: str | None,
    bank_account_no: str | None,
    ifsc: str | None,
    salary_monthly: float | None,
    previous_employer_monthly_salary: float | None,
) -> tuple[Employee, list[LoginCredential]]:
    """Create the login + employee record for one hire. Returns (employee, logins)."""
    _require_hire_fields(
        full_name=full_name,
        contact_email=contact_email,
        phone=phone,
        role_codenames=role_codenames,
        bank_name=bank_name,
    )
    full_name = full_name.strip()
    credentials: list[LoginCredential] = []

    # --- 1. the login (the email the form supplied, like student/guardian) ---
    email = (contact_email or "").strip().lower()

    # One contact, one person (`app/core/contacts.py`). A teacher who is also a parent is
    # **already on file**: their own number and address are theirs, so hiring them links
    # the person instead of making a second one. Somebody else's contact is refused here,
    # naming the family or the member of staff it belongs to.
    person = session.exec(select(User).where(User.email == email)).first()
    if (
        person is not None
        and session.exec(select(Employee).where(Employee.user_id == person.id)).first()
    ):
        raise HTTPException(
            status_code=422, detail="This login is already on the staff roll."
        )
    contacts.require_contact_free(
        session,
        who="The employee",
        phone=phone,
        email=email,
        **contacts.allow_ids_for_user(session, person.id if person else None),
    )

    if person is not None:
        # Their login stays as it is - the hire **adds the staff role** to the account
        # they already sign in with (a parent who now works here keeps one login).
        user = person
        granted = [code for code in role_codenames if grant_role(session, user, code)]
        credentials.append(
            LoginCredential(
                role=role_codenames[0],
                full_name=user.full_name,
                email=user.email,
                password=None,
                created=False,
            )
        )
        _ = granted  # the roles the hire added to the account they already had
    else:
        password = generate_temp_password()
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        set_user_roles(session, user, role_codenames)
        credentials.append(
            LoginCredential(
                role=role_codenames[0],
                full_name=full_name,
                email=user.email,
                password=password,
                created=True,
            )
        )

    # --- 2. the employee record (the main table) ------------------------
    profile = Employee(
        user_id=user.id,
        employee_code=_next_employee_code(session),
        department=department,
        qualification=qualification,
        experience_years=experience_years or 0,
        joining_date=joining_date,
        email=contact_email,
        phone=phone,
        address=address,
        emergency_contact=emergency_contact,
        aadhaar_no=aadhaar_no,
        pan_no=pan_no,
        bank_name=bank_name,
        bank_account_no=bank_account_no,
        ifsc=ifsc,
        previous_employer_monthly_salary=previous_employer_monthly_salary,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    # Subjects and salary are their own tables (many subjects; salary separate).
    _set_teacher_subjects(session, profile.id, subject_ids)
    _set_employee_salary(session, profile.id, salary_monthly)

    return profile, credentials
