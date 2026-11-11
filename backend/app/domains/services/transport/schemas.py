from uuid import UUID

from pydantic import BaseModel


class TransportRoute(BaseModel):
    id: UUID
    name: str
    busId: str
    driver: str
    stops: int
    students: int
    status: str


class Bus(BaseModel):
    id: UUID
    name: str
    plate: str
    route: str
    capacity: int
    occupied: int
    status: str
