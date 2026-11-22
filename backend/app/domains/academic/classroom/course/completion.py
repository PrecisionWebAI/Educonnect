"""The **one** calculation of "how much of the course is done".

Four screens need this number - the Classroom card, the Course tab, the Teachers
performance score and the Course tab's "ahead/behind" badge - so it is computed once,
here, from `chapter` + `chapter_progress`. There is no stored counter anywhere: a
denormalised `chapters_done` would have to be incremented on tick, decremented on
untick, re-checked when a chapter is added and repaired the first time somebody edited
the plan (which is exactly the table Phase 5 dropped).

"Done" always means **status = Completed** in `chapter_progress`. Pending and
"In progress" chapters count towards the total and not towards the done number.
"""

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    Classroom,
    SubjectTeacher,
)
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    ClassroomSubject,
)
from app.domains.admin.settings.academic_year_context import (
    current_academic_year as read_current_academic_year,
)
from app.domains.admin.settings.models import AcademicYear


def current_academic_year(session: Session) -> AcademicYear | None:
    """The academic year the screens treat as "now", or `None` when none is open.

    A **read**: unlike placement onboarding, it never creates the row. When it is
    missing, plans from every year are counted together - the honest answer for a
    school that has not set its calendar.
    """
    return read_current_academic_year(session)


def _chapter_totals(session: Session) -> dict[UUID, int]:
    """{classroom_subject_id: chapters planned} for the current academic year."""
    year = current_academic_year(session)
    statement = select(Chapter.classroom_subject_id, func.count(Chapter.id)).group_by(
        Chapter.classroom_subject_id
    )
    if year is not None:
        statement = statement.where(Chapter.academic_year_id == year.id)
    return {
        course_id: int(chapters)
        for course_id, chapters in session.exec(statement).all()
    }


def _done_totals(session: Session) -> dict[UUID, int]:
    """{classroom_subject_id: chapters completed}."""
    statement = (
        select(Chapter.classroom_subject_id, func.count(Chapter.id))
        .where(Chapter.status == CHAPTER_COMPLETED)
        .group_by(Chapter.classroom_subject_id)
    )
    return {course_id: int(done) for course_id, done in session.exec(statement).all()}


def _rooms_by_class(session: Session) -> dict[UUID, list[UUID]]:
    """{class_id: [classroom_id, ...]} for this school - one query, not one per row."""
    rooms: dict[UUID, list[UUID]] = {}
    for room_id, class_id in session.exec(
        select(Classroom.id, Classroom.class_id)
    ).all():
        rooms.setdefault(class_id, []).append(room_id)
    return rooms


def by_section(session: Session) -> dict[UUID, tuple[int, int]]:
    """{classroom_id: (done, total)} for every class-section that has a plan."""
    totals = _chapter_totals(session)
    if not totals:
        return {}

    done = _done_totals(session)
    result: dict[UUID, tuple[int, int]] = {}
    for room_id, course_ids in _section_subjects(session).items():
        total = sum(totals.get(course_id, 0) for course_id in course_ids)
        if not total:
            continue
        completed = sum(done.get(course_id, 0) for course_id in course_ids)
        result[room_id] = (completed, total)
    return result


def for_section(session: Session, section_id: UUID) -> tuple[int, int] | None:
    """(done, total) for one class-section, or `None` when no chapter plan exists."""
    return by_section(session).get(section_id)


def for_subject(
    session: Session, classroom_id: UUID, subject_id: UUID
) -> tuple[int, int]:
    """(done, total) for one section subject, named by its classroom-subject id."""
    row = session.exec(
        select(ClassroomSubject).where(
            ClassroomSubject.classroom_id == classroom_id,
            ClassroomSubject.id == subject_id,
        )
    ).first()
    if row is None:
        return (0, 0)
    return (
        _done_totals(session).get(row.id, 0),
        _chapter_totals(session).get(row.id, 0),
    )


def _section_subjects(session: Session) -> dict[UUID, set[UUID]]:
    """{classroom_id: active classroom-subject ids}."""
    subjects: dict[UUID, set[UUID]] = {}
    for room_id, course_id in session.exec(
        select(ClassroomSubject.classroom_id, ClassroomSubject.id).where(
            ClassroomSubject.status == COURSE_ACTIVE
        )
    ).all():
        subjects.setdefault(room_id, set()).add(course_id)
    return subjects


def subject_average_by_section(session: Session) -> dict[UUID, tuple[float, int]]:
    """{classroom_id: (average of completed/total per subject, subjects with a plan)}.

    D7: every subject is one vote, however many chapters it has; a subject with **no
    chapters** is left out (it has no plan to be a percentage *of*), and a section with no
    planned subject is absent entirely - "no data", not 0%.
    """
    totals = _chapter_totals(session)
    if not totals:
        return {}

    done = _done_totals(session)
    result: dict[UUID, tuple[float, int]] = {}
    for room_id, course_ids in _section_subjects(session).items():
        percents: list[float] = []
        for course_id in course_ids:
            total = totals.get(course_id, 0)
            if not total:
                continue
            completed = done.get(course_id, 0)
            percents.append(100.0 * completed / total)
        if percents:
            result[room_id] = (
                round(sum(percents) / len(percents), 1),
                len(percents),
            )
    return result


def for_section_average(session: Session, section_id: UUID) -> tuple[float, int] | None:
    """(subject-average %, subjects with a plan) for one section, or None."""
    return subject_average_by_section(session).get(section_id)


def planned_subjects(session: Session) -> dict[UUID, int]:
    """{class_id: how many subjects have a chapter plan} for the current academic year."""
    rows = session.exec(
        select(Classroom.class_id, func.count(func.distinct(Chapter.classroom_subject_id)))
        .join(ClassroomSubject, ClassroomSubject.classroom_id == Classroom.id)
        .join(Chapter, Chapter.classroom_subject_id == ClassroomSubject.id)
        .group_by(Classroom.class_id)
    ).all()
    return {class_id: int(count) for class_id, count in rows}


def by_teacher(
    session: Session, teacher_ids: list[UUID]
) -> dict[UUID, tuple[int, int]]:
    """{employee_id: (done, total)} across the subjects that person holds **now**.

    A teacher who handed a subject over keeps only what they finished while holding it;
    the total they are measured against is the plan of the subjects they hold today.
    """
    if not teacher_ids:
        return {}

    totals = _chapter_totals(session)
    if not totals:
        return {}

    done = _done_totals(session)
    holdings = session.exec(
        select(SubjectTeacher.teacher_id, SubjectTeacher.classroom_subject_id).where(
            SubjectTeacher.teacher_id.in_(teacher_ids),
            SubjectTeacher.effective_to.is_(None),
            SubjectTeacher.classroom_subject_id.is_not(None),
        )
    ).all()

    result: dict[UUID, list[int]] = {}
    for teacher_id, course_id in holdings:
        total = totals.get(course_id, 0)
        if not total:
            continue
        bucket = result.setdefault(teacher_id, [0, 0])
        bucket[0] += done.get(course_id, 0)
        bucket[1] += total
    return {teacher_id: (values[0], values[1]) for teacher_id, values in result.items()}
