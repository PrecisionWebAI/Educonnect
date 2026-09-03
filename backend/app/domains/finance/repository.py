from sqlmodel import Session, select

from .models import FeeStructure, FeeTransaction
from .schemas import FeeStructureCreate, FeeTransactionCreate


def get_fee_structures(
    session: Session, skip: int = 0, limit: int = 100
) -> list[FeeStructure]:
    return list(session.exec(select(FeeStructure).offset(skip).limit(limit)).all())


def get_fee_structures_by_class(session: Session, class_id: int) -> list[FeeStructure]:
    statement = select(FeeStructure).where(FeeStructure.grade_class_id == class_id)
    return list(session.exec(statement).all())


def create_fee_structure(
    session: Session, structure_in: FeeStructureCreate
) -> FeeStructure:
    db_structure = FeeStructure.model_validate(structure_in)
    session.add(db_structure)
    session.commit()
    session.refresh(db_structure)
    return db_structure


def get_transactions_by_student(
    session: Session, student_id: int
) -> list[FeeTransaction]:
    statement = select(FeeTransaction).where(FeeTransaction.student_id == student_id)
    return list(session.exec(statement).all())


def create_transaction(
    session: Session, transaction_in: FeeTransactionCreate
) -> FeeTransaction:
    db_transaction = FeeTransaction.model_validate(transaction_in)
    session.add(db_transaction)
    session.commit()
    session.refresh(db_transaction)
    return db_transaction
