"""Shared test helpers for the classroom-owned subject model.

A subject belongs to one class-section (`classroomsubject`). Tests that used to build a
school-wide `Subject` and name its id everywhere now build the section's own row with
`section_subject`, and use its id as `classroom_subject_id`.
"""

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    ClassroomSubject,
)
from app.domains.admin.settings.models import AcademicYear


def ensure_year(session: Session) -> AcademicYear:
    """The school's current academic year; create 2026-27 when the test has none."""
    year = session.exec(select(AcademicYear).where(AcademicYear.is_current)).first()
    if year is not None:
        return year
    year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
        school_id=tenant_of(session),
    )
    session.add(year)
    session.commit()
    session.refresh(year)
    return year


def section_subject(
    session: Session,
    classroom_id: UUID,
    name: str,
    *,
    code: str | None = None,
    year: AcademicYear | None = None,
) -> ClassroomSubject:
    """One active subject of one section, in the current academic year."""
    year = year or ensure_year(session)
    row = ClassroomSubject(
        classroom_id=classroom_id,
        name=name,
        code=code,
        academic_year_id=year.id,
        status=COURSE_ACTIVE,
        school_id=tenant_of(session),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class named_subject:  # noqa: N801 - reads like a value at the call sites
    """A subject that is only a **name**.

    A section subject has no school-wide row behind it any more; tests that used to
    create one to get a name to type into "Add subject" now just carry the name.
    """

    def __init__(self, name: str) -> None:
        self.name = name
