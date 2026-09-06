from fastapi import HTTPException
from sqlmodel import Session

from app.domains.academics.models import GradeClass, Section
from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import repository
from .models import StudentProfile
from .schemas import StudentCreate, StudentRead


def _build_student_read(session: Session, s: StudentProfile) -> StudentRead:
    user = session.get(User, s.user_id) if s.user_id else None
    grade_class = (
        session.get(GradeClass, s.grade_class_id) if s.grade_class_id else None
    )
    sec = session.get(Section, s.section_id) if s.section_id else None

    return StudentRead(
        id=s.id,
        user_id=s.user_id,
        admission_number=s.admission_number,
        admissionNo=s.admission_number,
        date_of_birth=s.date_of_birth,
        guardian_name=s.guardian_name,
        guardian=s.guardian_name,
        grade_class_id=s.grade_class_id,
        section_id=s.section_id,
        name=user.full_name if user else "Student",
        className=grade_class.name if grade_class else "10",
        section=sec.name if sec else "A",
        gender="Male",
        phone="98xxxx001",
        email=user.email if user else "student@school.edu",
        status="Active" if (user and user.is_active) else "Inactive",
    )


def get_student(session: Session, student_id: int) -> StudentRead:
    student = repository.get_student_by_id(session, student_id=student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _build_student_read(session, student)


def get_students(
    session: Session, skip: int = 0, limit: int = 100
) -> list[StudentRead]:
    raw_students = repository.get_students(session, skip=skip, limit=limit)
    return [_build_student_read(session, s) for s in raw_students]


def create_student(session: Session, student_in: StudentCreate) -> StudentProfile:
    # Validate user exists
    user = user_repository.get_user_by_id(session, user_id=student_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if student already exists for this user
    existing_student = repository.get_student_by_user_id(
        session, user_id=student_in.user_id
    )
    if existing_student:
        raise HTTPException(
            status_code=400, detail="Student profile already exists for this user"
        )

    return repository.create_student(session, student_in=student_in)
