from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import NotificationItem

router = APIRouter()

_can_read = RequirePermission("messages.read")


@router.get("", response_model=list[NotificationItem])
def read_notifications(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """This person's notifications, newest first."""
    return service.list_notifications(session=session, user=current_user)


@router.post("/mark-read")
def mark_notifications_read(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Mark every unread notification for this person as read."""
    return service.mark_notifications_read(session=session, user=current_user)
