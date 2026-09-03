import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.students import repository as student_repository
from app.domains.students.schemas import StudentCreate
from app.domains.users import repository as user_repository
from app.domains.users.models import RoleEnum, UserCreate

from . import repository
from .models import AdmissionApplication, AdmissionStatus
from .schemas import AdmissionApplicationCreate, AdmissionStatusUpdate


def create_application(
    session: Session, application_in: AdmissionApplicationCreate
) -> AdmissionApplication:
    return repository.create_application(session, application_in)


def get_applications(
    session: Session, status: str | None = None, skip: int = 0, limit: int = 100
) -> list[AdmissionApplication]:
    return repository.get_applications(session, status, skip, limit)


def update_application_status(
    session: Session, application_id: int, status_update: AdmissionStatusUpdate
) -> AdmissionApplication:
    application = repository.get_application_by_id(session, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = status_update.status
    if status_update.notes:
        application.notes = status_update.notes

    session.add(application)
    session.commit()
    session.refresh(application)

    # Auto-provision student account on approval
    if application.status == AdmissionStatus.approved:
        _provision_student_account(session, application)

    return application


def _provision_student_account(session: Session, app: AdmissionApplication):
    # Create User account for student
    # Note: in reality, we might create a user account for the parent too.
    # For now, let's create a student user account based on student name.
    username = f"{app.student_first_name.lower()}.{app.student_last_name.lower()}{str(uuid.uuid4())[:4]}"

    user_in = UserCreate(
        username=username,
        email=app.guardian_email,  # using guardian email for student
        password="changeme123",  # default password
        role=RoleEnum.student,
    )
    user = user_repository.create_user(session, user_in)

    # Create StudentProfile
    student_in = StudentCreate(
        user_id=user.id,
        admission_number=f"ADM-{app.id}",
        date_of_birth=app.date_of_birth,
        guardian_name=app.guardian_name,
        # grade_class_id can be assigned later
    )
    student_repository.create_student(session, student_in)
