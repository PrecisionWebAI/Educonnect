"""One rule for "only this academic year's data": the current year is the context.

Three shapes of table, one helper each:

* a table that **owns** a year column (`classroomsubject`, `exam`, `enrollment`, ...) -
  `by_year_column`;
* a table that only has a **date** (attendance, class log, leave, ...) - `by_date_window`,
  the current year's `start_date .. end_date`;
* people and master data (student, employee, guardian, admission and hiring records) -
  never filtered.

A school with no current year keeps the unfiltered behaviour instead of showing an empty
screen, the same fallback `academic_year_window` uses.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session

from .academic_year_context import academic_year_for_date, current_academic_year
from .models import AcademicYear


def year_bounds(session: Session) -> tuple[date, date] | None:
    """The current year's first and last day, or `None` when none is open."""
    year = current_academic_year(session)
    return (year.start_date, year.end_date) if year is not None else None


def in_year(session: Session, day: date) -> bool:
    """Is `day` inside the current academic year? (`True` when no year is open.)"""
    bounds = year_bounds(session)
    return True if bounds is None else bounds[0] <= day <= bounds[1]


def by_date_window(session: Session, statement, column):
    """Keep only the rows whose `column` falls inside the current academic year."""
    bounds = year_bounds(session)
    if bounds is None:
        return statement
    return statement.where(column >= bounds[0], column <= bounds[1])


def by_year_column(session: Session, statement, column, *, include_null: bool = False):
    """Keep only the rows whose year `column` is the current academic year.

    `include_null` also keeps rows written before the column existed (the timetable
    reads those as "the current year").
    """
    year = current_academic_year(session)
    if year is None:
        return statement
    if include_null:
        return statement.where(or_(column == year.id, column.is_(None)))
    return statement.where(column == year.id)


_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def month_labels(session: Session) -> list[str] | None:
    """The month labels of the current year ("Apr 2026" ... "Mar 2027"), or `None`.

    The salary register stores its month as the label the screen prints, so the year is
    applied by listing the labels that belong to it.
    """
    bounds = year_bounds(session)
    if bounds is None:
        return None
    start, end = bounds
    labels: list[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        labels.append(f"{_MONTHS[month - 1]} {year}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return labels


def current_year_id(session: Session) -> UUID | None:
    year = current_academic_year(session)
    return year.id if year is not None else None


def viewing_other_year(session: Session) -> bool:
    """True when this request looks at a year that is not the one running today.

    `student.classroom_id` describes today's placement, so for any other year a class
    roll has to be read from that year's `enrollment` rows instead.
    """
    viewed = current_academic_year(session)
    real = academic_year_for_date(session, date.today())
    return bool(viewed and real and viewed.id != real.id)


def room_filter(session: Session, classroom_id):
    """The `WHERE` clause for "students of this class-section(s)" in the year on screen.

    `classroom_id` is one room id, or a collection of them.
    """
    from sqlmodel import select

    from app.domains.academic.classroom.students.models import Enrollment, Student

    many = not isinstance(classroom_id, UUID)
    rooms = list(classroom_id) if many else classroom_id
    if not viewing_other_year(session):
        return Student.classroom_id.in_(rooms) if many else Student.classroom_id == rooms
    viewed = current_academic_year(session)
    return Student.id.in_(
        select(Enrollment.student_id).where(
            Enrollment.academic_year_id == viewed.id,
            Enrollment.classroom_id.in_(rooms) if many else Enrollment.classroom_id == rooms,
            Enrollment.status == "active",
        )
    )


def placed(session: Session):
    """`(student_id, classroom_id)` pairs of the year on screen, as a subquery.

    For grouped counts (class cards, strength) that used to read the placement pointer:
    the running year still reads it, any other year reads its enrollments.
    """
    from sqlmodel import select

    from app.domains.academic.classroom.students.models import Enrollment, Student

    if not viewing_other_year(session):
        return select(
            Student.id.label("student_id"), Student.classroom_id.label("classroom_id")
        ).subquery()
    viewed = current_academic_year(session)
    return (
        select(
            Enrollment.student_id.label("student_id"),
            Enrollment.classroom_id.label("classroom_id"),
        )
        .where(Enrollment.academic_year_id == viewed.id, Enrollment.status == "active")
        .subquery()
    )


def todays_year(session: Session, today: date | None = None) -> AcademicYear | None:
    """The academic year **today falls in** (the calendar's truth), or `None`.

    Not the same thing as `current_academic_year`, which is the year somebody selected
    on screen: attendance may only be written in the year the clock is in.
    """
    return academic_year_for_date(session, today or date.today())
