"""Staff salary service.

Payroll is a two-step state machine, and this is where it lives:

    Pending  --run payroll-->  Processing  --mark paid-->  Paid (+ paid_on)

`paid_on` is stamped by the server, never sent by the client, so a row can only
claim to be Paid with the date the server saw.

The register row stores only the money and `employee_id`; `read_payment` is what
turns it into the row the screen shows, reading the employee's code, name,
designation (their primary role) and department through that link.
"""

from datetime import date
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session

from app.domains.auth.roles import role_codenames
from app.domains.people.staff.models import Employee
from app.domains.admin.users.models import User

from . import repository
from .models import STATUS_PAID, STATUS_PROCESSING, SalaryPayment
from .schemas import PayrollRunResult, SalaryPaymentRead


def read_payment(session: Session, payment: SalaryPayment) -> SalaryPaymentRead:
    """One register row: stored money + the employee detail read through `employee_id`."""
    employee = session.get(Employee, payment.employee_id)
    user = session.get(User, employee.user_id) if employee else None
    roles = role_codenames(session, employee.user_id) if employee else []
    return SalaryPaymentRead(
        id=payment.id,
        employee_id=payment.employee_id,
        staff_code=employee.employee_code if employee else "",
        staff_name=user.full_name if user else "Staff",
        designation=roles[0] if roles else "",
        department=employee.department if employee else "",
        month=payment.month,
        gross=payment.gross,
        deductions=payment.deductions,
        net=payment.net,
        status=payment.status,
        paid_on=payment.paid_on,
    )


def list_register(
    session: Session, month: str | None = None
) -> list[SalaryPaymentRead]:
    return [
        read_payment(session, row) for row in repository.get_register(session, month)
    ]


def run_payroll(session: Session, month: str) -> PayrollRunResult:
    """Queues the month's still-Pending rows for processing."""
    rows = repository.get_pending(session, month)
    for row in rows:
        row.status = STATUS_PROCESSING
        session.add(row)
    session.commit()
    return PayrollRunResult(month=month, queued=len(rows))


def mark_paid(session: Session, payment_id: UUID) -> SalaryPaymentRead:
    payment = repository.get_payment(session, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Salary row not found")
    payment.status = STATUS_PAID
    payment.paid_on = date.today()
    return read_payment(session, repository.save_payment(session, payment))

