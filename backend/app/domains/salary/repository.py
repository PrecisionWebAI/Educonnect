"""Database access for the salary register."""

from sqlmodel import Session, select

from .models import STATUS_PENDING, SalaryPayment


def get_register(session: Session, month: str | None = None) -> list[SalaryPayment]:
    """Rows in insertion order.

    The seed inserts the newest month first, so "insertion order" is also
    "Sep 2026, Aug 2026, Jul 2026" - the order the register's month dropdown
    shows - without needing to parse the month labels for sorting.
    """
    query = select(SalaryPayment)
    if month:
        query = query.where(SalaryPayment.month == month)
    return list(session.exec(query.order_by(SalaryPayment.id)).all())


def get_payment(session: Session, payment_id: int) -> SalaryPayment | None:
    return session.get(SalaryPayment, payment_id)


def get_pending(session: Session, month: str) -> list[SalaryPayment]:
    """The rows a payroll run has to pick up for `month`."""
    return list(
        session.exec(
            select(SalaryPayment)
            .where(SalaryPayment.month == month)
            .where(SalaryPayment.status == STATUS_PENDING)
            .order_by(SalaryPayment.id)
        ).all()
    )


def save_payment(session: Session, payment: SalaryPayment) -> SalaryPayment:
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment
