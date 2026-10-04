from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import PayrollRunRequest, PayrollRunResult, SalaryPaymentRead

router = APIRouter()

_can_read = RequirePermission("payroll.read")
_can_manage = RequirePermission("payroll.manage")


@router.get("/register", response_model=list[SalaryPaymentRead])
def read_register(
    month: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The salary register, optionally narrowed to one month ("Sep 2026")."""
    return service.list_register(session=session, month=month)


@router.post("/payroll/run", response_model=PayrollRunResult)
def run_payroll(
    run_in: PayrollRunRequest,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Queues every Pending row of `month` for processing."""
    return service.run_payroll(session=session, month=run_in.month)


@router.put("/register/{payment_id}/pay", response_model=SalaryPaymentRead)
def mark_paid(
    payment_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Marks one salary row Paid and stamps today's date on it."""
    return service.mark_paid(session=session, payment_id=payment_id)
