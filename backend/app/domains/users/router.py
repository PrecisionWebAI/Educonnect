from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission, get_current_active_user

from . import service
from .models import RoleEnum, User, UserCreate, UserRead

router = APIRouter()


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
    """
    return service.create_user(session=session, user_create=user_in)


@router.get("", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """
    List all users (Admin only).
    """
    return service.get_users(session=session, skip=skip, limit=limit)


@router.put("/{user_id}/roles", response_model=UserRead)
def update_user_roles(
    user_id: int,
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
    from fastapi import HTTPException

    from app.domains.auth.roles import set_user_roles

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    granted = set_user_roles(session, user, [role.value for role in roles_in])
    if not granted:
        raise HTTPException(status_code=400, detail="No valid roles supplied")
    return user


@router.post("/{parent_user_id}/assign-student/{student_id}")
def assign_parent_to_student(
    parent_user_id: int,
    student_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """
    Assign a parent user to a student profile.
    """
    from app.domains.students.models import StudentParentRelationship

    rel = StudentParentRelationship(
        student_id=student_id,
        parent_user_id=parent_user_id,
        relationship_type="Guardian",
    )
    session.add(rel)
    session.commit()
    return {"status": "success"}


@router.post("/teachers/{teacher_id}/assign-class/{class_id}")
def assign_class_teacher(
    teacher_id: int,
    class_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(RequirePermission("users.manage")),
):
    """
    Assign a teacher as a class teacher.
    """
    from app.domains.teachers.models import ClassTeacherAssignment

    assignment = ClassTeacherAssignment(
        teacher_id=teacher_id, classroom_id=class_id, academic_year_id=1
    )
    session.add(assignment)
    session.commit()
    return {"status": "success"}
