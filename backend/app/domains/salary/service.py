"""Staff salary service.

Payroll is a two-step state machine, and this is where it lives:

    Pending  --run payroll-->  Processing  --mark paid-->  Paid (+ paid_on)

`paid_on` is stamped by the server, never sent by the client, so a row can only
claim to be Paid with the date the server saw.
"""

from datetime import date

from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import STATUS_PAID, STATUS_PROCESSING, SalaryPayment
from .schemas import PayrollRunResult, SalaryPaymentRead


def _read(payment: SalaryPayment) -> SalaryPaymentRead:
    return SalaryPaymentRead.model_validate(payment.model_dump())


def list_register(
    session: Session, month: str | None = None
) -> list[SalaryPaymentRead]:
    return [_read(row) for row in repository.get_register(session, month)]


def run_payroll(session: Session, month: str) -> PayrollRunResult:
    """Queues the month's still-Pending rows for processing."""
    rows = repository.get_pending(session, month)
    for row in rows:
        row.status = STATUS_PROCESSING
        session.add(row)
    session.commit()
    return PayrollRunResult(month=month, queued=len(rows))


def mark_paid(session: Session, payment_id: int) -> SalaryPaymentRead:
    payment = repository.get_payment(session, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Salary row not found")
    payment.status = STATUS_PAID
    payment.paid_on = date.today()
    return _read(repository.save_payment(session, payment))
