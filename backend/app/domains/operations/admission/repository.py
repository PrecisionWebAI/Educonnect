from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, or_
from sqlmodel import Session, select

from app.domains.academic.classroom.students.models import Enrollment, Student

from .models import AdmissionApplication
from .schemas import AdmissionApplicationCreate


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplication:
    # `target_academic_year_id` belongs to the enrollment request, not to the
    # student row; never let it reach the model.
    payload = application_in.model_dump(exclude={"target_academic_year_id"})
    db_app = AdmissionApplication.model_validate(payload)
    session.add(db_app)
    session.commit()
    session.refresh(db_app)
    return db_app


def get_applications(
    session: Session,
    skip: int = 0,
    limit: int | None = None,
    academic_year_id: UUID | None = None,
) -> list[AdmissionApplication]:
    """Newest first, optionally restricted to one academic year.

    Every row is a student the school has admitted, so the query carries no
    workflow filter at all - there is no draft to leave out. When the screen passes
    an academic year, the row must have that year's `enrollment`; without one the
    API keeps its old whole-roll answer for callers that intentionally want history.
    """
    query = select(AdmissionApplication).order_by(
        AdmissionApplication.created_on.desc(),
        AdmissionApplication.admission_number.desc(),
    )
    if academic_year_id is not None:
        query = query.join(
            Enrollment, Enrollment.student_id == AdmissionApplication.id
        ).where(Enrollment.academic_year_id == academic_year_id)
    query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return list(session.exec(query).all())


def separated() -> ColumnElement[bool]:
    """SQL form of `Student.separation`: a date **or** a reason means they left.

    Kept next to the model's own rule so `stats()` cannot drift from what a row
    reports (an empty reason string is "no reason", exactly like the model's
    `not self.separation_reason`).
    """
    return or_(
        Student.separation_date.is_not(None),
        and_(Student.separation_reason.is_not(None), Student.separation_reason != ""),
    )


def stats(
    session: Session, academic_year_id: UUID | None = None
) -> dict[str, int]:
    """The Admission screen's tiles, counted by the database for **this school**.

    An academic-year filter joins the year's enrollment; no filter keeps the old
    whole-roll answer. The SELECTs are plain ORM selects, so the tenant filter
    (`app/core/db.py`) scopes every one of them to the caller's school.
    """

    def scoped(statement, *, with_separation: bool = False):
        if academic_year_id is not None:
            statement = statement.join(
                Enrollment, Enrollment.student_id == Student.id
            ).where(Enrollment.academic_year_id == academic_year_id)
        if with_separation:
            statement = statement.where(separated())
        return statement

    students = session.exec(scoped(select(func.count(Student.id)))).one()
    inactive = session.exec(
        scoped(select(func.count(Student.id)), with_separation=True)
    ).one()
    mid_dropped = session.exec(
        scoped(
            select(func.count(Student.id)).where(
                Student.separation_session == "Incomplete Session"
            )
        )
    ).one()
    return {
        "students": int(students),
        "active": int(students) - int(inactive),
        "inactive": int(inactive),
        "mid_dropped": int(mid_dropped),
    }


def get_application_by_id(
    session: Session, application_id: UUID
) -> AdmissionApplication | None:
    return session.get(AdmissionApplication, application_id)


def save_application(
    session: Session, application: AdmissionApplication
) -> AdmissionApplication:
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def _sequence_of(value: str | None, prefix: str) -> int | None:
    """`"ADM-2026-0042"` -> `42`; None when the tail is not a number."""
    if not value or not value.startswith(prefix):
        return None
    tail = value.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def next_admission_number(session: Session) -> str:
    """`ADM-<year>-<nnnn>` - one past the highest number already handed out.

    The sequence is the school's own, read off `student.admission_number`, which is
    the **single** number a learner has: the form number it used to be minted from
    is gone (there was nowhere left to park it once the draft went), so a number is
    handed out exactly when a student is created and stays with that student for
    good.
    """
    prefix = f"ADM-{date.today().year}-"
    issued: list[str | None] = list(
        session.exec(
            select(Student.admission_number).where(
                Student.admission_number.startswith(prefix)
            )
        ).all()
    )
    numbers = [
        number
        for number in (_sequence_of(value, prefix) for value in issued)
        if number is not None
    ]
    return f"{prefix}{max(numbers, default=0) + 1:04d}"
