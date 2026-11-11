from uuid import UUID

from pydantic import BaseModel


class LeaveApplicationItem(BaseModel):
    id: UUID
    student: str
    className: str
    type: str
    from_date: str
    to_date: str
    reason: str
    days: int
    status: str
    submittedAt: str


class StaffLeaveRow(BaseModel):
    id: UUID
    name: str
    role: str
    type: str
    from_date: str
    days: int
    balance: int
    status: str
