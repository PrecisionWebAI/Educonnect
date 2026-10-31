from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import StaffPerformance, TeacherCreate, TeacherRead, WorkloadMatrixRow

router = APIRouter()

# Remove AdminPrincipalDirector and LeadershipRoles


@router.get("", response_model=list[TeacherRead])
def read_teachers(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.read")),
):
    """
    List all teachers. Anyone authenticated can typically view the staff directory.
    """
    return service.get_teachers(session=session, skip=skip, limit=limit)


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    teacher_in: TeacherCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.create")),
):
    """
    Create a teacher profile. Admin/Principal/Director only.
    """
    return service.create_teacher(session=session, teacher_in=teacher_in)


@router.get("/workload", response_model=list[WorkloadMatrixRow])
def read_workload_matrix(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.view_workload")),
):
    return service.workload_matrix(session=session)


@router.get("/performance", response_model=list[StaffPerformance])
def read_staff_performance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.view_workload")),
):
    return service.staff_performance(session=session)


@router.get("/{teacher_id}", response_model=TeacherRead)
def read_teacher(
    teacher_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.read")),
):
    """
    Get a specific teacher profile.
    """
    return service.get_teacher(session=session, teacher_id=teacher_id)
