"""One row: this person, this day, what the office recorded.

The status is kept as **text**, like `staffduty.duty_type`, because it is a fixed
vocabulary (`labels.ATTENDANCE_STATUSES`) and not a state machine: adding a word a
school asks for is a one-line change in `labels`, not a migration of every row.

`on_leave` is deliberately not a value this column may hold - it is derived from
`leaverequest` (see `__init__.py`), so a leave that is cancelled cannot leave a
stale "On Leave" row behind.
"""

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import CheckConstraint, UniqueConstraint
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
    #: When the person actually clocked in and out (Phase 2). NULL means nobody
    #: recorded a time - the register then reports the status alone instead of
    #: inventing a 09:00 that was never taken. `time` and not a datetime: the day is
    #: already the `date` column, and a second copy of it could disagree.
    check_in_time: time | None = None
    check_out_time: time | None = None
    #: The approved leave this absence is explained by, when it is (Phase 2). Set for
    #: a `half_day`/`absent` row the office tied to a request; the register still
    #: derives `On Leave` from `leaverequest`, so this link is for the trail, not the
    #: display. NULL on a normal working day.
    leave_request_id: UUID | None = Field(
        default=None, foreign_key="leaverequest.id", index=True
    )


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
        #: The vocabulary in `labels.ATTENDANCE_STATUSES`. `on_leave` is **not** here:
        #: an approved leave is derived from `leaverequest`, so storing it would leave
        #: a stale "On Leave" row behind the moment a leave is cancelled (see the
        #: module docstring and `__init__.py`). `late` is not here either - `labels`
        #: explains why a status that could touch pay waits for an agreed rule.
        CheckConstraint(
            "status IN ('present', 'absent', 'half_day')",
            name="ck_staffattendancerecord_status",
        ),
    )

    #: Who marked it. NULL when a migration or the seed wrote the row.
    marked_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)
    #: Moves when a marked day is amended - the audit row says what it was before.
    updated_at: datetime = Field(default_factory=utcnow)
