"""The Course tab's backend: the plan, who teaches it, and how far each section has got.

Rules this module keeps
-----------------------
* **One source of truth for "done"**: `completion.py` counts `chapter_progress`; this
  module never stores a total of its own.
* **A teacher change is history**: the subject teacher rows are a timeline
  (`effective_from` / `effective_to`), and the per-teacher share of completed chapters
  comes from who ticked them - so handing a subject over does not move finished work to
  the new name.
* **Only the owner (or the office) may tick**: `classes.update` for the office, otherwise
  the caller must hold that subject in that section right now.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    CHAPTER_STATUSES,
    Chapter,
    ChapterProgress,
    Classroom,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import room_label
from app.domains.auth.service import AuthorizationService
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.profile.repository import employee_names

from . import completion
from .schemas import (
    ChapterRowRead,
    ChapterTickIn,
    CourseTeacherRead,
    SectionCourseRead,
    SubjectCourseRead,
)


def _room_or_404(session: Session, section_id: UUID) -> Classroom:
    """This school's class-section, or a `404` (the Phase 1 tenant rule)."""
    room = session.get(Classroom, section_id)
    school = tenant_of(session)
    if room is None or (school is not None and room.school_id != school):
        raise HTTPException(status_code=404, detail="Class-section not found")
    return room


def _employee_of(session: Session, user) -> UUID | None:
    """The `employee` row behind a login, when the person is staff."""
    if user is None or getattr(user, "id", None) is None:
        return None
    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    return employee.id if employee is not None else None


def _may_tick(session: Session, user, room: Classroom, subject_id: UUID) -> bool:
    """The office (any section) or the person holding this subject **now**.

    Not "a teacher": a teacher of *another* subject in the same room must not be able to
    tick this one, and a teacher of the same subject in another section must not either.
    """
    if user is None:
        return False
    if AuthorizationService.has_permission(user, "classes.update", session=session):
        return True
    employee_id = _employee_of(session, user)
    if employee_id is None:
        return False
    holding = session.exec(
        select(SubjectTeacher.id).where(
            SubjectTeacher.classroom_id == room.id,
            SubjectTeacher.subject_id == subject_id,
            SubjectTeacher.teacher_id == employee_id,
            SubjectTeacher.effective_to.is_(None),
        )
    ).first()
    return holding is not None


def _teachers_by_subject(
    session: Session, classroom_id: UUID
) -> dict[UUID, list[SubjectTeacher]]:
    """{subject_id: the timeline of teachers}, oldest assignment first."""
    rows = session.exec(
        select(SubjectTeacher)
        .where(SubjectTeacher.classroom_id == classroom_id)
        .order_by(SubjectTeacher.effective_from)
    ).all()
    grouped: dict[UUID, list[SubjectTeacher]] = {}
    for row in rows:
        grouped.setdefault(row.subject_id, []).append(row)
    return grouped


def _current_teacher_id(timeline: list[SubjectTeacher]) -> UUID | None:
    for row in timeline:
        if row.effective_to is None:
            return row.teacher_id
    return None


def _current_teacher(
    timeline: list[SubjectTeacher], names: dict[UUID, str]
) -> str | None:
    teacher_id = _current_teacher_id(timeline)
    return names.get(teacher_id) if teacher_id is not None else None


def _teacher_shares(
    timeline: list[SubjectTeacher],
    progress: dict[UUID, ChapterProgress],
    names: dict[UUID, str],
) -> list[CourseTeacherRead]:
    """Each person who held the subject, with what they personally finished."""
    completed_by: dict[UUID, int] = {}
    for row in progress.values():
        if row.status == CHAPTER_COMPLETED and row.completed_by_employee_id:
            completed_by[row.completed_by_employee_id] = (
                completed_by.get(row.completed_by_employee_id, 0) + 1
            )

    shares: list[CourseTeacherRead] = []
    for row in timeline:
        shares.append(
            CourseTeacherRead(
                employee_id=row.teacher_id,
                name=names.get(row.teacher_id, "A teacher"),
                effective_from=row.effective_from,
                effective_to=row.effective_to,
                current=row.effective_to is None,
                completed=completed_by.get(row.teacher_id, 0),
            )
        )
    return shares


def _chapter_row(
    session: Session,
    chapter: Chapter,
    progress: ChapterProgress | None,
    names: dict[UUID, str],
    today: date,
    *,
    can_tick: bool,
) -> ChapterRowRead:
    """One chapter: the plan, this section's status, and the ahead/behind verdict."""
    status = progress.status if progress is not None else "Pending"
    completed_on = progress.completed_on if progress is not None else None
    finished = status == CHAPTER_COMPLETED

    ahead: bool | None = None
    if finished and chapter.planned_date is not None and completed_on is not None:
        ahead = completed_on <= chapter.planned_date
    behind = (
        not finished
        and chapter.planned_date is not None
        and chapter.planned_date < today
    )

    return ChapterRowRead(
        chapter_id=chapter.id,
        sequence=chapter.sequence,
        name=chapter.name,
        planned_date=chapter.planned_date,
        status=status,
        completed_on=completed_on,
        completed_by=(
            names.get(progress.completed_by_employee_id)
            if progress is not None and progress.completed_by_employee_id
            else None
        ),
        completed_by_employee_id=(
            progress.completed_by_employee_id if progress is not None else None
        ),
        progress_id=progress.id if progress is not None else None,
        ahead=ahead,
        behind=behind,
        can_tick=can_tick,
    )


