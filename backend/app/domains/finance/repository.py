from sqlmodel import Session, func, select

from app.domains.academics.models import GradeClass
from app.domains.students.models import StudentProfile

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


def get_grade_class(session: Session, class_name: str) -> GradeClass | None:
    """Resolve a class the UI sent ("Grade 6", "Class 6", "6") to `gradeclass`.

    The name match is tried first because that is the stored truth; the level
    fallback keeps older wording ("Class 6") working, since the label the form
    offers and the label the school typed do not have to match forever.
    """
    cleaned = (class_name or "").strip()
    if not cleaned:
        return None
    grade = session.exec(
        select(GradeClass).where(func.lower(GradeClass.name) == cleaned.lower())
    ).first()
    if grade is not None:
        return grade
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    return session.exec(
        select(GradeClass).where(GradeClass.level == int(digits))
    ).first()


def get_grade_class_names(session: Session) -> dict[int, str]:
    """{grade_class_id: name} - one query for the whole fee list."""
    return {
        grade.id: grade.name
        for grade in session.exec(select(GradeClass)).all()
        if grade.id is not None
    }


def count_students_by_grade(session: Session) -> dict[int, int]:
    """{grade_class_id: students} - powers the "Students" column."""
    rows = session.exec(
        select(StudentProfile.grade_class_id, func.count()).group_by(
            StudentProfile.grade_class_id
        )
    ).all()
    return {
        int(grade_id): int(count) for grade_id, count in rows if grade_id is not None
    }
