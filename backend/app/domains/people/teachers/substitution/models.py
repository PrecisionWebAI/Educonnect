"""The two tables a substitution needs: why somebody is away, and who stood in.

`substitutionrequest` is the **demand**: one row per person per day, saying why
their periods need cover - a leave type, a training day, an official duty. It
exists so an assignment can point at a reason that survives the leave being edited,
and so cover for a non-leave absence has somewhere to live.

`substitutionassignment` is the **supply**: this period, on this date, covered by
that person. `UNIQUE(school_id, period_id, on_date)` is the rule the whole feature
turns on - *one* adult walks into a given room at a given hour - and PostgreSQL
enforces it (all three columns are NOT NULL), so two clerks assigning the same slot
from two tabs cannot invent a second teacher for it.

What is deliberately **not stored**:

* the affected periods - derived from `timetableperiod` for that weekday, so a
  timetable edit moves the cover list with it instead of leaving stale rows;
* "covered / open" - derived from whether an assignment exists for the slot;
* the leave itself - `leaverequest` owns it, and `leave_request_id` only names the
  row the absence came from. Two sources of truth for "is this person away" is how
  the register and the cover sheet start disagreeing about the same Tuesday.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow
from app.domains.people.teachers import labels


class SubstitutionRequestBase(SQLModel):
    """One person, one day, and why their timetable needs somebody else."""

    #: The person who is away.
    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    on_date: date
    #: The reason in the school's own words: the leave type ("Sick"), or
    #: "Training" / "Official duty" for an absence that is not leave.
    reason: str
    #: The office's note ("half-day, morning only").
    note: str | None = None
    #: The `leaverequest` row this absence came from, when it came from one. NULL
    #: for a training day: not every absence is a leave, and inventing one would
    #: spend days from a balance nobody granted.
    leave_request_id: UUID | None = Field(default=None, foreign_key="leaverequest.id")


class SubstitutionRequest(SubstitutionRequestBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, employee_id, on_date)` - one absence per person per day.

    Both columns are NOT NULL, so PostgreSQL enforces it, and `repository.ensure_request`
    updates the row it finds rather than inserting a second: two rows for one
    absence would leave the assignment's `request_id` pointing at whichever one was
    written first.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "employee_id",
            "on_date",
            name="uq_substitutionrequest_employee_date",
        ),
    )

    #: Who wrote it. NULL when a migration or the seed did.
    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)


class SubstitutionAssignmentBase(SQLModel):
    """Who covers one period, on one date, in place of one absent teacher."""

    request_id: UUID = Field(foreign_key="substitutionrequest.id", index=True)
    #: The slot being covered. Its class, subject and times are read from the
    #: timetable rather than copied here: a copied period would keep saying 09:00
    #: after the timetable moved it.
    period_id: UUID = Field(foreign_key="timetableperiod.id", index=True)
    on_date: date
    #: Kept on the row as well, because the absence is the thing being answered:
    #: a cover must still name who it was for if the request row is ever removed.
    absent_employee_id: UUID = Field(foreign_key="employee.id", index=True)
    substitute_employee_id: UUID = Field(foreign_key="employee.id", index=True)
    #: `labels.ASSIGNED` / `labels.APPROVED`.
    status: str = labels.ASSIGNED
    note: str | None = None


class SubstitutionAssignment(
    SubstitutionAssignmentBase, TenantMixin, UUIDMixin, table=True
):
    """`UNIQUE(school_id, period_id, on_date)` - one substitute per slot.

    Both columns are NOT NULL, so the constraint is real. A withdrawn cover is
    **deleted** rather than marked `Cancelled` (see `labels.SUBSTITUTION_STATUSES`):
    a cancelled row would keep the slot occupied and block the replacement the
    office is trying to record. The trail keeps the history.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "period_id",
            "on_date",
            name="uq_substitutionassignment_period_date",
        ),
    )

    assigned_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    assigned_at: datetime = Field(default_factory=utcnow)
    #: The approval - NULL until somebody with `substitutions.approve` signs it.
    decided_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    decided_at: datetime | None = None
