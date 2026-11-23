"""The one place that answers: which academic year is current, and what date belongs where.

The product has a single ``academic_year`` master (1 April -> 31 March). Screens and
services must ask this module instead of repeating the query:

* :func:`current_academic_year` is a read. It never creates a row; the dedicated
  current-year endpoint calls :func:`ensure_current_academic_year`, so a school always
  has today's year by default without every other GET mutating the calendar.
* :func:`require_current_academic_year` turns "nothing is open" into the same friendly
  ``409`` everywhere.
* :func:`academic_year_for_date` maps a dated row (attendance, salary, holiday) to the
  academic year that contains it.
* :func:`ensure_current_academic_year` is the *onboarding* path used by placement: it
  uses the date-covered row when one exists, and only then creates the row for today.

All reads are tenant-scoped by the request session (``school_id``), so one school's
calendar can never answer another school's question.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.admin.settings.models import AcademicYear

#: The school year: 1 April -> 31 March.
ACADEMIC_YEAR_START_MONTH = 4
ACADEMIC_YEAR_END_MONTH = 3


def academic_year_label(start_year: int) -> str:
    """``2026`` -> ``2026-27`` - the way the school writes the year."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def academic_year_start_year(today: date) -> int:
    """The starting calendar year of the academic year containing ``today``."""
    return today.year if today.month >= ACADEMIC_YEAR_START_MONTH else today.year - 1


def academic_year_bounds(start_year: int) -> tuple[date, date]:
    """``(1 April start_year, 31 March start_year + 1)``."""
    return (
        date(start_year, ACADEMIC_YEAR_START_MONTH, 1),
        date(start_year + 1, ACADEMIC_YEAR_END_MONTH, 31),
    )


def current_academic_year(session: Session) -> AcademicYear | None:
    """The year the screens read, or ``None`` when the school has not opened one.

    Deliberately read-only: a GET must not create a calendar row. Placement uses
    :func:`ensure_current_academic_year` when onboarding needs one.
    """
    # The year this request was asked to look at (`X-Academic-Year`), when there is one;
    # otherwise the school's running year.
    chosen = session.info.get("academic_year_id")
    if chosen is not None:
        row = session.exec(
            select(AcademicYear).where(AcademicYear.id == chosen)
        ).first()
        if row is not None:
            return row
    return session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()


def current_academic_year_id(session: Session) -> UUID | None:
    """The current year's id, or ``None``. Kept separate for callers that need no row."""
    year = current_academic_year(session)
    return year.id if year is not None else None


def academic_year_window(
    session: Session,
    academic_year_id: UUID | None = None,
    *,
    all_years: bool = False,
) -> tuple[date | None, date | None, AcademicYear | None]:
    """The date window a report should use.

    `all_years=True` means no filter; a named year must belong to the tenant (a
    foreign id is a `404`); otherwise the current year is the default. A school
    with no current year keeps its historical all-years behavior rather than
    showing an empty report.
    """
    if all_years:
        return None, None, None

    year: AcademicYear | None
    if academic_year_id is not None:
        year = session.get(AcademicYear, academic_year_id)
        if year is None or year.school_id != tenant_of(session):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Academic year not found")
    else:
        year = current_academic_year(session)
    if year is None:
        return None, None, None
    return year.start_date, year.end_date, year


def require_current_academic_year(session: Session) -> AcademicYear:
    """The current year, or a friendly ``409`` when the school has not set one."""
    from fastapi import HTTPException

    year = current_academic_year(session)
    if year is None:
        raise HTTPException(
            status_code=409,
            detail=("No academic year is open. Open the current academic year first."),
        )
    return year


def academic_year_for_date(session: Session, day: date) -> AcademicYear | None:
    """The year whose ``start_date``/``end_date`` contains ``day``.

    Dates are the truth; we do not guess from the label. A date outside every opened
    window returns ``None`` (legacy/out-of-range data).
    """
    return session.exec(
        select(AcademicYear)
        .where(AcademicYear.start_date <= day)
        .where(AcademicYear.end_date >= day)
    ).first()


def ensure_current_academic_year(
    session: Session, today: date | None = None
) -> AcademicYear:
    """The current year for onboarding, creating it only when nothing covers today.

    Order matters: an existing current row wins; otherwise a row that already covers
    today is marked current (the calendar already exists); only when neither exists do
    we create today's year. The unique indexes make the create race-safe.
    """
    found = current_academic_year(session)
    if found is not None:
        return found

    day = today or date.today()
    covered = academic_year_for_date(session, day)
    if covered is not None:
        covered.is_current = True
        session.add(covered)
        session.commit()
        session.refresh(covered)
        return covered

    start_year = academic_year_start_year(day)
    start, end = academic_year_bounds(start_year)
    name = academic_year_label(start_year)
    row = AcademicYear(
        name=name,
        start_date=start,
        end_date=end,
        is_current=True,
        school_id=tenant_of(session),
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(AcademicYear).where(AcademicYear.name == name)
        ).first()
        if existing is None:  # pragma: no cover - the unique keys guarantee one
            raise
        if not existing.is_current:
            existing.is_current = True
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing
    session.refresh(row)
    return row
