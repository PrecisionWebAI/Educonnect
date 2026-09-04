from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import StaffPerformance, TeacherCreate, TeacherRead, WorkloadMatrixRow

router = APIRouter()

# Admin, Principal, or Director might manage teachers
AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)


@router.get("", response_model=list[TeacherRead])
def read_teachers(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    """
    List all teachers. Anyone authenticated can typically view the staff directory.
    """
    return service.get_teachers(session=session, skip=skip, limit=limit)


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    teacher_in: TeacherCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Create a teacher profile. Admin/Principal/Director only.
    """
    return service.create_teacher(session=session, teacher_in=teacher_in)


@router.get("/workload", response_model=list[WorkloadMatrixRow])
def read_workload_matrix(session: Session = Depends(get_session)):
    return [
        WorkloadMatrixRow(
            staff="P. Menon",
            subject="Physics",
            classes=["10-A", "10-B", "9-A"],
            periods=18,
            utilisation=82,
        ),
        WorkloadMatrixRow(
            staff="M. Iyer",
            subject="Mathematics",
            classes=["10-A", "11-A"],
            periods=16,
            utilisation=74,
        ),
        WorkloadMatrixRow(
            staff="S. Kapoor",
            subject="English",
            classes=["9-A", "9-B", "10-A"],
            periods=20,
            utilisation=91,
        ),
        WorkloadMatrixRow(
            staff="R. Verma",
            subject="History",
            classes=["8-A", "8-B"],
            periods=14,
            utilisation=64,
        ),
        WorkloadMatrixRow(
            staff="K. Nair",
            subject="Computer Science",
            classes=["12-A", "11-A"],
            periods=15,
            utilisation=70,
        ),
        WorkloadMatrixRow(
            staff="D. Singh",
            subject="Physical Education",
            classes=["All"],
            periods=22,
            utilisation=95,
        ),
    ]


@router.get("/performance", response_model=list[StaffPerformance])
def read_staff_performance(session: Session = Depends(get_session)):
    return [
        StaffPerformance(
            id=1, staff="P. Menon", rating=4.6, reviews=12, trend="up", score=88
        ),
        StaffPerformance(
            id=2, staff="M. Iyer", rating=4.4, reviews=10, trend="up", score=84
        ),
        StaffPerformance(
            id=3, staff="S. Kapoor", rating=4.8, reviews=15, trend="up", score=92
        ),
        StaffPerformance(
            id=4, staff="R. Verma", rating=4.1, reviews=8, trend="flat", score=76
        ),
        StaffPerformance(
            id=5, staff="K. Nair", rating=4.3, reviews=9, trend="flat", score=80
        ),
        StaffPerformance(
            id=6, staff="D. Singh", rating=4.7, reviews=11, trend="up", score=90
        ),
    ]


@router.get("/{teacher_id}", response_model=TeacherRead)
def read_teacher(teacher_id: int, session: Session = Depends(get_session)):
    """
    Get a specific teacher profile.
    """
    return service.get_teacher(session=session, teacher_id=teacher_id)
