from datetime import date
from uuid import UUID
from sqlmodel import Session, select

from app.domains.students.models import StudentProfile

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
    session: Session, status: str | None = None, skip: int = 0, limit: int = 500
) -> list[AdmissionApplication]:
    """Newest first, so the Registered/Draft tables show the latest work on top."""
    query = select(AdmissionApplication)
    if status:
        query = query.where(AdmissionApplication.status == status)
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


def next_application_no(session: Session) -> str:
    """`ADM-<year>-<nnnn>` - one past the highest number already handed out.

    A number counts as handed out when it sits on an application **or** on a
    student: a `studentprofile.admission_number` *is* the application number it was
    created from, so a student whose application row was removed later still owns
    that number. Ignoring them made the number repeat, and the registration then
    failed for good on the student's unique admission number.
    """
    prefix = f"ADM-{date.today().year}-"
    issued: list[str | None] = list(
        session.exec(
            select(AdmissionApplication.application_no).where(
                AdmissionApplication.application_no.startswith(prefix)
            )
        ).all()
    )
    issued += list(
        session.exec(
            select(StudentProfile.admission_number).where(
                StudentProfile.admission_number.startswith(prefix)
            )
        ).all()
    )
    numbers = [
        number
        for number in (_sequence_of(value, prefix) for value in issued)
        if number is not None
    ]
    return f"{prefix}{max(numbers, default=0) + 1:04d}"
