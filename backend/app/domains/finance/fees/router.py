from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission, get_current_active_user
from app.domains.auth.roles import has_role
from app.domains.auth.service import AuthorizationService

from . import service
from .schemas import (
    CollectionReportRowRead,
    FeeInvoiceRead,
    FeeTransactionCreate,
    FeeTransactionRead,
    PayrollEntryRead,
    SalaryStructureRowRead,
    StudentDuesResponse,
)

router = APIRouter()


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


def may_read_student_dues(session: Session, user, student_id: UUID) -> bool:
    """True for the office, or for the family the student belongs to.

    A **student** reads their own record; a **guardian** reads the children linked
    to their `guardian` person row (siblings share one); any other `fees.read`
    holder - the office - reads any student, because the permission itself is the
    gate there. Without this, every holder of `fees.read` (a parent included) could
    read any child's balance in the school.
    """
    from app.domains.academic.classroom.students.models import (
        Guardian,
        Student,
        StudentGuardianRelationship,
    )

    if not has_role(user, "student", "guardian"):
        return True
    student = session.get(Student, student_id)
    if student is None:
        return False
    if has_role(user, "student"):
        return student.user_id == user.id
    return (
        session.exec(
            select(StudentGuardianRelationship)
            .join(
                Guardian,
                Guardian.id == StudentGuardianRelationship.guardian_id,
            )
            .where(
                StudentGuardianRelationship.student_id == student_id,
                Guardian.user_id == user.id,
            )
        ).first()
        is not None
    )


@router.get("/students/{student_id}/dues", response_model=StudentDuesResponse)
def get_student_dues(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    """The pending fee balance for a student.

    A family reads **their own child** only (`may_read_student_dues`); the office
    reads any student, because `fees.read` is the gate there.
    """
    if not may_read_student_dues(session, current_user, student_id):
        raise HTTPException(status_code=403, detail="Not your child's record")
    return service.get_student_dues(session=session, student_id=student_id)


@router.get("/invoices", response_model=list[FeeInvoiceRead])
def read_invoices(
    student_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    from app.domains.academic.classroom.students.models import Student

    # A student only ever sees their own invoices.
    if has_role(current_user, "student") and student_id is None:
        profile = session.exec(
            select(Student).where(Student.user_id == current_user.id)
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
