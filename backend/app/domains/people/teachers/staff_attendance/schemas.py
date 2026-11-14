"""The register's shapes: one day, one month, and the two writes.

Three rules, each about a number a screen would otherwise print wrongly:

* **the key and its label travel together.** `status` comes with `status_label`
  (`half_day` -> `Half Day`), so the table and the filter print one spelling;
* **`not_marked` is a word, not a zero.** A day nobody marked is its own status in
  the register, and its own count in the month, because "absent" is a claim about a
  person and "not marked" is a claim about the office;
* **`on_leave` cannot be written.** The write schemas offer only the three
  markable words; a caller asking to store `on_leave` is told why instead of
  getting a row that would go stale the day the leave is cancelled.
"""

from datetime import date, datetime, time, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.text import CanonicalRequest

#: The three words a register row may hold - `labels.ATTENDANCE_STATUSES`, typed
#: so the request body is refused at the edge rather than in the service.
MarkableStatus = Literal["present", "absent", "half_day"]


class AttendanceMarkIn(BaseModel):
    """One person's day, inside a bulk payload."""

    employee_id: UUID
    status: MarkableStatus
    #: The office's own words. Prose, so it keeps its case.
    remarks: str | None = Field(default=None, max_length=200)


class AttendanceSelfIn(BaseModel):
    """One person's own day (`POST /teachers/me/attendance`).

    Deliberately **no `employee_id`**: the person is the one holding the token, so a
    body that names somebody else cannot be sent at all. The times are optional -
    a school that only records present/absent does not have to invent a 09:00.
    """

    date: date
    status: MarkableStatus
    remarks: str | None = Field(default=None, max_length=200)
    check_in_time: time | None = None
    check_out_time: time | None = None


class AttendanceBulkIn(CanonicalRequest):
    """A whole day's register in one call.

    `max_length=200` is a sanity rail, not a rule about schools: every school this
    product serves marks under that in a day, and a payload of five thousand rows
    is a bug in a loop rather than an office at work. The per-status vocabulary is
    checked by `MarkableStatus`; a duplicate employee is refused below, because two
    rows for one person would make "what did we record" depend on list order.
    """

    date: date
    records: list[AttendanceMarkIn] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _one_row_per_person(self) -> AttendanceBulkIn:
        seen: set[UUID] = set()
        for row in self.records:
            if row.employee_id in seen:
                raise ValueError(
                    "The same employee appears twice in one register; "
                    "send one status per person."
                )
            seen.add(row.employee_id)
        return self

    @model_validator(mode="after")
    def _not_the_future(self) -> AttendanceBulkIn:
        """Refuse a date nobody can have marked yet.

        One day of slack on purpose: the server may be in UTC while the school is a
        day ahead, and blocking the office's own "today" for a few hours every
        evening would be worse than allowing a typo'd tomorrow. A register for next
        year is still a `422`.
        """
        if self.date > date.today() + timedelta(days=1):
            raise ValueError("A register cannot be marked for a future date.")
        return self


class AttendanceRecordPatch(CanonicalRequest):
    """Amend one marked day. Every field is optional, at least one is required."""

    status: MarkableStatus | None = None
    remarks: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _something_to_change(self) -> AttendanceRecordPatch:
        if self.status is None and self.remarks is None:
            raise ValueError("Send a status or remarks to change.")
        return self


class RegisterRowRead(BaseModel):
    """One line of the day's register - a person, not a row.

    Everybody on the roll gets a line, whether or not anybody marked them, because
    the office's question is "who has not been marked yet" and a missing line
    answers it silently. `record_id` is `None` for a person with no row that day.
    """

    employee_id: UUID
    employee_code: str
    name: str
    department: str
    designation: str | None = None
    #: `present` / `absent` / `half_day` / `on_leave` / `not_marked`.
    status: str
    #: The screen's word for `status` (`Half Day`, `On Leave`, `Not Marked`).
    status_label: str
    #: True when `status` is one of the three this register stores.
    is_marked: bool = False
    #: The row to amend, or `None` when this person has no row for the day.
    record_id: UUID | None = None
    remarks: str | None = None
    #: The leave that made this person `on_leave` (`Medical`, `Casual`).
    leave_type: str | None = None
    marked_by: str | None = None
    marked_at: datetime | None = None


class RegisterRead(BaseModel):
    """One day: every person in scope, plus the counts above the table.

    The counts describe **the day in scope** (the department filter applies, the
    status filter does not), so picking "Absent" narrows the list without changing
    the numbers above it - the same rule the directory's tiles follow.
    """

    date: date
    #: `Monday` - the register is read by a person who thinks in weekdays.
    weekday: str
    rows: list[RegisterRowRead] = Field(default_factory=list)
    total: int = 0
    present: int = 0
    absent: int = 0
    half_day: int = 0
    on_leave: int = 0
    #: On the roll, no row, no leave. The office's to-do list.
    not_marked: int = 0
    marked: int = 0
    #: Present + half days over the **marked** days (`labels.attendance_percent`).
    percent: int = 0


class AttendanceDayRead(BaseModel):
    """One day in a person's month grid."""

    date: date
    day: int
    weekday: str
    status: str
    status_label: str
    remarks: str | None = None
    leave_type: str | None = None
    record_id: UUID | None = None
    marked_by: str | None = None
    marked_at: datetime | None = None


class StaffMonthRead(BaseModel):
    """One person's month: the grid, the counts, and what they are a share of.

    `not_marked` is sent beside `percent` so the screen can say "92% of 20 marked
    days, 10 not marked yet" instead of implying the month is complete.
    """

    employee_id: UUID
    employee_code: str
    name: str
    department: str
    #: `2026-11`, the key the caller sent.
    month: str
    #: `November 2026`, so the sheet does not re-implement month names.
    month_label: str
    days: list[AttendanceDayRead] = Field(default_factory=list)
    present: int = 0
    absent: int = 0
    half_day: int = 0
    on_leave: int = 0
    not_marked: int = 0
    marked: int = 0
    percent: int = 0
