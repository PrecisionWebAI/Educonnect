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
    ChapterProgress,
    Classroom,
    SubjectTeacher,
)
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    COURSE_ARCHIVED,
    ClassroomSubject,
)
from app.domains.admin.settings.models import AcademicYear


def current_year(session: Session) -> AcademicYear | None:
    """The session the screens treat as "now", or `None` when none is open.

    A **read**: unlike `placement.current_academic_year` it never creates the row. When
    it is missing, plans from every year are counted together - the honest answer for a
    school that has not set its calendar, and the next placement opens the row anyway.
    """
    return session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()


def _chapter_totals(session: Session) -> dict[tuple[UUID, UUID], int]:
    """{(class_id, subject_id): chapters planned} for the current session."""
    year = current_year(session)
    statement = select(
        Chapter.class_id, Chapter.subject_id, func.count(Chapter.id)
    ).group_by(Chapter.class_id, Chapter.subject_id)
    if year is not None:
        statement = statement.where(Chapter.academic_year_id == year.id)

    return {
        (class_id, subject_id): int(chapters)
        for class_id, subject_id, chapters in session.exec(statement).all()
    }


def _done_totals(session: Session) -> dict[tuple[UUID, UUID, UUID], int]:
    """{(classroom_id, class_id, subject_id): chapters completed}."""
    statement = (
        select(
            ChapterProgress.classroom_id,
            Chapter.class_id,
            Chapter.subject_id,
            func.count(ChapterProgress.id),
        )
        .join(Chapter, Chapter.id == ChapterProgress.chapter_id)
        .where(ChapterProgress.status == CHAPTER_COMPLETED)
        .group_by(ChapterProgress.classroom_id, Chapter.class_id, Chapter.subject_id)
    )
    return {
        (classroom_id, class_id, subject_id): int(done)
        for classroom_id, class_id, subject_id, done in session.exec(statement).all()
    }


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
    for class_id, room_ids in _rooms_by_class(session).items():
        subjects = [key for key in totals if key[0] == class_id]
        if not subjects:
            continue
        total = sum(totals[key] for key in subjects)
        if not total:
            continue
        for room_id in room_ids:
            completed = sum(done.get((room_id, *key), 0) for key in subjects)
            result[room_id] = (completed, total)
    return result


def for_section(session: Session, section_id: UUID) -> tuple[int, int] | None:
    """(done, total) for one class-section, or `None` when no chapter plan exists."""
    return by_section(session).get(section_id)


def for_subject(
    session: Session, classroom_id: UUID, subject_id: UUID
) -> tuple[int, int]:
    """(done, total) for one subject in one class-section."""
    room = session.get(Classroom, classroom_id)
    if room is None:
        return (0, 0)
    totals = _chapter_totals(session)
    total = totals.get((room.class_id, subject_id), 0)
    if not total:
        return (0, 0)
    done = _done_totals(session).get((classroom_id, room.class_id, subject_id), 0)
    return (done, total)


def _section_subjects(session: Session) -> dict[UUID, set[UUID]]:
    """{classroom_id: subjects the section runs} - active rows plus legacy assignments."""
    subjects: dict[UUID, set[UUID]] = {}
    for room_id, subject_id in session.exec(
        select(ClassroomSubject.classroom_id, ClassroomSubject.subject_id).where(
            ClassroomSubject.status == COURSE_ACTIVE
        )
    ).all():
        subjects.setdefault(room_id, set()).add(subject_id)

    for room_id, subject_id in session.exec(
        select(SubjectTeacher.classroom_id, SubjectTeacher.subject_id).where(
            SubjectTeacher.classroom_subject_id.is_(None)
        )
    ).all():
        subjects.setdefault(room_id, set()).add(subject_id)

    # A chapter plan belongs to the **class**, so every section of that class is measured
    # against it even before a section row exists. This is the old card's rule too: 9-B
    # with the plan and nothing ticked reads 0%, not "no data".
    archived = {
        (room_id, subject_id)
        for room_id, subject_id in session.exec(
            select(ClassroomSubject.classroom_id, ClassroomSubject.subject_id).where(
                ClassroomSubject.status == COURSE_ARCHIVED
            )
        ).all()
    }
    by_class: dict[UUID, set[UUID]] = {}
    for class_id, subject_id in session.exec(
        select(Chapter.class_id, Chapter.subject_id).distinct()
    ).all():
        by_class.setdefault(class_id, set()).add(subject_id)
    for room_id, class_id in session.exec(
        select(Classroom.id, Classroom.class_id)
    ).all():
        subjects.setdefault(room_id, set()).update(
            subject_id
            for subject_id in by_class.get(class_id, set())
            if (room_id, subject_id) not in archived
        )
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
    rooms = dict(session.exec(select(Classroom.id, Classroom.class_id)).all())
    result: dict[UUID, tuple[float, int]] = {}
    for room_id, subject_ids in _section_subjects(session).items():
        class_id = rooms.get(room_id)
        if class_id is None:
            continue
        percents: list[float] = []
        for subject_id in subject_ids:
            total = totals.get((class_id, subject_id), 0)
            if not total:
                continue
            completed = done.get((room_id, class_id, subject_id), 0)
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
    """{class_id: how many subjects have a chapter plan} for the current session."""
    counts: dict[UUID, int] = {}
    for class_id, _subject_id in _chapter_totals(session):
        counts[class_id] = counts.get(class_id, 0) + 1
    return counts


def by_teacher(
    session: Session, teacher_ids: list[UUID]
) -> dict[UUID, tuple[int, int]]:
    """{employee_id: (done, total)} across the subjects that person holds **now**.

    A teacher who handed a subject over keeps only what they finished while holding it
    (the progress row's `completed_by_employee_id` is theirs); the total they are
    measured against is the plan of the subjects they hold today.
    """
    if not teacher_ids:
        return {}

    totals = _chapter_totals(session)
    if not totals:
        return {}

    rooms = {
        room_id: class_id
        for class_id, room_ids in _rooms_by_class(session).items()
        for room_id in room_ids
    }
    done = _done_totals(session)

    holdings = session.exec(
        select(
            SubjectTeacher.teacher_id,
            SubjectTeacher.classroom_id,
            SubjectTeacher.subject_id,
        ).where(
            SubjectTeacher.teacher_id.in_(teacher_ids),
            SubjectTeacher.effective_to.is_(None),
        )
    ).all()

    result: dict[UUID, list[int]] = {}
    for teacher_id, classroom_id, subject_id in holdings:
        class_id = rooms.get(classroom_id)
        if class_id is None:
            continue
        total = totals.get((class_id, subject_id), 0)
        if not total:
            continue
        bucket = result.setdefault(teacher_id, [0, 0])
        bucket[0] += done.get((classroom_id, class_id, subject_id), 0)
        bucket[1] += total
    return {teacher_id: (values[0], values[1]) for teacher_id, values in result.items()}
