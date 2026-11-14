"""One row: this person, this day, what the office recorded.

The status is kept as **text**, like `staffduty.duty_type`, because it is a fixed
vocabulary (`labels.ATTENDANCE_STATUSES`) and not a state machine: adding a word a
school asks for is a one-line change in `labels`, not a migration of every row.

`on_leave` is deliberately not a value this column may hold - it is derived from
`leaverequest` (see `__init__.py`), so a leave that is cancelled cannot leave a
stale "On Leave" row behind.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class StaffAttendanceBase(SQLModel):
    """What the register records about one person on one day."""

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    #: The day being marked. A register is dated, never "current".
    date: date
    #: `labels.ATTENDANCE_STATUSES` - `present` / `absent` / `half_day`.
    status: str
    #: The office's own words ("medical", "arrived after the assembly").
    remarks: str | None = None


class StaffAttendanceRecord(StaffAttendanceBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, employee_id, date)` - one row per person per day.

    Unlike `staffduty`, every column in this key is NOT NULL, so PostgreSQL
    actually enforces it: the bulk upsert (`service.mark_bulk`) updates the row it
    finds instead of inserting a second one, and this constraint is the backstop
    for two callers marking the same day at the same moment.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "employee_id",
            "date",
            name="uq_staffattendancerecord_employee_date",
        ),
    )

    #: Who marked it. NULL when a migration or the seed wrote the row.
    marked_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)
    #: Moves when a marked day is amended - the audit row says what it was before.
    updated_at: datetime = Field(default_factory=utcnow)
