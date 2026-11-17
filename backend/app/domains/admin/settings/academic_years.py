"""The school's session year: read it, open a new one, make one current.

Three routes, and they exist because the year was previously **only** created as a
side effect of a placement (`academic_year` is opened the first time a child is put
in a class). A school could therefore not say "this is the year we are running" - the
calendar decided for it - and the navbar had nothing to show.

The rules the routes keep:

* a session is **1 April -> 31 March**, derived from its name ("2026-27"), so a school
  cannot open a June-to-April window and quietly measure a different year than the one
  the score and the chapter plan assume;
* **at most one row is current** per school. It is enforced by a partial unique index
  in the database, so the switch below clears the old flag in the same transaction
  rather than relying on a screen to be careful;
* opening a year does **not** move the school into it. Planning next year in advance
  is normal; the school must keep showing the year that is running until somebody
  says otherwise. Only the first year of a school becomes current on creation,
  because otherwise the screens would have no year at all.

Reading is `settings.read` (the year is printed on most screens); switching it is
`academic_year.manage`, which is the office's decision, not a department's.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.tenancy import tenant_of
from app.domains.auth.dependencies import RequirePermission

from .models import AcademicYear

router = APIRouter()

_can_read = RequirePermission("settings.read")
_can_manage = RequirePermission("academic_year.manage")

#: The session months: 1 April -> 31 March.
SESSION_START_MONTH = 4
SESSION_END_MONTH = 3


class SessionYearRead(BaseModel):
    """One row of the navbar's selector."""

    id: UUID
    name: str
    start_date: date
    end_date: date
    #: True for the year the screens treat as "now" - at most one per school.
    is_current: bool


class SessionYearIn(BaseModel):
    """A name ("2026-27") or a starting year (2026) - never a hand-typed window.

    The dates are derived, so "the year runs April to March" is a fact of the product
    rather than something each school types correctly. A name that is not a
    consecutive pair (`2026-2029`, `FY26`) is refused with a 422 instead of being
    stored and then read back as a different window.
    """

    name: str | None = Field(default=None, max_length=16)
    start_year: int | None = Field(default=None, ge=2000, le=2100)


def _label(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _start_year_from_label(name: str) -> int | None:
    """The starting year of "2026-27", or `None` when the label is not one."""
    head, _, tail = name.strip().partition("-")
    if len(head) != 4 or not head.isdigit() or len(tail) != 2 or not tail.isdigit():
        return None
    start = int(head)
    return start if int(tail) == (start + 1) % 100 else None


def _bounds(start_year: int) -> tuple[date, date]:
    return (
        date(start_year, SESSION_START_MONTH, 1),
        date(start_year + 1, SESSION_END_MONTH, 31),
    )


def _today_session_year(today: date | None = None) -> int:
    """The starting year of the session `today` falls in (April onwards is next)."""
    day = today or date.today()
    return day.year if day.month >= SESSION_START_MONTH else day.year - 1


def _reads(row: AcademicYear) -> SessionYearRead:
    return SessionYearRead(
        id=row.id,
        name=row.name,
        start_date=row.start_date,
        end_date=row.end_date,
        is_current=row.is_current,
    )


@router.get("/session-years", response_model=list[SessionYearRead])
def read_session_years(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every session this school has opened, newest window first."""
    rows = session.exec(
        select(AcademicYear).order_by(
            AcademicYear.start_date.desc()  # type: ignore[attr-defined]
        )
    ).all()
    return [_reads(row) for row in rows]


@router.post("/session-years", response_model=SessionYearRead, status_code=201)
def open_session_year(
    payload: SessionYearIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Open a session (`409` when the name is already open, `422` on a bad label).

    The first year a school opens becomes current - otherwise every screen would have
    no session to read. Every later one is planned and waits for somebody to switch.
    """
    start_year = payload.start_year
    if payload.name is not None:
        parsed = _start_year_from_label(payload.name)
        if parsed is None:
            raise HTTPException(
                status_code=422,
                detail="A session is named for its two years in a row, e.g. 2026-27.",
            )
        if start_year is not None and start_year != parsed:
            raise HTTPException(
                status_code=422,
                detail="The name and the starting year describe different sessions.",
            )
        start_year = parsed
    if start_year is None:
        start_year = _today_session_year()

    name = _label(start_year)
    existing = session.exec(
        select(AcademicYear).where(AcademicYear.name == name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"The session {name} is already open."
        )

    start, end = _bounds(start_year)
    running = session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()

    row = AcademicYear(
        name=name,
        start_date=start,
        end_date=end,
        is_current=running is None,
        school_id=tenant_of(session),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _reads(row)


@router.patch("/session-years/{year_id}/current", response_model=SessionYearRead)
def make_session_current(
    year_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Make one session the one the screens read (`404` for an unknown id).

    The old flag is cleared in the same transaction: `uq_academicyear_one_current`
    would refuse two current rows, and a half-applied switch would leave the school
    with none.
    """
    row = session.get(AcademicYear, year_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session year not found")

    if not row.is_current:
        running = session.exec(
            select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
        ).all()
        for other in running:
            other.is_current = False
            session.add(other)
        row.is_current = True
        session.add(row)
        session.commit()
        session.refresh(row)
    return _reads(row)
