"""Phase 9's three staff aggregates - derived, never stored.

`GET /reports/staff-summary` answers the three questions a principal asks at the end
of a term, from tables this product already keeps:

* **how much of the register is being filled in, and how does it read?** (attendance)
* **how is the timetable spread across the staff?** (workload)
* **how are the staff scoring this session?** (performance - attendance, workload and
  course completion, the same three ingredients the Performance tab ranks people by)

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


class StaffPerformanceSummary(BaseModel):
    """The roll's scores for the session, summarised - never a stored number.

    The per-person scores come from `people/teachers/performance`, so the tile above
    the table and the rows inside it cannot disagree. `scored` is how many people had
    **something** recorded: a school that has not marked its register yet gets
    `average: null` rather than a 0 that reads as a failing staff.
    """

    #: The session the numbers describe, from `academic_year` (or the calendar).
    session: str = ""
    session_start: date | None = None
    session_end: date | None = None
    #: Everybody the aggregate covers, at the caller's scope.
    people: int = 0
    #: How many of them had a score at all.
    scored: int = 0
    average: float | None = None
    maximum: int | None = None
    minimum: int | None = None
    #: Each component averaged over the people who have it - `None` when nobody does.
    attendance: int | None = None
    workload: int | None = None
    course: int | None = None


class StaffSummaryReport(BaseModel):
    attendance: StaffAttendanceSummary
    workload: StaffWorkloadSummary
    performance: StaffPerformanceSummary
    #: `school` for the office, `scoped` when the caller only sees some people - the
    #: payload says which, so a number is never quietly about fewer people.
    scope: str
    people: int
