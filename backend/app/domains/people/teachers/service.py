"""The read models behind the Teachers & Staff screen.

Four tabs read from here (directory, workload, leave, performance) plus the
summary tiles above them, and they all describe the same set of people: whoever
is on the teaching roll. That is why the employee list is read once by
`repository.teaching_employees` and shared - a tile that counted a different set
from the table underneath it is how the old screen ended up reporting "12 active"
over a list of nine.

Cost is bounded per request, not per row: each fact (subjects, class-sections,
timetable load, today's leave, ratings) is one statement for the whole page
instead of one per teacher.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    Classroom,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.admin.users import repository as user_repository
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from . import labels, repository, scope
from .models import TeacherReview, TeacherSubject
from .schemas import (
    StaffPerformance,
    StaffSummary,
    TeacherCreate,
    TeacherRead,
    WorkloadMatrixRow,
)


def _reads(session: Session, teachers: list[Employee]) -> list[TeacherRead]:
    """One directory row per employee, from a fixed number of reads.

    Seven statements for the whole page (users, subjects, timetable load, the two
    assignment tables, the class-section labels, today's leave). Reading them per
    teacher was ~550 round trips on a seeded school.
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

    periods = repository.period_counts(session, teacher_ids)

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
    room_labels = labels_by_section(
        session, [room for room_ids in rooms.values() for room in room_ids]
    )

    on_leave = repository.approved_leave_today(session, date.today())

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
                staffCode=teacher.employee_code,
                name=user.full_name if user else "",
                # No fallback to the department: "takes no subject" and "sits in
                # the Science department" are two different facts, and the table
                # has a column for each.
                subject=", ".join(subjects.get(teacher.id, [])),
                phone=teacher.phone or "",
                email=teacher.email or (user.email if user else ""),
                status=labels.employee_status(
                    deactivated_at=teacher.deactivated_at,
                    left_on=teacher.left_on,
                    on_leave=teacher.user_id in on_leave,
                ),
                classes=sorted(
                    {
                        room_labels[room]
                        for room in rooms.get(teacher.id, set())
                        if room in room_labels
                    }
                ),
                workload=periods.get(teacher.id, 0),
            )
        )
    return reads


def get_teacher(
    session: Session, teacher_id: UUID, user: User | None = None
) -> TeacherRead:
    """One employee, if this caller may see them.

    A teacher asking for a colleague's id gets `404`, not `403`: the answer must
    not confirm that somebody else's id exists.
    """
    teacher = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    visible = scope.visible_employee_ids(session, user)
    if teacher is None or (visible is not None and teacher.id not in visible):
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _reads(session, [teacher])[0]


def get_teachers(
    session: Session,
    *,
    user: User | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[TeacherRead]:
    """The directory: the caller's own scope of the school, filtered by the screen."""
    rows = repository.get_teachers(
        session,
        visible_ids=scope.visible_employee_ids(session, user),
        q=q,
        department=department,
        status=status,
        skip=skip,
        limit=limit,
    )
    return _reads(session, rows)


def staff_summary(session: Session) -> StaffSummary:
    """The tiles above the directory, counted over the whole teaching roll.

    Counted here rather than added up from the rows the browser happens to hold:
    a filter or a page must not change "Total staff".
    """
    teachers = repository.teaching_employees(session)
    on_leave = repository.approved_leave_today(session, date.today())
    periods = repository.period_counts(session, [teacher.id for teacher in teachers])

    counts = {labels.ACTIVE: 0, labels.ON_LEAVE: 0, labels.INACTIVE: 0}
    without_timetable = 0
    for teacher in teachers:
        status = labels.employee_status(
            deactivated_at=teacher.deactivated_at,
            left_on=teacher.left_on,
            on_leave=teacher.user_id in on_leave,
        )
        counts[status] += 1
        if status != labels.INACTIVE and not periods.get(teacher.id):
            without_timetable += 1

    return StaffSummary(
        total=len(teachers),
        active=counts[labels.ACTIVE],
        on_leave_today=counts[labels.ON_LEAVE],
        inactive=counts[labels.INACTIVE],
        periods_per_week=sum(periods.values()),
        without_timetable=without_timetable,
    )


def workload_matrix(session: Session) -> list[WorkloadMatrixRow]:
    """Each teacher's real load, from their assignments and timetable periods.

    Four statements for the page. Everybody on the teaching roll gets a row - a
    teacher with no subject or no period yet is a fact the principal wants to
    see, not a row to hide. `capacity` is the timetable's own week, so
    "utilisation" compares two real numbers.
    """
    teachers = repository.teaching_employees(session)
    if not teachers:
        return []

    teacher_ids = [teacher.id for teacher in teachers]
    capacity = repository.week_capacity(session)
    periods = repository.period_counts(session, teacher_ids)
    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(User.id.in_([teacher.user_id for teacher in teachers]))
        ).all()
    }

    subjects: dict[UUID, set[str]] = {}
    rooms: dict[UUID, set[UUID]] = {}
    for teacher_id, subject_name, room_id in session.exec(
        select(SubjectTeacher.teacher_id, Subject.name, SubjectTeacher.classroom_id)
        .join(Subject, Subject.id == SubjectTeacher.subject_id)
        .where(SubjectTeacher.teacher_id.in_(teacher_ids))
    ).all():
        subjects.setdefault(teacher_id, set()).add(subject_name)
        rooms.setdefault(teacher_id, set()).add(room_id)
    room_labels = labels_by_section(
        session, [room for room_ids in rooms.values() for room in room_ids]
    )

    rows: list[WorkloadMatrixRow] = []
    for teacher in teachers:
        load = periods.get(teacher.id, 0)
        rows.append(
            WorkloadMatrixRow(
                id=teacher.id,
                staff=names.get(teacher.user_id, ""),
                subject=", ".join(sorted(subjects.get(teacher.id, set()))),
                classes=sorted(
                    {
                        room_labels[room]
                        for room in rooms.get(teacher.id, set())
                        if room in room_labels
                    }
                ),
                periods=load,
                capacity=capacity,
                utilisation=labels.utilisation(load, capacity),
            )
        )
    return rows


