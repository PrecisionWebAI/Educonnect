from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission, get_current_active_user
from app.domains.auth.service import PLATFORM_ROLES

from . import service
from .models import RoleEnum, User, UserCreate, UserRead

router = APIRouter()


def _reject_platform_roles(roles: list[RoleEnum], current_user: User) -> None:
    """A school admin must never mint platform-level roles (for itself or others)."""
    if current_user.school_id is None:
        return  # the platform admin may grant anything
    banned = [role.value for role in roles if role.value in PLATFORM_ROLES]
    if banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Roles {banned} can only be granted by a platform admin",
        )


def _require_same_school(school_id: UUID | None, current_user: User) -> None:
    """404 when the caller is school-scoped and the target belongs elsewhere.

    The tenant filter already hides other schools' rows from the session, so this
    is belt-and-braces: it never *confirms* that a cross-school id exists.
    """
    if current_user.school_id is not None and school_id != current_user.school_id:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get the currently authenticated user's profile.
    """
    return current_user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """
    Create a new user (Admin only).

    A school admin's new user is stamped with the caller's school, so the account
    can never float outside a tenant. Platform roles are rejected at the door.
    """
    _reject_platform_roles(user_in.roles, current_user)
    return service.create_user(
        session=session, user_create=user_in, school_id=current_user.school_id
    )


@router.get("", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """
    List all users (Admin only). School-scoped: the tenant filter already narrows
    this to the caller's school.
    """
    return service.get_users(session=session, skip=skip, limit=limit)


@router.put("/{user_id}/roles", response_model=UserRead)
def update_user_roles(
    user_id: UUID,
    roles_in: list[RoleEnum],
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("roles.manage")),
):
    """Replace a user's roles.

    A person may hold several (principal **and** teacher, teacher **and**
    guardian). The first codename in the list becomes their primary role - the
    one whose dashboard opens at login - so the caller decides the default hat
    and the two can not disagree.
    """
    from app.domains.auth.roles import set_user_roles

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _require_same_school(target.school_id, current_user)
    _reject_platform_roles(roles_in, current_user)

    granted = set_user_roles(session, target, [role.value for role in roles_in])
    if not granted:
        raise HTTPException(status_code=400, detail="No valid roles supplied")
    return target


# A `POST /{parent_user_id}/assign-student/{student_id}` route used to live here. A
# guardian is a **person** now - their own `guardian` row, joined to each child
# through `student_guardian_relationship` - so linking one is the Students screen's
# job (`POST /students/{student_id}/guardians`, `academic/classroom/students/guardians.py`), where the
# phone/email rule ("one contact, one person") is applied. The route could not even
# build its row any more: `parent_user_id` is not a column, and nothing called it.


@router.post("/teachers/{teacher_id}/assign-class/{class_id}")
def assign_class_teacher(
    teacher_id: UUID,
    class_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """Assign a teacher as a class teacher.

    Assigning a class teacher is the Classroom screen's job now - it names the
    *section* (`PUT /classroom/sections/{section_id}/class-teacher`), which is the
    unit a class teacher actually runs. This route kept a class-wide assignment
    alive, and a class-wide row cannot say which section the person takes.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "Assign a class teacher through "
            "PUT /classroom/sections/{section_id}/class-teacher."
        ),
    )
