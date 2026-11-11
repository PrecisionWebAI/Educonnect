from datetime import date
from uuid import UUID
from sqlmodel import Session, select

from app.domains.students.models import Student

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
    session: Session, skip: int = 0, limit: int = 500
) -> list[AdmissionApplication]:
    """Newest first, so the list shows the school's latest admission on top.

    Every row is a student the school has admitted, so the query carries no
    workflow filter at all - there is no draft to leave out.
    """
    query = select(AdmissionApplication)
    query = query.order_by(AdmissionApplication.id.desc()).offset(skip).limit(limit)
    return list(session.exec(query).all())


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
