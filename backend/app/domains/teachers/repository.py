from uuid import UUID
from sqlmodel import Session, select

from app.domains.auth.models import Role, UserRole
from app.domains.auth.roles import grant_role
from app.domains.staff.models import Employee
from app.domains.users.models import User

from .schemas import TeacherCreate

TEACHING_ROLES = ("teacher", "class_teacher", "subject_teacher")


def _next_employee_code(session: Session) -> str:
    """Next EMP-#### across the employee table (mirrors the staff service)."""
    codes = session.exec(select(Employee.employee_code)).all()
    numbers = [
        int(code.rsplit("-", 1)[-1])
        for code in codes
        if code and code.rsplit("-", 1)[-1].isdigit()
    ]
    return f"EMP-{max(numbers, default=36) + 1:04d}"


def get_teacher_by_id(session: Session, teacher_id: UUID) -> Employee | None:
    return session.get(Employee, teacher_id)


def get_teacher_by_user_id(session: Session, user_id: UUID) -> Employee | None:
    statement = select(Employee).where(Employee.user_id == user_id)
    return session.exec(statement).first()


def get_teachers(
    session: Session, skip: int = 0, limit: int = 100
) -> list[Employee]:
    """Employees holding at least one teaching role (roles live in `user_role`)."""
    statement = (
        select(Employee)
        .join(UserRole, UserRole.user_id == Employee.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(TEACHING_ROLES))
        .distinct()
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def create_teacher(session: Session, teacher_in: TeacherCreate) -> Employee:
    db_teacher = Employee(
        user_id=teacher_in.user_id,
        employee_code=_next_employee_code(session),
        department=teacher_in.department,
        qualification=teacher_in.qualification,
        joining_date=teacher_in.joining_date,
    )
    session.add(db_teacher)
    session.commit()
    session.refresh(db_teacher)

    # The role lives in `user_role`, not on the employee row. `grant_role` adds
    # it without disturbing any role the person already holds.
    user = session.get(User, teacher_in.user_id)
    if user is not None:
        grant_role(session, user, "teacher")
    return db_teacher
