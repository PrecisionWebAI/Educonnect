from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import MeetingItem

router = APIRouter()

_can_read = RequirePermission("ptm.read")


@router.get("", response_model=list[MeetingItem])
def read_meetings(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The meeting calendar, soonest first."""
    return service.list_meetings(session=session)
