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

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.security import generate_temp_password, get_password_hash
from app.domains.auth.models import Role, UserRole
from app.domains.auth.roles import set_user_roles
from app.domains.hiring.models import FIRST_EMP_NUMBER
from app.domains.hiring.repository import get_emp_ids
from app.domains.salary.models import EmployeeSalary
from app.domains.staff.models import Employee
from app.domains.teachers.models import TeacherSubject
from app.domains.staff.schemas import (
    LoginCredential,
    StaffPasswordResetRead,
    StaffProfileCreate,
    StaffProfileCreateRead,
    StaffProfileRead,
)
from app.domains.users.models import User

#: Roles that teach (these people take classes).
TEACHING_ROLES = ("teacher", "class_teacher", "subject_teacher")

#: Roles this screen never hires - they are made somewhere else, if at all.
NOT_HIRED_HERE = ("student", "guardian", "system_admin", "school_admin")

#: Sentinel for "the caller did not load this, go and read it".
_UNSET = object()


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
        from app.domains.hiring.models import STATUS_HIRED, HiringCandidate

        candidate = session.get(HiringCandidate, profile_in.candidate_id)
        if candidate is not None and candidate.status != STATUS_HIRED:
            candidate.status = STATUS_HIRED
            candidate.emp_id = profile.employee_code
            candidate.decided_at = datetime.utcnow()
            session.add(candidate)
            session.commit()

    return StaffProfileCreateRead.model_validate(
        {**_profile_read(session, profile).model_dump(), "credentials": credentials or None}
    )


def _profile_read(
    session: Session,
    profile: Employee,
    *,
    user: User | None = None,
    roles: list[str] | None = None,
    subject_ids: list[int] | None = None,
    salary_monthly: float | None | object = _UNSET,
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
    session: Session, profile_id: int, profile_in: StaffProfileCreate
) -> StaffProfileRead:
    """Edit an existing employee's record (the Hired tab's Edit action)."""
    profile = session.get(Employee, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    roles = _validate_roles(session, _resolve_roles(profile_in))

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
    profile.email = (profile_in.contact_email or "").strip() or None
    profile.phone = (profile_in.phone or "").strip() or None
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


def reset_login_password(session: Session, profile_id: int) -> StaffPasswordResetRead:
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


# ---------------------------------------------------------------------------
# Promotion - a registration becoming a real staff member
# ---------------------------------------------------------------------------


def _is_teaching(roles: list[str]) -> bool:
    """True when the person holds at least one teaching role."""
    return any(role in TEACHING_ROLES for role in roles)


def _roles_by_user(session: Session, user_ids: list[int]) -> dict[int, list[str]]:
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
    grouped: dict[int, list[tuple[bool, str]]] = {}
    for user_id, codename, is_primary in rows:
        grouped.setdefault(user_id, []).append((is_primary, codename))
    return {
        user_id: [
            name for _, name in sorted(pairs, key=lambda pair: (not pair[0], pair[1]))
        ]
        for user_id, pairs in grouped.items()
    }


def _roles_of_user(session: Session, user_id: int) -> list[str]:
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
    session: Session, teacher_ids: list[int]
) -> dict[int, list[int]]:
    """{employee_id: [subject_id, ...]} - one query for the whole Hired tab."""
    unique_ids = list(dict.fromkeys(teacher_ids))
    if not unique_ids:
        return {}
    rows = session.exec(
        select(TeacherSubject.teacher_id, TeacherSubject.subject_id)
        .where(TeacherSubject.teacher_id.in_(unique_ids))
        .order_by(TeacherSubject.subject_id)
    ).all()
    grouped: dict[int, list[int]] = {}
    for teacher_id, subject_id in rows:
        grouped.setdefault(teacher_id, []).append(subject_id)
    return grouped


def _set_teacher_subjects(
    session: Session, teacher_id: int, subject_ids: list[int]
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


def _resolve_subject_ids(profile_in: StaffProfileCreate) -> list[int]:
    """The subjects a hire asks for: the list, else the single legacy field."""
    ids = [int(value) for value in (profile_in.subject_ids or []) if value]
    if not ids and profile_in.subject_id:
        ids = [profile_in.subject_id]
    return list(dict.fromkeys(ids))


def _salaries_by_employee(
    session: Session, employee_ids: list[int]
) -> dict[int, float]:
    """{employee_id: salary_monthly} - one query for the whole Hired tab."""
    unique_ids = list(dict.fromkeys(employee_ids))
    if not unique_ids:
        return {}
    rows = session.exec(
        select(EmployeeSalary.employee_id, EmployeeSalary.salary_monthly).where(
            EmployeeSalary.employee_id.in_(unique_ids)
        )
    ).all()
    return {employee_id: salary for employee_id, salary in rows}


def _set_employee_salary(
    session: Session, employee_id: int, salary_monthly: float | None
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
    """Next EMP-#### - pipeline hires included, so no two people share a code."""
    issued = list(get_emp_ids(session)) + list(
        session.exec(select(Employee.employee_code)).all()
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
    subject_ids: list[int],
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
    full_name = full_name.strip() or "Staff"
    credentials: list[LoginCredential] = []

    # --- 1. the login (the email the form supplied, like student/guardian) ---
    email = (contact_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(
            status_code=422, detail="A login with this email already exists."
        )
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
