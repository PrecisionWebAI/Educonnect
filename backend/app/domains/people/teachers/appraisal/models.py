"""Four tables: the window, one person's appraisal in it, their goals, and training.

`appraisalcycle` is the window a school runs its season in ("2025-26 Annual",
April to March). `appraisal` is **one person inside one window** - the rating they
gave themselves, the rating their reviewer recorded, and where the conversation has
got to. `appraisalgoal` is a measurable line inside that appraisal ("Class 9 average
above 75"), and `trainingrecord` is what somebody attended, which is the evidence a
goal was worked on rather than merely written down.

Why a separate `appraisal` and not a column on `employee`: the same person is
appraised every year, and last year's rating is a fact that must not be overwritten
by this year's. `UNIQUE(school_id, cycle_id, employee_id)` makes "one appraisal per
person per season" the database's rule rather than a screen's.

`teacherreview` (the anonymous star ratings) is deliberately **not** merged in: an
anonymous parent review and a signed appraisal are different claims about the same
teacher, and averaging them is how a school ends up defending a number nobody wrote.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow
from app.domains.people.teachers import labels


class AppraisalCycleBase(SQLModel):
    """One appraisal season."""

    name: str
    start_date: date
    end_date: date
    #: `labels.APPRAISAL_CYCLE_STATUSES` - `Draft` (being planned), `Open` (in
    #: progress), `Closed` (the year is signed off).
    status: str = labels.CYCLE_DRAFT
    note: str | None = None


class AppraisalCycle(AppraisalCycleBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, name)` - "2025-26 Annual" exists once."""

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_appraisalcycle_school_name"),
    )

    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)


class AppraisalBase(SQLModel):
    """One person's appraisal in one cycle."""

    cycle_id: UUID = Field(foreign_key="appraisalcycle.id", index=True)
    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    #: `labels.APPRAISAL_STATUSES` - Draft -> Submitted -> Reviewed -> Finalized.
    status: str = labels.APPRAISAL_DRAFT
    #: 1..5, in the person's own words. NULL until they fill the form in.
    self_rating: int | None = None
    self_note: str | None = None
    #: 1..5, the reviewer's. NULL until somebody reviews it.
    reviewer_rating: int | None = None
    reviewer_note: str | None = None
    #: Who reviewed it. Kept on the row so "who said this" survives a role change.
    reviewer_employee_id: UUID | None = Field(default=None, foreign_key="employee.id")


class Appraisal(AppraisalBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, cycle_id, employee_id)` - one appraisal per season."""

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "cycle_id",
            "employee_id",
            name="uq_appraisal_cycle_employee",
        ),
    )

    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    #: Set the moment the office finalises it; nothing may change afterwards.
    finalized_at: datetime | None = None


class AppraisalGoalBase(SQLModel):
    """One measurable line in an appraisal."""

    appraisal_id: UUID = Field(foreign_key="appraisal.id", index=True)
    title: str
    #: What "done" looks like, in the school's own words ("above 75% for Class 9").
    target: str | None = None
    #: The reviewer's verdict on it - NULL while nobody has judged it, which is not
    #: the same as "not achieved".
    achieved: bool | None = None
    #: How much it counts when a school weights its goals. 1 by default so an
    #: appraisal with no explicit weights is still summable.
    weight: int = 1


class AppraisalGoal(AppraisalGoalBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)


class TrainingRecordBase(SQLModel):
    """Something the school sent somebody to, or paid for."""

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    title: str
    provider: str | None = None
    on_date: date
    hours: int = 0
    note: str | None = None


class TrainingRecord(TrainingRecordBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)
    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
