from fastapi import HTTPException
from sqlmodel import Session

from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import repository
from .models import TeacherProfile
from .schemas import TeacherCreate, TeacherRead


def _build_teacher_read(session: Session, t: TeacherProfile) -> TeacherRead:
    user = session.get(User, t.user_id) if t.user_id else None
    return TeacherRead(
        id=t.id,
        user_id=t.user_id,
        department=t.department,
        qualification=t.qualification,
        joining_date=t.joining_date,
        staffCode=f"T-{100 + (t.id or 1)}",
        name=user.full_name if user else "Teacher",
        subject=t.department,
        phone="98xxxx201",
        email=user.email if user else "teacher@school.edu",
        status="Active" if (user and user.is_active) else "On Leave",
        classes=["10-A", "10-B"],
        workload=18,
    )


def get_teacher(session: Session, teacher_id: int) -> TeacherRead:
    teacher = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _build_teacher_read(session, teacher)


def get_teachers(
    session: Session, skip: int = 0, limit: int = 100
) -> list[TeacherRead]:
    raw_teachers = repository.get_teachers(session, skip=skip, limit=limit)
    return [_build_teacher_read(session, t) for t in raw_teachers]


def create_teacher(session: Session, teacher_in: TeacherCreate) -> TeacherProfile:
    # Validate user exists
    user = user_repository.get_user_by_id(session, user_id=teacher_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if teacher profile already exists for this user
    existing_teacher = repository.get_teacher_by_user_id(
        session, user_id=teacher_in.user_id
    )
    if existing_teacher:
        raise HTTPException(
            status_code=400, detail="Teacher profile already exists for this user"
        )

    return repository.create_teacher(session, teacher_in=teacher_in)