def section_course(session: Session, section_id: UUID, user=None) -> SectionCourseRead:
    """Everything the Course tab shows for one class-section, in one read."""
    room = _room_or_404(session, section_id)
    year = completion.current_year(session)
    teachers = _teachers_by_subject(session, room.id)
    if not teachers:
        return SectionCourseRead(
            section_id=room.id,
            label=room_label(session, room.id),
            academic_year=year.name if year is not None else None,
            subjects=[],
        )

    subjects = {
        subject.id: subject
        for subject in session.exec(
            select(Subject).where(Subject.id.in_(list(teachers)))
        ).all()
    }

    chapter_statement = select(Chapter).where(
        Chapter.class_id == room.class_id,
        Chapter.subject_id.in_(list(teachers)),
    )
    if year is not None:
        chapter_statement = chapter_statement.where(Chapter.academic_year_id == year.id)
    chapters = list(
        session.exec(
            chapter_statement.order_by(Chapter.subject_id, Chapter.sequence)
        ).all()
    )
    progress = {
        row.chapter_id: row
        for row in session.exec(
            select(ChapterProgress).where(
                ChapterProgress.classroom_id == room.id,
                ChapterProgress.chapter_id.in_([chapter.id for chapter in chapters]),
            )
        ).all()
    }

    employee_ids: set[UUID] = {
        row.completed_by_employee_id
        for row in progress.values()
        if row.completed_by_employee_id is not None
    }
    employee_ids |= {
        row.teacher_id for timeline in teachers.values() for row in timeline
    }
    names = employee_names(session, list(employee_ids))
    today = date.today()

    result: list[SubjectCourseRead] = []
    for subject_id, timeline in teachers.items():
        subject = subjects.get(subject_id)
        if subject is None:
            continue
        rows = [
            _chapter_row(
                session,
                chapter,
                progress.get(chapter.id),
                names,
                today,
                can_tick=_may_tick(session, user, room, subject_id),
            )
            for chapter in chapters
            if chapter.subject_id == subject_id
        ]
        done = sum(1 for row in rows if row.status == CHAPTER_COMPLETED)
        total = len(rows)
        result.append(
            SubjectCourseRead(
                subject_id=subject_id,
                subject=subject.name,
                current_teacher=_current_teacher(timeline, names),
                current_teacher_id=_current_teacher_id(timeline),
                teachers=_teacher_shares(timeline, progress, names),
                done=done,
                total=total,
                percent=round(100.0 * done / total, 1) if total else None,
                next_chapter=next(
                    (
                        f"Ch {row.sequence} · {row.name}"
                        for row in rows
                        if row.status != CHAPTER_COMPLETED
                    ),
                    None,
                ),
                behind=sum(1 for row in rows if row.behind),
                planned=any(row.planned_date is not None for row in rows),
                chapters=rows,
            )
        )

    result.sort(key=lambda item: item.subject)
    return SectionCourseRead(
        section_id=room.id,
        label=room_label(session, room.id),
        academic_year=year.name if year is not None else None,
        subjects=result,
    )


def tick_chapter(
    session: Session, chapter_id: UUID, payload: ChapterTickIn, user=None
) -> ChapterRowRead:
    """Move one chapter's status for one class-section.

    Setting `Completed` stamps **today** and **who** did it; taking it back to Pending or
    In progress clears both, so the per-teacher share can never claim a chapter twice.
    """
    chapter = session.get(Chapter, chapter_id)
    school = tenant_of(session)
    if chapter is None or (school is not None and chapter.school_id != school):
        raise HTTPException(status_code=404, detail="Chapter not found")

    room = _room_or_404(session, payload.classroom_id)
    if room.class_id != chapter.class_id:
        raise HTTPException(
            status_code=409,
            detail="That chapter belongs to another class.",
        )

    status = (payload.status or "").strip()
    if status not in CHAPTER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {', '.join(CHAPTER_STATUSES)}.",
        )

    if not _may_tick(session, user, room, chapter.subject_id):
        raise HTTPException(
            status_code=403,
            detail="Only the teacher of this subject, or the office, can tick it.",
        )

    progress = session.exec(
        select(ChapterProgress).where(
            ChapterProgress.chapter_id == chapter.id,
            ChapterProgress.classroom_id == room.id,
        )
    ).first()
    if progress is None:
        progress = ChapterProgress(
            chapter_id=chapter.id,
            classroom_id=room.id,
            status=status,
            school_id=school,
        )

    employee_id = _employee_of(session, user)
    if status == CHAPTER_COMPLETED:
        progress.completed_on = date.today()
        progress.completed_by_employee_id = employee_id
    else:
        progress.completed_on = None
        progress.completed_by_employee_id = None
    progress.status = status

    session.add(progress)
    session.commit()
    session.refresh(progress)

    return _chapter_row(
        session,
        chapter,
        progress,
        employee_names(
            session,
            [progress.completed_by_employee_id]
            if progress.completed_by_employee_id
            else [],
        ),
        date.today(),
        can_tick=True,
    )
