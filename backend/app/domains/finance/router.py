from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    FeeStructureCreate,
    FeeStructureRead,
    FeeTransactionCreate,
    FeeTransactionRead,
    StudentDuesResponse,
)

router = APIRouter()

AdminOrAccountant = RoleChecker(
    [RoleEnum.admin, RoleEnum.accountant, RoleEnum.director]
)


@router.get("/structures", response_model=list[FeeStructureRead])
def read_fee_structures(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(AdminOrAccountant),
):
    """
    List active fee structures.
    """
    return service.get_fee_structures(session=session, skip=skip, limit=limit)


@router.post(
    "/structures", response_model=FeeStructureRead, status_code=status.HTTP_201_CREATED
)
def create_fee_structure(
    structure_in: FeeStructureCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminOrAccountant),
):
    """
    Admin/Accountant creates a new fee rule.
    """
    return service.create_fee_structure(session=session, structure_in=structure_in)


@router.post(
    "/transactions",
    response_model=FeeTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_in: FeeTransactionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminOrAccountant),
):
    """
    Record a student's fee payment.
    """
    return service.create_transaction(session=session, transaction_in=transaction_in)


@router.get("/students/{student_id}/dues", response_model=StudentDuesResponse)
def get_student_dues(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(
        RoleChecker(
            [RoleEnum.admin, RoleEnum.accountant, RoleEnum.director, RoleEnum.principal]
        )
    ),
    # Could also allow parents/students to see their own dues
):
    """
    Calculates and returns the pending fee balance for a student.
    """
    return service.get_student_dues(session=session, student_id=student_id)
