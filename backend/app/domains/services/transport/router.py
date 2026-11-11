from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import Bus, TransportRoute

router = APIRouter()

_can_read = RequirePermission("transport.read")


@router.get("/routes", response_model=list[TransportRoute])
def read_transport_routes(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every route the school runs, with its bus, driver and stop count."""
    return service.list_transport_routes(session=session)


@router.get("/buses", response_model=list[Bus])
def read_buses(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The fleet: plate, route, capacity and seats taken."""
    return service.list_buses(session=session)