def _trend(ratings: list[int]) -> str:
    """Which way the ratings moved: recent half against the older half.

    A teacher with one rating has no movement to report, and "flat" is the
    honest answer for that - not a made-up direction.
    """
    if len(ratings) < 2:
        return "flat"
    midpoint = len(ratings) // 2
    older = sum(ratings[:midpoint]) / midpoint
    recent = sum(ratings[midpoint:]) / (len(ratings) - midpoint)
    if recent > older:
        return "up"
    if recent < older:
        return "down"
    return "flat"


def staff_performance(session: Session) -> list[StaffPerformance]:
    """Per-teacher summary computed from the anonymous `teacherreview` rows.

    Only teachers with at least one rating appear: an empty list is the honest
    answer before any review exists, and a fabricated 0 would read as a bad
    score rather than "not rated yet".
    """
    reviews = session.exec(
        select(TeacherReview.teacher_id, TeacherReview.rating).order_by(
            TeacherReview.teacher_id,  # type: ignore[arg-type]
            TeacherReview.created_at,  # type: ignore[arg-type]
        )
    ).all()
    if not reviews:
        return []

    ratings: dict[UUID, list[int]] = {}
    for teacher_id, rating in reviews:
        ratings.setdefault(teacher_id, []).append(rating)

    teachers = {
        teacher.id: teacher for teacher in repository.teaching_employees(session)
    }
    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(
                User.id.in_([teacher.user_id for teacher in teachers.values()])
            )
        ).all()
    }

    rows: list[StaffPerformance] = []
    for teacher_id, values in ratings.items():
        teacher = teachers.get(teacher_id)
        if teacher is None:
            # A review of somebody who is no longer on the roll: keep the number
            # out of the screen the roll defines, but do not drop the review row.
            continue
        rating = round(sum(values) / len(values), 1)
        rows.append(
            StaffPerformance(
                id=teacher_id,
                staff=names.get(teacher.user_id, ""),
                rating=rating,
                reviews=len(values),
                trend=_trend(values),  # type: ignore[arg-type]
                score=round(rating / 5 * 100),
            )
        )
    return sorted(rows, key=lambda row: row.staff)


def create_teacher(session: Session, teacher_in: TeacherCreate) -> Employee:
    """Add a teacher profile for an existing login.

    The employee row is the teaching record; the `teacher` role is what puts them
    on the roll the directory reads.
    """
    user = user_repository.get_user_by_id(session, user_id=teacher_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if repository.get_teacher_by_user_id(session, user_id=teacher_in.user_id):
        raise HTTPException(
            status_code=400, detail="Teacher profile already exists for this user"
        )

    return repository.create_teacher(session, teacher_in=teacher_in)
