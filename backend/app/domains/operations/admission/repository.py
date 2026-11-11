from datetime import date
from uuid import UUID
from sqlalchemy import ColumnElement, and_, func, or_
from sqlmodel import Session, select

from app.domains.academic.classroom.students.models import Student

from .models import AdmissionApplication
from .schemas import AdmissionApplicationCreate


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplication:
    db_app = AdmissionApplication.model_validate(application_in)
    session.add(db_app)
    session.commit()
    session.refresh(db_app)
    return db_app


def get_applications(
    session: Session, skip: int = 0, limit: int | None = None
) -> list[AdmissionApplication]:
    """Newest first, so the list shows the school's latest admission on top.

    Every row is a student the school has admitted, so the query carries no
    workflow filter at all - there is no draft to leave out.

    `limit=None` - the default - is the **whole roll**: the screen filters and
    paginates the rows it was given, so a cap below the roll silently hides
    students (and the tiles used to be derived from this list, which is how they
    came to show the cap). The order is the admission date and then the number the
    school minted - a `date` alone puts a whole day's admissions in arbitrary
    order, and `id` is a UUID, so it never meant "newest".
    """
    query = (
        select(AdmissionApplication)
        .order_by(
            AdmissionApplication.created_on.desc(),
            AdmissionApplication.admission_number.desc(),
        )
        .offset(skip)
    )
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


def stats(session: Session) -> dict[str, int]:
    """The Admission screen's tiles, counted by the database for **this school**.

    Three counts over one table: the roll, the students who left, and those who
    left mid-session. The SELECTs are plain ORM selects, so the tenant filter
    (`app/core/db.py`) scopes every one of them to the caller's school.
    """
    students = session.exec(select(func.count(Student.id))).one()
    inactive = session.exec(select(func.count(Student.id)).where(separated())).one()
    mid_dropped = session.exec(
        select(func.count(Student.id)).where(
            Student.separation_session == "Incomplete Session"
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
