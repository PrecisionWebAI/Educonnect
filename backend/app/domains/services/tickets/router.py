from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import TicketItem

router = APIRouter()

# A ticket is a message to the help desk, so the queue is read with the messaging
# permission the nav entry already asks for.
_can_read = RequirePermission("messages.read")


@router.get("", response_model=list[TicketItem])
def read_tickets(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The help desk queue, most recently updated first."""
    return service.list_tickets(session=session)
