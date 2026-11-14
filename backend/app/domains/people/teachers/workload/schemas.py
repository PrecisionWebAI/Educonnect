"""The shapes the workload tab reads, and the two it writes.

Three rules, each learned from a number that used to lie:

* **a percentage is never the only thing sent.** `periods` and `capacity` travel
  with `utilisation`, so the bar and the figure beside it cannot come from two
  different denominators;
* **the API sends the key, the screen prints the label.** `duty_type` comes with
  `duty_type_label`, the way a document carries `doc_type_label`;
* **vocabularies are checked here.** A duty type outside `labels.DUTY_TYPES` or a
  day outside `labels.WEEK_DAYS` is a `422` at the edge with the list spelled
  out, not a row the audit feed later cannot name.
"""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.text import CanonicalRequest

from .. import labels


class WorkloadRuleRead(BaseModel):
    """The school's policy, as the capacity dialog opens it.

    `is_set` is the difference between "a full week is 24 periods" and "nobody has
    said yet" - the dialog needs it to decide whether it is editing a decision or
    making the first one.
    """

    weekly_periods: int | None = None
    overload_percent: int = 100
    underload_percent: int = 60
    is_set: bool = False
    updated_at: datetime | None = None
    #: Who last set it, by name.
    updated_by: str | None = None


class WorkloadRuleWrite(CanonicalRequest):
    """One full week, in periods. Bounded so a typo cannot empty the matrix.

    `le=100` on the weekly periods is a sanity rail, not a rule about schools: a
    week with more than a hundred teaching periods is a data-entry mistake, and
    dividing by it would report every teacher as "Light".
    """

    weekly_periods: int = Field(ge=1, le=100)
    overload_percent: int = Field(default=100, ge=50, le=300)
    underload_percent: int = Field(default=60, ge=0, le=100)

    @model_validator(mode="after")
    def _thresholds(self) -> WorkloadRuleWrite:
        """A person cannot be "lightly loaded" above the overload line.

        Allowed through, the two thresholds would overlap and every teacher would
        be both - the badge picks `Overloaded` first, so the under-load number
        would simply stop meaning anything.
        """
        if self.underload_percent >= self.overload_percent:
            raise ValueError(
                "The under-load threshold must be below the over-load threshold."
            )
        return self


class StaffDutyCreate(CanonicalRequest):
    """One duty to add. Its shape rules are below, not in the router.

    Every check here is a fact about a duty that cannot be true at once, so a
    `422` naming it is better than a row that the week grid then has to guess at.
    """

    #: `labels.DUTY_TYPES` (`exam_duty`, `gate_duty`, …).
    duty_type: str
    title: str | None = None
    #: Weekly, e.g. `monday`. Mutually exclusive with `on_date`.
    day_of_week: str | None = None
    #: A single date, e.g. an invigilation. Mutually exclusive with `day_of_week`.
    on_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    #: Defaults to today when the caller does not say.
    effective_from: date | None = None
    effective_to: date | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _one_shape(self) -> StaffDutyCreate:
        duty_type = (self.duty_type or "").strip().lower()
        if duty_type not in labels.DUTY_TYPES:
            allowed = ", ".join(labels.DUTY_TYPES)
            raise ValueError(f"A duty type must be one of: {allowed}.")
        self.duty_type = duty_type

        if self.day_of_week is not None:
            day = self.day_of_week.strip().lower()
            if day not in labels.WEEK_DAYS:
                allowed = ", ".join(labels.WEEK_DAYS)
                raise ValueError(f"A duty day must be one of: {allowed}.")
            self.day_of_week = day

        if self.day_of_week and self.on_date:
            raise ValueError(
                "A duty is either weekly or a single date, not both. "
                "Leave both empty for a standing duty."
            )
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("The end time must be after the start time.")
        if (
            self.effective_from
            and self.effective_to
            and self.effective_to < self.effective_from
        ):
            raise ValueError("The end date must not be before the start date.")
        return self


class StaffDutyRead(BaseModel):
    """One duty, as the person's drawer lists it."""

    id: UUID
    duty_type: str
    #: The screen's word for `duty_type` (`Exam Duty`).
    duty_type_label: str
    title: str | None = None
    day_of_week: str | None = None
    day_label: str | None = None
    on_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    #: `09:00-11:00`, or None for a duty with no hours.
    slot: str | None = None
    hours: float = 0.0
    effective_from: date
    effective_to: date | None = None
    note: str | None = None
    created_at: datetime | None = None


class WeekSlotRead(BaseModel):
    """One cell of the week grid: a taught period or a duty.

    `kind` is what the grid colours differently, and it is the reason periods and
    duties can share one list - a teacher does not experience them as two weeks.
    """

    kind: Literal["period", "duty"]
    day: str
    day_label: str
    start: time | None = None
    end: time | None = None
    #: `09:00-09:45`; empty when the duty has no hours.
    slot: str = ""
    #: The subject for a period, the duty's own name for a duty.
    subject: str
    #: `Class 9-A` for a period; None for a duty.
    class_label: str | None = None
    room: str | None = None
    title: str | None = None
    period_id: UUID | None = None
    duty_id: UUID | None = None


class WeekDayRead(BaseModel):
    """One column of the grid. A day with nothing in it is still a day."""

    day: str
    day_label: str
    slots: list[WeekSlotRead] = Field(default_factory=list)
    periods: int = 0
    duties: int = 0


class StaffWeekRead(BaseModel):
    """One person's week: the grid, its two totals and the duty hours beside them."""

    id: UUID
    name: str
    department: str
    days: list[WeekDayRead] = Field(default_factory=list)
    periods: int = 0
    duties: int = 0
    #: Hours of *duty* only - see the note in `__init__.py` on why these are not
    #: folded into the period count.
    duty_hours: float = 0.0
    #: Days with neither a period nor a duty, so the screen can say "3 free days".
    empty_days: int = 0


class DepartmentLoad(BaseModel):
    """One row of the analytics split."""

    department: str
    staff: int
    periods: int
    utilisation: int
    overloaded: int


class WorkloadAnalytics(BaseModel):
    """The tiles above the matrix, counted over the same rows the matrix shows.

    `capacity` and `capacity_source` travel together for the same reason
    `periods` and `utilisation` do: the screen must be able to print "out of 24
    (school rule)" without deciding which number it was given.
    """

    capacity: int
    capacity_source: Literal["rule", "timetable"]
    #: What the timetable itself runs, whatever the rule says.
    week_slots: int = 0
    weekly_periods_rule: int | None = None
    staff: int = 0
    total_periods: int = 0
    average_periods: float = 0.0
    average_utilisation: int = 0
    overloaded: int = 0
    #: On the roll with no period in the timetable yet.
    unassigned: int = 0
    duties: int = 0
    by_department: list[DepartmentLoad] = Field(default_factory=list)
