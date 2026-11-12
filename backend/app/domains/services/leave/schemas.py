"""The rows both leave screens print.

One rule, learned the hard way: **the wire speaks snake_case**, and the browser's
services convert it to camelCase with `toCamel` (`frontend/src/lib/api/case.ts`).
Mixing the two on one object - which the old `submittedAt` beside `from_date` did
- means one of them arrives as `undefined` and the table shows an empty column
with no error anywhere.

A value the backend genuinely does not have yet is `None`, never `0` or `""`:
"no leave balance recorded" and "zero days left" are different sentences to a
teacher.
"""

from uuid import UUID

from pydantic import BaseModel


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
    staff_name: str
    #: `employee.employee_code` (`EMP-0043`); "" for the rare requester who has
    #: a login but no employee record.
    staff_code: str
    #: The catalog's own word ("Teacher", "Vice Principal"), not the codename.
    role: str
    leave_type: str
    from_date: str
    to_date: str
    days: int
    reason: str
    #: Who covers the class. `None` until the substitution screen can name one -
    #: an empty string would print as a blank cell that looks like a bug.
    substitute: str | None = None
    #: Days left in the leave type's balance. `None` until balances are tracked.
    balance: int | None = None
    status: str
    applied_at: str
