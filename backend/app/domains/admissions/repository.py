from datetime import date

from sqlmodel import Session, select

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
    session: Session, application_id: int
) -> AdmissionApplication | None:
    return session.get(AdmissionApplication, application_id)


def save_application(
    session: Session, application: AdmissionApplication
) -> AdmissionApplication:
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def next_application_no(session: Session) -> str:
    """`ADM-<year>-<nnnn>` - one past the highest number already handed out."""
    prefix = f"ADM-{date.today().year}-"
    last = session.exec(
        select(AdmissionApplication.application_no)
        .where(AdmissionApplication.application_no.startswith(prefix))
        .order_by(AdmissionApplication.application_no.desc())
    ).first()
    sequence = 1
    if last:
        try:
            sequence = int(last.rsplit("-", 1)[1]) + 1
        except IndexError, ValueError:
            sequence = 1
    return f"{prefix}{sequence:04d}"
