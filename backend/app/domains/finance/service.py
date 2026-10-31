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


# ---------------------------------------------------------------------------
# Real screens: invoices, collection reports and payroll all read the tables.
# ---------------------------------------------------------------------------


def _student_names(session: Session) -> dict[int, str]:
    """{studentprofile.id: user.full_name} - one join, one query."""
    from sqlmodel import select

    from app.domains.students.models import StudentProfile
    from app.domains.users.models import User

    rows = session.exec(
        select(StudentProfile.id, User.full_name).join(
            User, User.id == StudentProfile.user_id
        )
    ).all()
    return {int(sp_id): name for sp_id, name in rows}


def list_invoices(
    session: Session, student_id: int | None = None
) -> list["FeeInvoiceRead"]:
    """One invoice per (student, applicable fee head); paid/due from real rows."""
    from collections import defaultdict

    from sqlmodel import select

    from app.domains.students.models import StudentProfile

    from .schemas import FeeInvoiceRead

    structures = repository.get_fee_structures(session, limit=1000)
    students = list(session.exec(select(StudentProfile)).all())
    if student_id:
        students = [s for s in students if s.id == student_id]

    names = _student_names(session)
    classroom_names = repository.get_classroom_names(session)

    paid_by: dict[tuple[int, int], float] = defaultdict(float)
    for tx in session.exec(select(FeeTransaction)).all():
        paid_by[(tx.student_id, tx.fee_structure_id)] += tx.amount_paid

    invoices: list[FeeInvoiceRead] = []
    next_id = 1
    for student in students:
        for structure in structures:
            if structure.classroom_id != student.classroom_id:
                continue
            paid = paid_by.get((student.id, structure.id), 0.0)
            due = max(0.0, structure.amount - paid)
            status = "Paid" if due <= 0 else ("Partial" if paid > 0 else "Due")
            invoices.append(
                FeeInvoiceRead(
                    id=next_id,
                    student=names.get(student.id, f"Student {student.id}"),
                    className=classroom_names.get(student.classroom_id or 0, "—"),
                    head=structure.name,
                    amount=structure.amount,
                    paid=paid,
                    due=due,
                    status=status,
                )
            )
            next_id += 1
    return invoices


def _salary_rows(session: Session) -> list["SalaryPayment"]:
    from sqlmodel import select

    from app.domains.salary.models import SalaryPayment

    return list(session.exec(select(SalaryPayment).order_by(SalaryPayment.id)).all())


#: `salarypayment.status` -> the label the payroll screens show.
SALARY_STATUS_TO_PAYROLL = {
    "Pending": "Draft",
    "Processing": "Posted",
    "Paid": "Paid",
}


def list_salary_structure(session: Session) -> list["SalaryStructureRowRead"]:
    """Payroll "Salary Structure" tab, from the real salary register.

    `salarypayment` stores gross/deductions/net (a register, not a component
    breakdown), so `basic` carries the gross and hra/da/special are 0 - no
    invented numbers.
    """
    from .schemas import SalaryStructureRowRead

    return [
        SalaryStructureRowRead(
            id=row.id,
            staffCode=row.staff_code,
            name=row.staff_name,
            basic=row.gross,
            hra=0.0,
            da=0.0,
            special=0.0,
            total=row.gross,
        )
        for row in _salary_rows(session)
    ]


def list_payroll(session: Session) -> list["PayrollEntryRead"]:
    """Payroll "Month Processing" / "Payslips" tabs, from the salary register."""
    from .schemas import PayrollEntryRead

    return [
        PayrollEntryRead(
            id=row.id,
            staffCode=row.staff_code,
            name=row.staff_name,
            basic=row.gross,
            allowances=0.0,
            deductions=row.deductions,
            net=row.net,
            status=SALARY_STATUS_TO_PAYROLL.get(row.status, row.status),
        )
        for row in _salary_rows(session)
    ]


def list_collection_reports(session: Session) -> list["CollectionReportRowRead"]:
    """Fee-collection summary computed from real fee rows.

    Periods are "Today", "This week" and "All time" over `feetransaction.date`;
    the mode line is the cash vs digital split of what was actually collected.
    """
    from datetime import date, timedelta

    from sqlmodel import select

    from .schemas import CollectionReportRowRead

    total_billed = sum(
        structure.amount for structure in repository.get_fee_structures(session, limit=1000)
    )
    transactions = list(session.exec(select(FeeTransaction)).all())

    def _fmt(amount: float) -> str:
        return f"₹{amount:,.0f}"

    def _row(row_id: int, period: str, since: date | None) -> CollectionReportRowRead:
        scoped = [tx for tx in transactions if since is None or tx.date >= since]
        collected = sum(tx.amount_paid for tx in scoped)
        cash = sum(tx.amount_paid for tx in scoped if tx.payment_mode.value == "cash")
        variance = (collected - total_billed) / total_billed * 100 if total_billed else 0.0
        cash_pct = round(cash / collected * 100) if collected else 0
        return CollectionReportRowRead(
            id=row_id,
            period=period,
            billed=_fmt(total_billed),
            collected=_fmt(collected),
            variance=f"{variance:+.0f}%",
            mode=f"Cash {cash_pct}% / Digital {100 - cash_pct}%",
        )

    today = date.today()
    return [
        _row(1, "Today", today),
        _row(2, "This week", today - timedelta(days=7)),
        _row(3, "All time", None),
    ]
