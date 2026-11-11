"""The one leave table behind both leave screens.

A student leave and a staff leave are the same request -> approve/reject flow, so
they share `leaverequest`: `student_id` is set for a student and NULL for a staff
member. `leave_type` and `status` are plain text because the screen shows the words
that were chosen ("Medical", "Pending") rather than mapping enum names.

Tenant-scoped (`TenantMixin`) like every other school-owned table.
"""

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class LeaveRequestBase(SQLModel):
    #: Set for a student leave, NULL for a staff leave.
    student_id: UUID | None = Field(default=None, foreign_key="student.id")
    #: The person who filed it (the guardian/student for a student leave, the
    #: staff member for a staff leave).
    requester_user_id: UUID = Field(foreign_key="user.id")
    leave_type: str  # "Medical" / "Personal" / "Casual" / "Sick" / "Earned" / "OD"
    from_date: date
    to_date: date
    days: int
    reason: str | None = None
    status: str = Field(default="Pending")  # "Pending" / "Approved" / "Rejected"


class LeaveRequest(LeaveRequestBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
