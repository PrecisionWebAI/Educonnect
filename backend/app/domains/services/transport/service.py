"""Transport reads: the routes and the fleet, from real rows.

`/transport/routes` and `/transport/buses` used to answer with invented routes;
the tables (`transportroute`, `bus`) already hold what the board shows.
"""

from sqlmodel import Session, select

from .models import Bus as BusModel
from .models import TransportRoute as TransportRouteModel
from .schemas import Bus, TransportRoute


def list_transport_routes(session: Session) -> list[TransportRoute]:
    """Every route in the transport office's register."""
    return [
        TransportRoute(
            id=route.id,  # type: ignore[arg-type]
            name=route.name,
            busId=route.bus_id,
            driver=route.driver,
            stops=route.stops,
            students=route.students,
            status=route.status,
        )
        for route in session.exec(select(TransportRouteModel)).all()
    ]


def list_buses(session: Session) -> list[Bus]:
    """The fleet, with the seats currently taken."""
    return [
        Bus(
            id=bus.id,  # type: ignore[arg-type]
            name=bus.name,
            plate=bus.plate,
            route=bus.route,
            capacity=bus.capacity,
            occupied=bus.occupied,
            status=bus.status,
        )
        for bus in session.exec(select(BusModel)).all()
    ]
