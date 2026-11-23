"""The school's academic year: read it, open a new one, make one current.

The year is a single master (`academic_year`, 1 April -> 31 March). The navbar and
every screen read the one row whose `is_current` is true; opening a future year is
planning and does **not** move the school into it.

Rules:

* the window is derived from the label ("2026-27"), so a school cannot quietly run a
  different calendar from the one the score and chapter plan assume;
* at most one row is current per school (DB partial unique index), so switching clears
  the old flag in the same transaction;
* only the first year becomes current on creation; later years wait for an explicit
  switch;
* **only roles senior to the principal** (`system_admin`/`school_admin`, and future
  director/admin roles) may open or switch a year. The principal and vice-principal
  can read the current year but cannot move the school's calendar.

Reading the full list is `settings.read`; reading the current year is auth-only. The
current-year GET calls `academic_year_context.ensure_current_academic_year`, so a
school always has today's year by default; the list/other reads stay read-only.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.tenancy import tenant_of
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import (
    RequirePermission,
    get_current_active_user,
)
from app.domains.auth.roles import roles_of

from . import year_scope
from .academic_year_context import (
    academic_year_bounds,
    academic_year_for_date,
    academic_year_label,
    academic_year_start_year,
    current_academic_year,
    ensure_current_academic_year,
)
from .models import AcademicYear

router = APIRouter()

_can_read = RequirePermission("settings.read")
_can_manage = RequirePermission("academic_year.manage")

#: The principal and every role above. Keep the codenames that are actually seeded
#: (`system_admin`, `school_admin`, `principal`); director/admin are future school roles.
#: Vice principal, HOD, teacher, student and guardian only read the current year.
SENIOR_ACADEMIC_YEAR_ROLES = frozenset(
    {"system_admin", "school_admin", "director", "admin", "principal"}
)


class AcademicYearRead(BaseModel):
    """One row of the navbar's selector."""

    id: UUID
    name: str
    start_date: date
    end_date: date
    #: True for the year the screens treat as "now" - at most one per school.
    is_current: bool


class CurrentAcademicYearRead(BaseModel):
    """The current year for every signed-in role; `None` when none is open."""

    academic_year: AcademicYearRead | None = None


class AcademicYearIn(BaseModel):
    """A name ("2026-27") or a starting year (2026) - never a hand-typed window.

    The dates are derived, so "the year runs April to March" is a fact of the product
    rather than something each school types correctly. A name that is not a
    consecutive pair (`2026-2029`, `FY26`) is refused with a 422 instead of being
    stored and then read back as a different window.
    """

    name: str | None = Field(default=None, max_length=16)
    start_year: int | None = Field(default=None, ge=2000, le=2100)


class RequireSeniorAcademicYearManager:
    """The permission plus the role rule: only roles above the principal.

    A custom/legacy grant alone must not let the principal move the calendar. The
    permission stays the first gate (and keeps the matrix honest); this class adds
    the role check and exposes `permission` for the route-contract test.
    """

    permission = "academic_year.manage"

    def __call__(
        self,
        current_user: User = Depends(_can_manage),
    ) -> User:
        if not roles_of(current_user) & SENIOR_ACADEMIC_YEAR_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only the principal or a role above can change the academic year."
                ),
            )
        return current_user


_can_change = RequireSeniorAcademicYearManager()


def _start_year_from_label(name: str) -> int | None:
    """The starting year of "2026-27", or `None` when the label is not one."""
    head, _, tail = name.strip().partition("-")
    if len(head) != 4 or not head.isdigit() or len(tail) != 2 or not tail.isdigit():
        return None
    start = int(head)
    return start if int(tail) == (start + 1) % 100 else None


def _reads(row: AcademicYear) -> AcademicYearRead:
    return AcademicYearRead(
        id=row.id,
        name=row.name,
        start_date=row.start_date,
        end_date=row.end_date,
        is_current=row.is_current,
    )


