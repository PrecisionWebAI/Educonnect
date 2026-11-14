"""The rows both leave screens print, and the shapes the workflow moves.

One rule, learned the hard way: **the wire speaks snake_case**, and the browser's
services convert it to camelCase with `toCamel` (`frontend/src/lib/api/case.ts`).
Mixing the two on one object - which the old `submittedAt` beside `from_date` did
- means one of them arrives as `undefined` and the table shows an empty column
with no error anywhere.

A value the backend genuinely does not have yet is `None`, never `0` or `""`:
"no leave balance recorded" and "zero days left" are different sentences to a
teacher. That rule is why a type with no policy sends `entitled: null` rather than
`0` - see `labels` for the whole reasoning.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.text import CanonicalRequest

from . import labels


class LeaveApplicationItem(BaseModel):
    """One row of the student leave screen."""

    id: UUID
    student: str
    class_name: str
    type: str
    from_date: str
    to_date: str
    reason: str
    days: int
    status: str
    submitted_at: str


class StaffLeaveRow(BaseModel):
    """One row of the staff leave screen."""

    id: UUID
    #: The employee the leave belongs to. `None` for the rare requester who has a
    #: login but no employee record (a guardian filing on somebody's behalf).
    employee_id: UUID | None = None
    staff_name: str
    #: `employee.employee_code` (`EMP-0043`); "" for a requester with no record.
    staff_code: str
    #: The catalog's own word ("Teacher", "Vice Principal"), not the codename.
    role: str
    department: str = ""
    leave_type: str
    from_date: str
    to_date: str
    days: int
    reason: str
    #: Who covers the class. `None` until the substitution screen can name one -
    #: an empty string would print as a blank cell that looks like a bug.
    substitute: str | None = None
    #: Days left in this leave type for the leave's own year, **counted from the
    #: requests themselves**. `0` is "none left"; `None` is "this school tracks no
    #: balance for this type" - two different sentences.
    balance: int | None = None
    status: str
    applied_at: str
    #: Who decided it, and when. `None` while pending.
    decided_by: str | None = None
    decided_at: str | None = None
    decision_note: str | None = None


# --- policies ---------------------------------------------------------------


class LeavePolicyItem(CanonicalRequest):
    """One leave type and its annual grant, inside a save payload."""

    leave_type: str = Field(min_length=1, max_length=60)
    #: Days a year. `0` is "the type exists but grants nothing"; 365 is the rail -
    #: a year is the longest leave a school can grant.
    annual_days: int = Field(ge=0, le=365)


class LeavePoliciesWrite(CanonicalRequest):
    """The school's policy list, saved in one call.

    A list rather than one type at a time: the screen edits a table and presses one
    Save, and a per-type endpoint would leave the school half-saved when the third
    request fails. Types **omitted** from the payload are left alone - a school
    adding "Bereavement" does not want the same Save to delete every other type.
    """

    policies: list[LeavePolicyItem] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def _one_row_per_type(self) -> LeavePoliciesWrite:
        seen: set[str] = set()
        for policy in self.policies:
            key = labels.type_key(policy.leave_type)
            if key in seen:
                raise ValueError(
                    f"'{policy.leave_type}' appears twice; send one row per leave type."
                )
            seen.add(key)
        return self


class LeavePolicyRead(BaseModel):
    """One row of the policy table."""

    leave_type: str
    annual_days: int
    #: Who last set it, and when - the only trail a school-level row carries.
    updated_by: str | None = None
    updated_at: str | None = None


# --- balances ---------------------------------------------------------------


class LeaveBalanceRow(BaseModel):
    """One person, one leave type, one year - and what the numbers mean.

    `used` counts **approved** days, `pending` counts days still waiting, and
    `remaining` is what is still free to ask for (`labels.balance_left`). They
    travel together because "3 left" is not readable without knowing whether two
    more are already on somebody's desk.
    """

    employee_id: UUID
    employee_code: str
    staff_name: str
    department: str
    leave_type: str
    year: int
    #: `None` when this school tracks no entitlement for this type.
    entitled: int | None = None
    used: int = 0
    pending: int = 0
    remaining: int | None = None
    #: `policy` / `override` / `untracked` - where the entitlement came from, so
    #: the screen can say why two teachers with the same post differ.
    source: str = "untracked"


class LeaveBalancesRead(BaseModel):
    """The balance register: every person, every type, one year."""

    year: int
    #: The leave types in the order the screen lists its columns.
    types: list[str] = Field(default_factory=list)
    rows: list[LeaveBalanceRow] = Field(default_factory=list)


class LeaveBalanceWrite(CanonicalRequest):
    """Set one person's override for one type and year."""

    leave_type: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=2000, le=2100)
    entitled_days: int = Field(ge=0, le=365)
    #: Why it differs. Prose, so it keeps its case.
    note: str | None = Field(default=None, max_length=200)


# --- the workflow -----------------------------------------------------------


class LeaveApplyIn(CanonicalRequest):
    """Apply for leave - for one staff member, or for one student.

    At most **one** of `employee_id` / `student_id` says whose leave it is. Sending
    neither is the teacher's own form: the server looks their employee record up
    from the login, so a person filing their own leave never has to know their own
    id. Sending both is refused, because one request belongs to one person.
    """

    employee_id: UUID | None = None
    student_id: UUID | None = None
    leave_type: str = Field(min_length=1, max_length=60)
    from_date: date
    to_date: date
    #: Prose, so it keeps its case.
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _one_person(self) -> LeaveApplyIn:
        if self.employee_id is not None and self.student_id is not None:
            raise ValueError(
                "Send either an employee or a student - one leave belongs to one person."
            )
        return self

    @model_validator(mode="after")
    def _a_range_that_runs_forwards(self) -> LeaveApplyIn:
        if self.to_date < self.from_date:
            raise ValueError("The leave ends before it starts.")
        # A rail, not a rule about schools: a request over a year long is a typo in
        # a year field, and no balance can be checked against it.
        if (self.to_date - self.from_date).days > 365:
            raise ValueError("A single leave cannot run longer than a year.")
        return self


class LeaveDecisionIn(CanonicalRequest):
    """The note that travels with a decision (approve / reject / cancel).

    Optional, and prose, so it keeps its case: the reject screen's own words are
    what the applicant is shown.
    """

    note: str | None = Field(default=None, max_length=300)


class LeaveRequestRead(BaseModel):
    """One request after a write - the shape every workflow verb answers with.

    One shape for apply and the three decisions, so the screen's toast, its table
    and its balance strip all read the same object instead of three near-copies.
    `balance_remaining` is the person's days left for this type **after** the write
    (`None` for a student leave, or for a type this school does not track).
    """

    id: UUID
    #: `staff` or `student` - which screen the row belongs to.
    scope: str
    person: str
    person_code: str
    leave_type: str
    from_date: str
    to_date: str
    days: int
    reason: str
    status: str
    balance_remaining: int | None = None
    decided_by: str | None = None
    decided_at: str | None = None
    decision_note: str | None = None
    applied_at: str
