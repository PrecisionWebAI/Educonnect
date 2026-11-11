from uuid import UUID
from sqlmodel import Session, select

from .models import FeeTransaction
from .schemas import FeeTransactionCreate


def get_transactions_by_student(
    session: Session, student_id: UUID
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


def get_fee_structure(session: Session, structure_id: UUID) -> FeeStructure | None:
    return session.get(FeeStructure, structure_id)


def save_fee_structure(session: Session, structure: FeeStructure) -> FeeStructure:
    session.add(structure)
    session.commit()
    session.refresh(structure)
    return structure


def get_classroom(session: Session, class_name: str) -> Classroom | None:
    """Resolve a class the UI sent ("Class 6", "Grade 6", "6") to `classroom`.

    One implementation, in the academics domain that owns the vocabulary, so the
    fee card and the admission form resolve a class the same way.
    """
    return find_classroom(session, class_name)


def get_classroom_names(session: Session) -> dict[UUID, str]:
    """{class_id: class name} - one query for the whole fee list.

    The class is a `classname` catalog row now, so the fee list names it by that
    id: a fee head filed against "Class 10" shows the catalog's wording.
    """
    return {
        classroom.class_id: classroom.classname
        for classroom in session.exec(select(ClassName)).all()
        if classroom.class_id is not None
    }


def count_students_by_class(session: Session) -> dict[UUID, int]:
    """{classroom_id: students} - powers the "Students" column.

    The class is read through the student's section, so there is no class id
    stored on the student row to drift out of step. `select_from` is spelled out
    because the selected column belongs to the *joined* table - without it
    SQLAlchemy would take `section` as the FROM and join it to itself.
    """
    from app.domains.academic.classroom.academics.models import Section

    rows = session.exec(
        select(Classroom.class_id, func.count())
        .select_from(Student)
        .join(Classroom, Classroom.id == Student.classroom_id)
        .group_by(Classroom.class_id)
    ).all()
    return {
        classroom_id: int(count)
        for classroom_id, count in rows
        if classroom_id is not None
    }
