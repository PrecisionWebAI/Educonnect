"""Tickets reads: the help desk queue, from real rows.

`/tickets` used to answer with invented tickets; the `supportticket` table already
holds them, so this joins the reporter's name and orders by the last change.
"""

from sqlmodel import Session, select

from app.core.formatting import stamp
from app.domains.admin.users.models import User

from .models import SupportTicket
from .schemas import TicketItem


def list_tickets(session: Session) -> list[TicketItem]:
    """Every ticket, most recently updated first."""
    statement = select(SupportTicket).order_by(SupportTicket.updated_at.desc())  # type: ignore[attr-defined]
    items: list[TicketItem] = []
    for ticket in session.exec(statement).all():
        user = session.get(User, ticket.reporter_user_id)
        items.append(
            TicketItem(
                id=ticket.id,  # type: ignore[arg-type]
                subject=ticket.subject,
                category=ticket.category,
                priority=ticket.priority,
                status=ticket.status,
                reporter=user.full_name if user else "",
                assignee=ticket.assignee or "",
                updated=stamp(ticket.updated_at),
            )
        )
    return items
