from fastapi import HTTPException
from sqlmodel import Session

from app.domains.academics.models import Classroom
from app.domains.students import repository as student_repository

from . import repository
from .models import FeeFrequency, FeeStructure, FeeTransaction
from .schemas import (
    FeeStructureCreate,
    FeeStructureRowCreate,
    FeeStructureRowRead,
    FeeStructureRowUpdate,
    FeeStructureStatusUpdate,
    FeeTransactionCreate,
    StudentDuesResponse,
)


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

    class_id = student.classroom_id
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


# ---------------------------------------------------------------------------
# Fee-structure master (Operations > Fees Structure)
# ---------------------------------------------------------------------------

#: `feefrequency` enum value -> the label the fee card shows.
FREQUENCY_LABELS: dict[FeeFrequency, str] = {
    FeeFrequency.monthly: "Monthly",
    FeeFrequency.term: "Term",
    FeeFrequency.yearly: "Yearly",
    FeeFrequency.one_time: "One-time",
}
FREQUENCY_VALUES: dict[str, FeeFrequency] = {
    label: value for value, label in FREQUENCY_LABELS.items()
}


def _require_classroom(session: Session, class_name: str) -> Classroom:
    classroom = repository.get_classroom(session, class_name)
    if classroom is None:
        raise HTTPException(status_code=422, detail=f"Unknown class '{class_name}'")
    return classroom


def _require_frequency(label: str) -> FeeFrequency:
    frequency = FREQUENCY_VALUES.get((label or "").strip())
    if frequency is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown frequency '{label}'. Expected one of: "
            f"{', '.join(FREQUENCY_VALUES)}",
        )
    return frequency


def _structure_row(
    structure: FeeStructure,
    classroom_names: dict[int, str],
    student_counts: dict[int, int],
) -> FeeStructureRowRead:
    return FeeStructureRowRead(
        id=structure.id,
        head=structure.name,
        class_name=classroom_names.get(structure.classroom_id, "—"),
        frequency=FREQUENCY_LABELS.get(structure.frequency, str(structure.frequency)),
        amount=structure.amount,
        due_day=structure.due_day or "—",
        students=student_counts.get(structure.classroom_id, 0),
        status=structure.status,
    )


def _structure_maps(session: Session) -> tuple[dict[int, str], dict[int, int]]:
    return (
        repository.get_classroom_names(session),
        repository.count_students_by_class(session),
    )


def list_fee_structure_rows(session: Session) -> list[FeeStructureRowRead]:
    """The fee card: class names, live student counts and the publish state."""
    classroom_names, student_counts = _structure_maps(session)
    structures = repository.get_fee_structures(session, limit=1000)
    return [_structure_row(s, classroom_names, student_counts) for s in structures]


def create_fee_structure_row(
    session: Session, structure_in: FeeStructureRowCreate
) -> FeeStructureRowRead:
    """Adds a fee head as a draft; the office publishes it when it is ready."""
    classroom = _require_classroom(session, structure_in.class_name)
    structure = repository.create_fee_structure(
        session,
        FeeStructureCreate(
            name=structure_in.head.strip(),
            amount=structure_in.amount,
            classroom_id=classroom.id,
            frequency=_require_frequency(structure_in.frequency),
            due_day=structure_in.due_day or None,
            status="Draft",
        ),
    )
    classroom_names, student_counts = _structure_maps(session)
    return _structure_row(structure, classroom_names, student_counts)


def update_fee_structure_row(
    session: Session, structure_id: int, structure_in: FeeStructureRowUpdate
) -> FeeStructureRowRead:
    structure = repository.get_fee_structure(session, structure_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Fee head not found")

    classroom = _require_classroom(session, structure_in.class_name)
    structure.name = structure_in.head.strip()
    structure.amount = structure_in.amount
    structure.classroom_id = classroom.id
    structure.frequency = _require_frequency(structure_in.frequency)
    structure.due_day = structure_in.due_day or None

    classroom_names, student_counts = _structure_maps(session)
    return _structure_row(
        repository.save_fee_structure(session, structure),
        classroom_names,
        student_counts,
    )


def set_fee_structure_status(
    session: Session, structure_id: int, status_in: FeeStructureStatusUpdate
) -> FeeStructureRowRead:
    """Publish / unpublish a fee head."""
    structure = repository.get_fee_structure(session, structure_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Fee head not found")
    structure.status = status_in.status
    classroom_names, student_counts = _structure_maps(session)
    return _structure_row(
        repository.save_fee_structure(session, structure),
        classroom_names,
        student_counts,
    )
