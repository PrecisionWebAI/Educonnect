"""The two tables a workload needs: what a full week is, and what else fills it.

`staffworkloadrule` is **one row per school** - a policy, not a per-person
setting. It holds the number the utilisation figure is a percentage *of*, plus
the two thresholds the matrix's badge uses. Storing it once means the principal
changes "a full load" in one place instead of on forty rows that then disagree.

`staffduty` is the work that is neither a period nor leave: exam invigilation, a
gate, assembly, the library desk, a bus route, a club. It carries a weekly day
**or** a single date - a gate duty repeats every Monday, an invigilation happens
once - and a duty may have neither, which is how a standing responsibility
("library in-charge") is recorded without pretending it has a slot. Nothing here
counts towards the period total; see the note in `__init__.py`.
"""

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class StaffWorkloadRuleBase(SQLModel):
    """How the school measures a week.

    `weekly_periods` is **NULL until the office states it**, and NULL is not the
    same as zero: the matrix falls back to the timetable's own slot count and says
    so (`capacity_source: "timetable"`), because a denominator the school never
    chose is still a real one, while zero would report every teacher as
    unassigned.
    """

    weekly_periods: int | None = None
    #: Above this percentage of `weekly_periods` a person is overloaded.
    overload_percent: int = 100
    #: Below this percentage they are lightly loaded.
    underload_percent: int = 60


class StaffWorkloadRule(StaffWorkloadRuleBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id)` - one policy per school.

    The constraint is a backstop, not the rule: `repository.save_rule` updates the
    row it finds instead of inserting a second one, because two rules would leave
    the matrix choosing between them. PostgreSQL also treats two NULL `school_id`
    values as different, so the unique key cannot police a caller with no school -
    the service is where that is decided.
    """

    __table_args__ = (
        UniqueConstraint("school_id", name="uq_staffworkloadrule_school"),
    )

    #: Who last changed the policy. NULL when a migration or the seed wrote it.
    updated_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    updated_at: datetime = Field(default_factory=utcnow)


class StaffDutyBase(SQLModel):
    """One thing a person does outside their timetable.

    `day_of_week` and `on_date` are mutually exclusive (the schema refuses both);
    neither means a standing duty with no fixed slot. The times are optional for
    the same reason: "library in-charge" has hours nobody wrote down, and a
    default of 09:00-10:00 would be a number the school never said.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    #: `labels.DUTY_TYPES` - kept as text so a new duty type is a one-line change
    #: in `labels`, not a migration: it is a fixed vocabulary, not a state machine.
    duty_type: str
    #: Free text the office adds to tell two duties of the same type apart
    #: ("Half-Yearly Exam - Hall B").
    title: str | None = None
    #: A recurring weekly duty ("every Monday, gate").
    day_of_week: str | None = None
    #: A one-off duty ("12 December, invigilation").
    on_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    effective_from: date
    #: NULL means "still standing".
    effective_to: date | None = None
    note: str | None = None


class StaffDuty(StaffDutyBase, TenantMixin, UUIDMixin, table=True):
    """No `UNIQUE(employee, type, day, start)` on purpose.

    Every column in that key except `employee_id` may be NULL, and PostgreSQL
    treats two NULLs as different values - the constraint would let a duplicate
    straight through while looking like it prevented one. The duplicate check
    therefore lives in `service.add_duty`, which answers `409` with the duty it
    found, the same way `staffqualification` does.
    """

    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)
