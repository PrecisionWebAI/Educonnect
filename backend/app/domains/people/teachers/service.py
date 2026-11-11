from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.domains.academic.classroom.academics.models import ClassName, Classroom, Section, Subject, SubjectTeacher
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.users import repository as user_repository
from app.domains.admin.users.models import User

from . import repository
from app.domains.people.staff.models import Employee
from .models import TeacherSubject
from .schemas import TeacherCreate, TeacherRead


def _teacher_reads(session: Session, teachers: list[Employee]) -> list[TeacherRead]:
    """Rows for the Teachers table - six reads for the whole page.

    The screen lists every teacher with their subjects, their class-sections and
    their timetable load. Reading that per teacher was ~550 round trips on a seeded
    school (the page took minutes), so each fact is read once for all of them.
    """
    if not teachers:
        return []
    teacher_ids = [teacher.id for teacher in teachers if teacher.id is not None]
    user_ids = [teacher.user_id for teacher in teachers if teacher.user_id]
    users = (
        {
            user.id: user
            for user in session.exec(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )

    subjects: dict[UUID, list[str]] = {}
    for teacher_id, name in session.exec(
        select(TeacherSubject.teacher_id, Subject.name)
        .join(Subject, TeacherSubject.subject_id == Subject.id)
        .where(TeacherSubject.teacher_id.in_(teacher_ids))
        .order_by(Subject.name)  # type: ignore[arg-type]
    ).all():
        subjects.setdefault(teacher_id, []).append(name)

    periods = dict(
        session.exec(
            select(TimetablePeriod.teacher_id, func.count())
            .where(TimetablePeriod.teacher_id.in_(teacher_ids))
            .group_by(TimetablePeriod.teacher_id)  # type: ignore[arg-type]
        ).all()
    )

    # A teacher is attached to a class-section either as its class teacher or by
    # taking a subject in it; both are collected before the labels are read once.
    rooms: dict[UUID, set[UUID]] = {}
    for teacher_id, room_id in session.exec(
        select(Classroom.class_teacher_id, Classroom.id).where(
            Classroom.class_teacher_id.in_(teacher_ids)
        )
    ).all():
        rooms.setdefault(teacher_id, set()).add(room_id)
    for teacher_id, room_id in session.exec(
        select(SubjectTeacher.teacher_id, SubjectTeacher.classroom_id).where(
            SubjectTeacher.teacher_id.in_(teacher_ids)
        )
    ).all():
        rooms.setdefault(teacher_id, set()).add(room_id)
    labels = labels_by_section(
        session, [room for room_ids in rooms.values() for room in room_ids]
    )

    reads: list[TeacherRead] = []
    for teacher in teachers:
        user = users.get(teacher.user_id) if teacher.user_id else None
        reads.append(
            TeacherRead(
                id=teacher.id,
                user_id=teacher.user_id,
                department=teacher.department,
                qualification=teacher.qualification,
                joining_date=teacher.joining_date,
                staffCode=teacher.employee_code
                or f"T-{str(teacher.id).split('-')[0].upper()}",
                name=user.full_name if user else "Teacher",
                subject=", ".join(subjects.get(teacher.id, [])) or teacher.department,
                phone=teacher.phone or "",
                email=user.email if user else "teacher@school.edu",
                status="Active" if (user and user.is_active) else "On Leave",
                classes=sorted(
                    {labels[room] for room in rooms.get(teacher.id, set()) if room in labels}
                ),
                workload=int(periods.get(teacher.id, 0)),
            )
        )
    return reads


def get_teacher(session: Session, teacher_id: UUID) -> TeacherRead:
    teacher = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _teacher_reads(session, [teacher])[0]


def get_teachers(
    session: Session, skip: int = 0, limit: int = 100
) -> list[TeacherRead]:
    return _teacher_reads(
        session, repository.get_teachers(session, skip=skip, limit=limit)
    )


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

    from app.domains.academic.classroom.academics.models import ClassName, Classroom, Section, Subject, SubjectTeacher
    from app.domains.academic.classroom.timetable.models import TimetablePeriod

    from .schemas import WorkloadMatrixRow

    rows: list[WorkloadMatrixRow] = []
    for teacher in session.exec(select(Employee)).all():
        user = session.get(User, teacher.user_id)
        assignments = session.exec(
            select(SubjectTeacher).where(SubjectTeacher.teacher_id == teacher.id)
        ).all()
        if not assignments:
            continue
        subjects: list[str] = []
        classes: list[str] = []
        for assignment in assignments:
            subject = session.get(Subject, assignment.subject_id)
            if subject and subject.name not in subjects:
                subjects.append(subject.name)
            section = session.get(Classroom, assignment.classroom_id)
            classroom = session.get(ClassName, section.class_id) if section else None
            letter = session.get(Section, section.section_id) if section else None
            label = classroom.classname if classroom else ""
            if letter:
                label = f"{label}-{letter.section_name}"
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
                id=teacher.id,
                staff=user.full_name if user else "",
                rating=rating,
                reviews=len(ratings),
                trend=trend,
                score=score,
            )
        )
    return rows
