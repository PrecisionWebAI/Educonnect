from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission, get_current_active_user
from app.domains.auth.roles import has_role
from app.domains.auth.service import AuthorizationService

from . import service
from .schemas import (
    CollectionReportRowRead,
    FeeInvoiceRead,
    FeeStructureCreate,
    FeeStructureRead,
    FeeStructureRowCreate,
    FeeStructureRowRead,
    FeeStructureRowUpdate,
    FeeStructureStatusUpdate,
    FeeTransactionCreate,
    FeeTransactionRead,
    PayrollEntryRead,
    SalaryStructureRowRead,
    StudentDuesResponse,
)

router = APIRouter()

# Removed RoleCheckers


@router.get("/structures", response_model=list[FeeStructureRead])
def read_fee_structures(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
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
    current_user=Depends(RequirePermission("fees.manage_structure")),
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
    current_user=Depends(RequirePermission("fees.create")),
):
    """
    Record a student's fee payment.
    """
    return service.create_transaction(session=session, transaction_in=transaction_in)


@router.get("/students/{student_id}/dues", response_model=StudentDuesResponse)
def get_student_dues(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
    # Could also allow parents/students to see their own dues
):
    """
    Calculates and returns the pending fee balance for a student.
    """
    return service.get_student_dues(session=session, student_id=student_id)


@router.get("/invoices", response_model=list[FeeInvoiceRead])
def read_invoices(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    from sqlmodel import select

    from app.domains.students.models import StudentProfile

    # A student only ever sees their own invoices.
    if has_role(current_user, "student") and student_id is None:
        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        ).first()
        if profile:
            student_id = profile.id

    return service.list_invoices(session=session, student_id=student_id)


@router.get("/collection-reports", response_model=list[CollectionReportRowRead])
def read_collection_reports(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    return service.list_collection_reports(session=session)


@router.get("/salary-structure", response_model=list[SalaryStructureRowRead])
def read_salary_structure(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    if not (
        AuthorizationService.can(current_user, "payroll.read", session=session)
        or AuthorizationService.can(current_user, "payroll.view_payslip", session=session)
    ):
        raise HTTPException(status_code=403, detail="Missing required permission")
    return service.list_salary_structure(session=session)


@router.get("/payroll", response_model=list[PayrollEntryRead])
def read_payroll(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    if not (
        AuthorizationService.can(current_user, "payroll.read", session=session)
        or AuthorizationService.can(current_user, "payroll.view_payslip", session=session)
    ):
        raise HTTPException(status_code=403, detail="Missing required permission")
    return service.list_payroll(session=session)


# ---------------------------------------------------------------------------
# Fee-structure master (Operations > Fees Structure)
# ---------------------------------------------------------------------------


@router.get("/fee-structures", response_model=list[FeeStructureRowRead])
def read_fee_structure_rows(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    """The class-wise fee card, with live student counts per class."""
    return service.list_fee_structure_rows(session=session)


@router.post("/fee-structures", response_model=FeeStructureRowRead, status_code=201)
def create_fee_structure_row(
    structure_in: FeeStructureRowCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.manage_structure")),
):
    """Adds a fee head; it stays a Draft until the office publishes it."""
    return service.create_fee_structure_row(session=session, structure_in=structure_in)


@router.put("/fee-structures/{structure_id}", response_model=FeeStructureRowRead)
def update_fee_structure_row(
    structure_id: int,
    structure_in: FeeStructureRowUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.manage_structure")),
):
    """Edits a fee head's wording, class, frequency, amount or due day."""
    return service.update_fee_structure_row(
        session=session, structure_id=structure_id, structure_in=structure_in
    )


@router.put("/fee-structures/{structure_id}/status", response_model=FeeStructureRowRead)
def set_fee_structure_status(
    structure_id: int,
    status_in: FeeStructureStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.manage_structure")),
):
    """Publishes or unpublishes a fee head."""
    return service.set_fee_structure_status(
        session=session, structure_id=structure_id, status_in=status_in
    )
