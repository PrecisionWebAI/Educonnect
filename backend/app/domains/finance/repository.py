from sqlmodel import Session, func, select

from app.domains.academics.models import Classroom
from app.domains.students.models import StudentProfile

from .models import FeeStructure, FeeTransaction
from .schemas import FeeStructureCreate, FeeTransactionCreate


def get_fee_structures(
    session: Session, skip: int = 0, limit: int = 100
) -> list[FeeStructure]:
    return list(session.exec(select(FeeStructure).offset(skip).limit(limit)).all())


def get_fee_structures_by_class(session: Session, class_id: int) -> list[FeeStructure]:
    statement = select(FeeStructure).where(FeeStructure.classroom_id == class_id)
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


# ---------------------------------------------------------------------------
# Fee-structure master (Operations > Fees Structure)
# ---------------------------------------------------------------------------


def get_fee_structure(session: Session, structure_id: int) -> FeeStructure | None:
    return session.get(FeeStructure, structure_id)


def save_fee_structure(session: Session, structure: FeeStructure) -> FeeStructure:
    session.add(structure)
    session.commit()
    session.refresh(structure)
    return structure


def get_classroom(session: Session, class_name: str) -> Classroom | None:
    """Resolve a class the UI sent ("Class 6", "Grade 6", "6") to `classroom`.

    The exact name is tried first because that is the stored truth. The number
    fallback mends older wording: "Grade 6" and a bare "6" both resolve to the
    class called "Class 6", so fee rows written before the vocabulary moved from
    grades to classes still point at the right class.
    """
    cleaned = (class_name or "").strip()
    if not cleaned:
        return None
    classroom = session.exec(
        select(Classroom).where(func.lower(Classroom.name) == cleaned.lower())
    ).first()
    if classroom is not None:
        return classroom
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    return session.exec(
        select(Classroom).where(Classroom.name == f"Class {int(digits)}")
    ).first()


def get_classroom_names(session: Session) -> dict[int, str]:
    """{classroom_id: name} - one query for the whole fee list."""
    return {
        classroom.id: classroom.name
        for classroom in session.exec(select(Classroom)).all()
        if classroom.id is not None
    }


def count_students_by_class(session: Session) -> dict[int, int]:
    """{classroom_id: students} - powers the "Students" column."""
    rows = session.exec(
        select(StudentProfile.classroom_id, func.count()).group_by(
            StudentProfile.classroom_id
        )
    ).all()
    return {
        int(classroom_id): int(count)
        for classroom_id, count in rows
        if classroom_id is not None
    }
