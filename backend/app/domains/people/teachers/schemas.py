"""The shapes the Teachers & Staff screen reads.

Two rules these schemas follow, because both were broken before:

* a value that may not exist is **optional**, not a stand-in. The old
  `qualification: str` blew up the whole list with a 500 on a single employee
  whose qualification was NULL, and `workload: int = 18` printed an invented
  load for anybody the timetable query missed;
* a field name says what the value is (`status` is the employment state, not the
  login state) and the three statuses are the ones `labels` defines, so the API
  cannot grow a fourth word the badges do not know.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest


class TeacherCreate(CanonicalRequest):
    user_id: UUID
    department: str
    qualification: str | None = None
    joining_date: date


class TeacherRead(BaseModel):
    """One row of the staff directory."""

    id: UUID
    user_id: UUID
    department: str
    #: NULL for the staff who were hired without one - not a reason to fail.
    qualification: str | None = None
    joining_date: date
    #: `employee.employee_code` (`EMP-0043`) - always present on a real employee.
    staffCode: str
    name: str
    #: The subjects this teacher can take. Empty when none is listed yet, which
    #: is a different fact from "their department" and is shown separately.
    subject: str
    phone: str
    email: str
    #: `Inactive` (off the roll) / `On Leave` (approved leave today) / `Active`.
    status: Literal["Active", "Inactive", "On Leave"] = "Active"
    #: The class-sections they are attached to (class teacher or subject teacher).
    classes: list[str] = Field(default_factory=list)
    #: Timetable periods a week, from `timetableperiod`.
    workload: int = 0


class WorkloadMatrixRow(BaseModel):
    #: The employee id - names repeat, so a table keyed on the name collided.
    id: UUID
    staff: str
    subject: str
    classes: list[str]
    periods: int
    #: The week's teaching slots the school's timetable actually runs.
    capacity: int
    utilisation: int


class StaffPerformance(BaseModel):
    id: UUID
    staff: str
    rating: float
    reviews: int
    trend: Literal["up", "flat", "down"]
    score: int


class StaffSummary(BaseModel):
    """The four tiles above the directory - counted by the database.

    The screen used to derive them from the rows it had loaded, so a capped or
    filtered page silently changed the totals.
    """

    total: int
    active: int
    on_leave_today: int
    inactive: int
    #: Timetable periods a week across the whole teaching staff.
    periods_per_week: int
    #: Teachers on the roll with no period in the timetable yet.
    without_timetable: int
