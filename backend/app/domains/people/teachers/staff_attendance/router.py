"""The register's API: one day, one person's month, and the two writes.

Four routes, and the fixed one comes first - the same rule `api.py` follows for the
hub: `/register` and `/bulk` are declared before `/records/{record_id}`, and all of
them are mounted before the hub's `/{teacher_id}` so a segment can never be read as
a UUID.

There is deliberately **no `GET /teachers/attendance`**: the day's register *is*
the read, and a bare list of stored rows would be the wrong answer to the office's
question ("who has not been marked yet?"), since a person with no row is exactly
who they are looking for.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    AttendanceBulkIn,
    AttendanceDayRead,
    AttendanceRecordPatch,
    RegisterRead,
    StaffMonthRead,
)

router = APIRouter()

_can_view = RequirePermission("staff_attendance.read")
#: Today's roll. Narrower than reading it: a department head reads their
#: department's register but does not mark a colleague present.
_can_mark = RequirePermission("staff_attendance.mark")
#: Amending a day already marked. A separate codename from `mark` so a school can
#: later give marking to a coordinator without giving them the right to rewrite
#: history; both are checked by `scope.may_mark_attendance` today.
_can_update = RequirePermission("staff_attendance.update")


@router.get("/register", response_model=RegisterRead)
def read_register(
    on_date: date | None = Query(default=None, alias="date"),
    department: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """The day's register: every person in scope, marked or not.

    `date` defaults to today - the office opens this screen in the morning and
    marks the day they are in. The parameter is aliased because `date` is also the
    type, and a query string cannot be called `date_`.
    """
    return service.register(
        session,
        on_date=on_date or date.today(),
        user=current_user,
        department=department,
        status=status,
    )


@router.post("/bulk", response_model=RegisterRead)
def mark_register(
    payload: AttendanceBulkIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_mark),
):
    """Mark a whole day in one call, and answer with the day as it now reads.

    `409` for somebody on approved leave (the leave is the record, not this table)
    or for a leaver; `422` for a duplicate person or an unknown status.
    """
    return service.mark_bulk(session, payload, current_user)


@router.patch("/records/{record_id}", response_model=AttendanceDayRead)
def amend_register_record(
    record_id: UUID,
    payload: AttendanceRecordPatch,
    session: Session = Depends(get_session),
    current_user=Depends(_can_update),
):
    """Correct one marked day. The row is looked up by its own id (`404`)."""
    return service.amend(session, record_id, payload, current_user)


@router.get("/employees/{employee_id}", response_model=StaffMonthRead)
def read_staff_month(
    employee_id: UUID,
    month: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(_can_view),
):
    """One person's month: every day, the counts, the percentage.

    `month` is `YYYY-MM` and defaults to the current month; `422` names the shape
    it wanted. Out of scope is `404`, and a leaver's month stays readable.
    """
    return service.month(
        session, employee_id, month or date.today().strftime("%Y-%m"), current_user
    )
