"""Transport tables: the routes a bus runs and the buses themselves.

Tenant-scoped (`TenantMixin`) like every other school-owned table. `bus_id` on a
route is the fleet's own code ("B-01") rather than a foreign key, because the
transport office names buses by plate/code on the board it keeps.
"""

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class TransportRouteBase(SQLModel):
    name: str
    bus_id: str  # "B-01"
    driver: str
    stops: int = 0
    students: int = 0
    status: str = "Active"


class TransportRoute(TransportRouteBase, TenantMixin, UUIDMixin, table=True):
    pass


class BusBase(SQLModel):
    name: str
    plate: str
    route: str
    capacity: int = 0
    occupied: int = 0
    status: str = "Parked"


class Bus(BusBase, TenantMixin, UUIDMixin, table=True):
    pass
