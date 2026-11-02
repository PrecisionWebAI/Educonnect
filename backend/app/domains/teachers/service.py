from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.domains.academics.models import Classroom, Section, Subject
from app.domains.timetable.models import TimetablePeriod
from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import repository
from app.domains.staff.models import Employee
from .models import ClassTeacherAssignment, TeacherAssignment, TeacherSubject
from .schemas import TeacherCreate, TeacherRead


def _teacher_class_labels(session: Session, teacher_id: int) -> list[str]:
    """The class-section labels a teacher is attached to.

    Both assignment tables hold one row per class, so a teacher who runs two
    sections shows both - there is deliberately no UNIQUE on `teacher_id`, which
    is what lets one person be class teacher of more than one class.
    """
    labels: list[str] = []
    for model in (ClassTeacherAssignment, TeacherAssignment):
        rows = session.exec(
            select(model.classroom_id, model.section_id).where(
                model.teacher_id == teacher_id
            )
        ).all()
        for classroom_id, section_id in rows:
            classroom = session.get(Classroom, classroom_id)
            section = session.get(Section, section_id) if section_id else None
            label = classroom.name if classroom else ""
            if section:
                label = f"{label}-{section.name}"
            if label and label not in labels:
                labels.append(label)
    return sorted(labels)


def _build_teacher_read(session: Session, t: Employee) -> TeacherRead:
    user = session.get(User, t.user_id) if t.user_id else None
    subjects = session.exec(
        select(Subject.name)
        .join(TeacherSubject, TeacherSubject.subject_id == Subject.id)
        .where(TeacherSubject.teacher_id == t.id)
        .order_by(Subject.name)
    ).all()
    periods = session.exec(
        select(func.count())
        .select_from(TimetablePeriod)
        .where(TimetablePeriod.teacher_id == t.id)
    ).one()
    return TeacherRead(
        id=t.id,
        user_id=t.user_id,
        department=t.department,
        qualification=t.qualification,
        joining_date=t.joining_date,
        staffCode=f"T-{100 + (t.id or 1)}",
        name=user.full_name if user else "Teacher",
        subject=", ".join(subjects) if subjects else t.department,
        phone=t.phone or "",
        email=user.email if user else "teacher@school.edu",
        status="Active" if (user and user.is_active) else "On Leave",
        classes=_teacher_class_labels(session, t.id),
        workload=int(periods),
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


def create_teacher(session: Session, teacher_in: TeacherCreate) -> Employee:
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


def workload_matrix(session: Session) -> list["WorkloadMatrixRow"]:
    """Each teacher's real workload, from assignments + timetable periods."""
    from sqlmodel import func, select

    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.timetable.models import TimetablePeriod

    from .models import TeacherAssignment
    from .schemas import WorkloadMatrixRow

    rows: list[WorkloadMatrixRow] = []
    for teacher in session.exec(select(Employee)).all():
        user = session.get(User, teacher.user_id)
        assignments = session.exec(
            select(TeacherAssignment).where(TeacherAssignment.teacher_id == teacher.id)
        ).all()
        if not assignments:
            continue
        subjects: list[str] = []
        classes: list[str] = []
        for assignment in assignments:
            subject = session.get(Subject, assignment.subject_id)
            if subject and subject.name not in subjects:
                subjects.append(subject.name)
            classroom = session.get(Classroom, assignment.classroom_id)
            section = session.get(Section, assignment.section_id) if assignment.section_id else None
            label = classroom.name if classroom else ""
            if section:
                label = f"{label}-{section.name}"
            if label and label not in classes:
                classes.append(label)
        periods = session.exec(
            select(func.count())
            .select_from(TimetablePeriod)
            .where(TimetablePeriod.teacher_id == teacher.id)
        ).one()
        utilisation = min(100, int(periods / 22 * 100)) if periods else 0
        rows.append(
            WorkloadMatrixRow(
                staff=user.full_name if user else "",
                subject=", ".join(subjects),
                classes=classes,
                periods=int(periods),
                utilisation=utilisation,
            )
        )
    return rows


def staff_performance(session: Session) -> list["StaffPerformance"]:
    """Per-teacher summary computed from anonymous `teacherreview` rows.

    Only teachers with at least one rating appear (an empty list is the honest
    answer before any review has been collected). The `trend` compares the
    average of the most recent half of a teacher's reviews against the older
    half, so it reflects movement rather than an invented number.
    """
    from sqlmodel import select

    from .models import TeacherReview
    from .schemas import StaffPerformance

    rows: list[StaffPerformance] = []
    for teacher in session.exec(select(Employee)).all():
        user = session.get(User, teacher.user_id)
        reviews = session.exec(
            select(TeacherReview)
            .where(TeacherReview.teacher_id == teacher.id)
            .order_by(TeacherReview.created_at)
        ).all()
        if not reviews:
            continue
        ratings = [r.rating for r in reviews]
        rating = round(sum(ratings) / len(ratings), 1)
        score = round(rating / 5 * 100)
        trend = "flat"
        if len(ratings) >= 2:
            midpoint = len(ratings) // 2
            older = sum(ratings[:midpoint]) / midpoint
            recent = sum(ratings[midpoint:]) / (len(ratings) - midpoint)
            if recent > older:
                trend = "up"
            elif recent < older:
                trend = "down"
        rows.append(
            StaffPerformance(
                id=teacher.id or 0,
                staff=user.full_name if user else "",
                rating=rating,
                reviews=len(ratings),
                trend=trend,
                score=score,
            )
        )
    return rows
