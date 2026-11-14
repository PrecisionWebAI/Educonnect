"""Phase 9's three staff aggregates - derived, never stored.

`GET /reports/staff-summary` answers the three questions a principal asks at the end
of a term, from tables this product already keeps:

* **how much of the register is being filled in, and how does it read?** (attendance)
* **how is the timetable spread across the staff?** (workload)
* **where has the appraisal season got to?** (appraisal)

Nothing is copied into a report table: a stored aggregate is a number that was true
on the day somebody last ran a job, and the first question a principal asks is "does
this include last week?".
"""

from datetime import date

from pydantic import BaseModel


class StaffAttendanceSummary(BaseModel):
    #: The window the numbers describe - a percentage without one is not a fact.
    window_start: date
    window_end: date
    days: int
    present: int
    half_day: int
    absent: int
    marked: int
    #: A share of the days somebody **marked**, not of the calendar (see Phase 5).
    percent: int


class StaffWorkloadSummary(BaseModel):
    teachers: int
    periods: int
    average: float
    maximum: int
    #: Against the school's own capacity rule, or the heaviest load when no rule is
    #: set - and `capacity_source` says which, so the buckets mean something.
    under: int
    normal: int
    over: int
    capacity_source: str
    capacity: int


class StaffAppraisalSummary(BaseModel):
    cycle: str | None = None
    cycle_status: str | None = None
    total: int = 0
    submitted: int = 0
    reviewed: int = 0
    finalized: int = 0
    #: Mean of the reviewers' ratings, one decimal - `None` when nobody has rated.
    average_reviewer_rating: float | None = None
    goals_judged: int = 0
    goals_achieved: int = 0


class StaffSummaryReport(BaseModel):
    attendance: StaffAttendanceSummary
    workload: StaffWorkloadSummary
    appraisals: StaffAppraisalSummary
    #: `school` for the office, `scoped` when the caller only sees some people - the
    #: payload says which, so a number is never quietly about fewer people.
    scope: str
    people: int