@router.get("/academic-years/current", response_model=CurrentAcademicYearRead)
def read_current_academic_year(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    """The year every signed-in school role reads.

    A school should never be left without a running year: the first read ensures
    today's academic year exists (current), and later reads return the current row.
    Platform accounts with no school have no calendar to bootstrap, so they get null.
    """
    school_id = tenant_of(session)
    year = ensure_current_academic_year(session) if school_id is not None else None
    if year is not None:
        # A school that predates `enrollment` has students but no per-year row.
        # Backfilling only when the current year was *first* created missed every
        # school whose year already existed (the live database was one). The
        # function is idempotent and writes nothing once every placed student has
        # the year's row, so the read repairs the legacy gap instead of leaving
        # year-filtered screens empty forever.
        from app.domains.academic.classroom.students.placement import (
            backfill_current_enrollments,
        )

        # Only for the year **today falls in**: a student's class pointer describes
        # today's placement, so copying it into a next or previous year would enrol
        # everybody there without a promotion.
        todays = year_scope.todays_year(session)
        if todays is not None and todays.id == year.id:
            backfill_current_enrollments(session, year)
    return CurrentAcademicYearRead(
        academic_year=_reads(year) if year is not None else None
    )


@router.get("/academic-years", response_model=list[AcademicYearRead])
def read_academic_years(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every academic year this school has opened, newest window first."""
    rows = session.exec(
        select(AcademicYear).order_by(
            AcademicYear.start_date.desc()  # type: ignore[attr-defined]
        )
    ).all()
    return [_reads(row) for row in rows]


@router.post("/academic-years", response_model=AcademicYearRead, status_code=201)
def open_academic_year(
    payload: AcademicYearIn,
    session: Session = Depends(get_session),
    current_user=Depends(_can_change),
):
    """Open an academic year (`409` duplicate, `422` bad label).

    The first year a school opens becomes current - otherwise every screen would have
    no year to read. Every later one is planned and waits for somebody to switch.
    """
    if tenant_of(session) is None:
        raise HTTPException(
            status_code=409,
            detail="Select a school before opening an academic year.",
        )
    start_year = payload.start_year
    if payload.name is not None:
        parsed = _start_year_from_label(payload.name)
        if parsed is None:
            raise HTTPException(
                status_code=422,
                detail="An academic year is named for its two years in a row, e.g. 2026-27.",
            )
        if start_year is not None and start_year != parsed:
            raise HTTPException(
                status_code=422,
                detail="The name and the starting year describe different academic years.",
            )
        start_year = parsed
    if start_year is None:
        start_year = academic_year_start_year(date.today())

    name = academic_year_label(start_year)
    existing = session.exec(
        select(AcademicYear).where(AcademicYear.name == name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"The academic year {name} is already open."
        )

    start, end = academic_year_bounds(start_year)
    running = current_academic_year(session)
    if running is None:
        # A calendar row may already cover today without being flagged current.
        # Make that row current instead of making a newly opened next year current.
        covered = academic_year_for_date(session, date.today())
        if covered is not None:
            covered.is_current = True
            session.add(covered)
            session.commit()
            session.refresh(covered)
            running = covered

    # "Only one year ahead" is measured from the year that is really running (today's),
    # not from whichever year somebody happens to be looking at.
    running = year_scope.todays_year(session) or running
    if running is not None:
        running_start = _start_year_from_label(running.name)
        if running_start is not None and start_year != running_start + 1:
            expected = academic_year_label(running_start + 1)
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{running.name} is current; only {expected} can be opened next. "
                    "Past years stay available to switch to."
                ),
            )

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


def _reconcile_current_year(session: Session, year: AcademicYear) -> None:
    """Make the two "today" pointers agree with the year we just switched to.

    `student.classroom_id` is the directory's now, and `classroom.class_teacher_id`
    is the one-teacher shortcut the rest of the app still reads. The year's own
    rows remain the history: on a switch we copy the active enrollment and the open
    class-teacher assignment into those pointers, and clear a pointer that has no
    row in the new year rather than leaving last year's value showing.
    """
    from app.domains.academic.classroom.academics.models import Classroom
    from app.domains.academic.classroom.students.placement import (
        sync_placements_to_year,
    )
    from app.domains.academic.classroom.students.promotion.models import (
        ClassTeacherAssignment,
    )

    school_id = tenant_of(session)
    sync_placements_to_year(session, year)

    classrooms = session.exec(
        select(Classroom).where(Classroom.school_id == school_id)
    ).all()
    for classroom in classrooms:
        assignment = session.exec(
            select(ClassTeacherAssignment)
            .where(
                ClassTeacherAssignment.classroom_id == classroom.id,
                ClassTeacherAssignment.academic_year_id == year.id,
                ClassTeacherAssignment.effective_to.is_(None),
            )
            .order_by(ClassTeacherAssignment.effective_from.desc())
        ).first()
        classroom.class_teacher_id = (
            assignment.teacher_id if assignment is not None else None
        )
        session.add(classroom)


def reset_to_todays_year(session: Session) -> AcademicYear | None:
    """Make the year **today falls in** the school's current year (every login).

    The current year is meant to be the one that is really running. Somebody may switch
    to look at another year, but nobody should *start* a session there: each sign-in
    puts the school back on the running year. A school with no year covering today is
    left as it is. Returns the running year, or `None`.
    """
    real = year_scope.todays_year(session)
    if real is None:
        return None
    running = session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).all()
    if len(running) == 1 and running[0].id == real.id:
        return real
    for other in running:
        other.is_current = False
        session.add(other)
    session.flush()
    real.is_current = True
    session.add(real)
    _reconcile_current_year(session, real)
    session.commit()
    session.refresh(real)
    return real


@router.patch("/academic-years/{year_id}/current", response_model=AcademicYearRead)
def make_academic_year_current(
    year_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_change),
):
    """Make one academic year the one the screens read (`404` unknown id).

    The old flag is cleared in the same transaction: `uq_academicyear_one_current`
    would refuse two current rows, and a half-applied switch would leave the school
    with none.
    """
    row = session.get(AcademicYear, year_id)
    if row is None or row.school_id != tenant_of(session):
        raise HTTPException(status_code=404, detail="Academic year not found")

    if not row.is_current:
        running = session.exec(
            select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
        ).all()
        for other in running:
            other.is_current = False
            session.add(other)
        # Clear the old flag first: the partial unique index checks each
        # statement, so setting the new flag before the old one is flushed would
        # briefly leave two current rows and be refused.
        session.flush()
        row.is_current = True
        session.add(row)
        _reconcile_current_year(session, row)
        session.commit()
        session.refresh(row)
    return _reads(row)
