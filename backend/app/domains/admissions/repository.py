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
    session: Session, status: str | None = None, skip: int = 0, limit: int = 100
) -> list[AdmissionApplication]:
    query = select(AdmissionApplication)
    if status:
        query = query.where(AdmissionApplication.status == status)
    return list(session.exec(query.offset(skip).limit(limit)).all())


def get_application_by_id(
    session: Session, application_id: int
) -> AdmissionApplication | None:
    return session.get(AdmissionApplication, application_id)
