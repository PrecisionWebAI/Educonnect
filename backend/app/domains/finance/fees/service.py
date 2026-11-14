from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.students import repository as student_repository
from app.domains.operations.fees_structure import repository as fee_structures

from . import repository
from .models import FeeTransaction
from .schemas import (
    CollectionReportRowRead,
    FeeInvoiceRead,
    FeeTransactionCreate,
    PayrollEntryRead,
    SalaryStructureRowRead,
    StudentDuesResponse,
)


def create_transaction(
    session: Session, transaction_in: FeeTransactionCreate
) -> FeeTransaction:
    # Verify student exists
    student = student_repository.get_student_by_id(session, transaction_in.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # We could also verify the fee structure exists

    return repository.create_transaction(session, transaction_in)


def get_student_dues(session: Session, student_id: UUID) -> StudentDuesResponse:
    student = student_repository.get_student_by_id(session, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    section = (
        session.get(Classroom, student.classroom_id) if student.classroom_id else None
    )
    class_id = section.class_id if section else None
    if not class_id:
        return StudentDuesResponse(
            student_id=student_id,
            total_applicable_fees=0.0,
            total_paid=0.0,
            pending_balance=0.0,
        )

    applicable_structures = fee_structures.get_fee_structures_by_class(
        session, class_id
    )
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
# Real screens: invoices, collection reports and payroll all read the tables.
# ---------------------------------------------------------------------------


def _student_names(session: Session) -> dict[UUID, str]:
    """{Student.id: user.full_name} - one join, one query."""
    from sqlalchemy import func
    from sqlmodel import select

    from app.domains.academic.classroom.students.models import Student
    from app.domains.admin.users.models import User

    rows = session.exec(
        select(
            Student.id,
            func.coalesce(Student.full_name, User.full_name),
        ).join(User, User.id == Student.user_id, isouter=True)
    ).all()
    names: dict[UUID, str] = {}
    for sp_id, name in rows:
        names[sp_id] = name
    return names


def list_invoices(
    session: Session, student_id: UUID | None = None
) -> list[FeeInvoiceRead]:
    """One invoice per (student, applicable fee head); paid/due from real rows."""
    from collections import defaultdict

    from sqlmodel import select

    from app.domains.academic.classroom.students.models import Student

    from .schemas import FeeInvoiceRead

    structures = fee_structures.get_fee_structures(session, limit=1000)
    students = list(session.exec(select(Student)).all())
    if student_id:
        students = [s for s in students if s.id == student_id]

    names = _student_names(session)
    classroom_names = fee_structures.get_classroom_names(session)

    paid_by: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.00"))
    for tx in session.exec(select(FeeTransaction)).all():
        paid_by[(tx.student_id, tx.fee_structure_id)] += tx.amount_paid

    class_by_student: dict[UUID, UUID | None] = {}
    for student in students:
        section = (
            session.get(Classroom, student.classroom_id)
            if student.classroom_id
            else None
        )
        class_by_student[student.id] = section.class_id if section else None

    invoices: list[FeeInvoiceRead] = []
    for student in students:
        for structure in structures:
            if structure.class_id != class_by_student.get(student.id):
                continue
            paid = paid_by.get((student.id, structure.id), 0.0)
            due = max(0.0, structure.amount - paid)
            status = "Paid" if due <= 0 else ("Partial" if paid > 0 else "Due")
            invoices.append(
                FeeInvoiceRead(
                    id=f"{student.id}:{structure.id}",
                    student=names.get(student.id, f"Student {student.id}"),
                    className=classroom_names.get(
                        class_by_student.get(student.id), "—"
                    ),
                    head=structure.name,
                    amount=structure.amount,
                    paid=paid,
                    due=due,
                    status=status,
                )
            )
    return invoices


#: `salarypayment.status` -> the label the payroll screens show.
SALARY_STATUS_TO_PAYROLL = {
    "Pending": "Draft",
    "Processing": "Posted",
    "Paid": "Paid",
}


def list_salary_structure(session: Session) -> list[SalaryStructureRowRead]:
    """Payroll "Salary Structure" tab, from the real salary register.

    `salarypayment` stores gross/deductions/net (a register, not a component
    breakdown), so `basic` carries the gross and hra/da/special are 0 - no
    invented numbers. The staff code / name come from the employee the row
    points at, via the salary service.
    """
    from app.domains.operations.salary.service import list_register

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
        for row in list_register(session)
    ]


def list_payroll(session: Session) -> list[PayrollEntryRead]:
    """Payroll "Month Processing" / "Payslips" tabs, from the salary register."""
    from app.domains.operations.salary.service import list_register

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
        for row in list_register(session)
    ]


def list_collection_reports(session: Session) -> list[CollectionReportRowRead]:
    """Fee-collection summary computed from real fee rows.

    Periods are "Today", "This week" and "All time" over `feetransaction.date`;
    the mode line is the cash vs digital split of what was actually collected.
    """
    from datetime import date, timedelta

    from sqlmodel import select

    from .schemas import CollectionReportRowRead

    total_billed = sum(
        structure.amount
        for structure in fee_structures.get_fee_structures(session, limit=1000)
    )
    transactions = list(session.exec(select(FeeTransaction)).all())

    def _fmt(amount: Decimal | float) -> str:
        return f"₹{amount:,.0f}"

    def _row(row_id: str, period: str, since: date | None) -> CollectionReportRowRead:
        scoped = [tx for tx in transactions if since is None or tx.date >= since]
        collected = sum(tx.amount_paid for tx in scoped)
        cash = sum(tx.amount_paid for tx in scoped if tx.payment_mode.value == "cash")
        variance = (
            (collected - total_billed) / total_billed * 100 if total_billed else 0.0
        )
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
        _row("today", "Today", today),
        _row("this-week", "This week", today - timedelta(days=7)),
        _row("all-time", "All time", None),
    ]
