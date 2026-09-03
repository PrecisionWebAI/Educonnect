from fastapi import HTTPException
from sqlmodel import Session

from app.domains.students import repository as student_repository

from . import repository
from .models import FeeStructure, FeeTransaction
from .schemas import FeeStructureCreate, FeeTransactionCreate, StudentDuesResponse


def get_fee_structures(
    session: Session, skip: int = 0, limit: int = 100
) -> list[FeeStructure]:
    return repository.get_fee_structures(session, skip=skip, limit=limit)


def create_fee_structure(
    session: Session, structure_in: FeeStructureCreate
) -> FeeStructure:
    return repository.create_fee_structure(session, structure_in)


def create_transaction(
    session: Session, transaction_in: FeeTransactionCreate
) -> FeeTransaction:
    # Verify student exists
    student = student_repository.get_student_by_id(session, transaction_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # We could also verify the fee structure exists

    return repository.create_transaction(session, transaction_in)


def get_student_dues(session: Session, student_id: int) -> StudentDuesResponse:
    student = student_repository.get_student_by_id(session, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    class_id = student.grade_class_id
    if not class_id:
        return StudentDuesResponse(
            student_id=student_id,
            total_applicable_fees=0.0,
            total_paid=0.0,
            pending_balance=0.0,
        )

    applicable_structures = repository.get_fee_structures_by_class(session, class_id)
    total_applicable_fees = sum(struct.amount for struct in applicable_structures)

    transactions = repository.get_transactions_by_student(session, student_id)
    total_paid = sum(tx.amount_paid for tx in transactions)

    pending_balance = total_applicable_fees - total_paid

    return StudentDuesResponse(
        student_id=student_id,
        total_applicable_fees=total_applicable_fees,
        total_paid=total_paid,
        pending_balance=pending_balance,
    )
