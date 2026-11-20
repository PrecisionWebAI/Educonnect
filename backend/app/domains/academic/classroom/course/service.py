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

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics import service as academics_service
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
from app.domains.academic.classroom.academics.schemas import SubjectCreate
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    COURSE_ARCHIVED,
    PLAN_APPROVED,
    PLAN_REJECTED,
    ClassroomSubject,
    LessonPlan,
)
from app.domains.academic.classroom.exams.models import ExamPaperChapter
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole, utcnow
from app.domains.auth.service import AuthorizationService
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.labels import TEACHING_ROLES
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.people.teachers.profile.repository import employee_names
from app.domains.people.teachers.workload.models import StaffWorkloadRule

from . import completion, scope
from .schemas import (
    AddSectionSubjectIn,
    ChapterCreate,
    ChapterRowRead,
    ChapterTickIn,
    ChapterUpdate,
    CourseSubjectRowRead,
    CourseTeacherAssignIn,
    CourseTeacherRead,
    LessonPlanSummaryRead,
    SectionCourseRead,
    SubjectCourseRead,
    TeacherAssignResult,
)


def _room_or_404(session: Session, section_id: UUID) -> Classroom:
    """This school's class-section, or a `404` (the Phase 1 tenant rule).

    A **select**, not `session.get`: the identity map can still hold a row from before
    the session was bound to another school, and `get` would return it unfiltered.
    """
    room = session.exec(select(Classroom).where(Classroom.id == section_id)).first()
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
    if scope.can_manage_course(session, user):
        return True
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
    can_edit: bool = False,
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
        can_edit=can_edit,
    )


def _office(session: Session, user) -> bool:
    """The office's view: everything, without filtering subjects by ownership.

    `classes.update` is the pre-Course office right the existing screens already use;
    keeping it here means the old Course tab tests and the old endpoints see the same
    rows while `course.*` is rolled out.
    """
    if user is None:
        return True
    return (
        scope.can_manage_course(session, user)
        or scope.can_view_all_courses(session, user)
        or scope.can_approve_course(session, user)
        or AuthorizationService.has_permission(user, "classes.update", session=session)
    )


def _course_rows(
    session: Session,
    room: Classroom,
    year,
    include_archived: bool,
) -> list[ClassroomSubject]:
    statement = select(ClassroomSubject).where(ClassroomSubject.classroom_id == room.id)
    if year is not None:
        statement = statement.where(ClassroomSubject.academic_year_id == year.id)
    if not include_archived:
        statement = statement.where(ClassroomSubject.status == COURSE_ACTIVE)
    return list(session.exec(statement.order_by(ClassroomSubject.created_at)).all())


def _plan_counts(
    session: Session, classroom_subject_ids: list[UUID]
) -> dict[UUID, int]:
    """{classroom_subject_id: lesson plans written} - one query, not one per row."""
    if not classroom_subject_ids:
        return {}
    rows = session.exec(
        select(LessonPlan.classroom_subject_id, func.count(LessonPlan.id))
        .where(LessonPlan.classroom_subject_id.in_(classroom_subject_ids))
        .group_by(LessonPlan.classroom_subject_id)
    ).all()
    return {course_id: int(count) for course_id, count in rows}


def _lesson_plan_summary(
    session: Session,
    classroom_subject_ids: list[UUID],
    year: int,
    month: int,
) -> dict[UUID, LessonPlanSummaryRead]:
    """{section subject: this month's week counts} - one grouped query."""
    if not classroom_subject_ids:
        return {}
    rows = session.exec(
        select(
            LessonPlan.classroom_subject_id,
            LessonPlan.status,
            func.count(LessonPlan.id),
        )
        .where(
            LessonPlan.classroom_subject_id.in_(classroom_subject_ids),
            LessonPlan.year == year,
            LessonPlan.month == month,
        )
        .group_by(LessonPlan.classroom_subject_id, LessonPlan.status)
    ).all()

    summary: dict[UUID, LessonPlanSummaryRead] = {}
    for course_id, status, count in rows:
        item = summary.setdefault(
            course_id, LessonPlanSummaryRead(year=year, month=month)
        )
        item.submitted += int(count)
        if status == PLAN_APPROVED:
            item.approved += int(count)
        elif status == PLAN_REJECTED:
            item.rejected += int(count)
        else:
            item.pending += int(count)
    return summary


def _completed_counts(
    session: Session, room: Classroom, year, subject_ids: list[UUID]
) -> dict[UUID, int]:
    """{subject_id: chapters completed in this section} - one grouped query."""
    if not subject_ids:
        return {}
    statement = (
        select(Chapter.subject_id, func.count(ChapterProgress.id))
        .join(Chapter, Chapter.id == ChapterProgress.chapter_id)
        .where(
            ChapterProgress.classroom_id == room.id,
            ChapterProgress.status == CHAPTER_COMPLETED,
            Chapter.class_id == room.class_id,
            Chapter.subject_id.in_(subject_ids),
        )
    )
    if year is not None:
        statement = statement.where(Chapter.academic_year_id == year.id)
    rows = session.exec(statement.group_by(Chapter.subject_id)).all()
    return {subject_id: int(count) for subject_id, count in rows}


def section_course(
    session: Session,
    section_id: UUID,
    user=None,
    include_archived: bool = False,
) -> SectionCourseRead:
    """Everything the Course tab shows for one class-section, in one read.

    The rows are the section's own `classroomsubject` rows - a subject can exist before a
    teacher does - plus any legacy `subjectteacher` subject from before the Phase 1
    backfill. A teacher sees only the subjects they hold now; the office sees all.
    """
    room = _room_or_404(session, section_id)
    year = completion.current_academic_year(session)
    teachers = _teachers_by_subject(session, room.id)
    course_rows = _course_rows(session, room, year, include_archived)
    section_subject_ids = {row.subject_id for row in course_rows} | set(teachers)

    slots: dict[UUID, ClassroomSubject | None] = {
        row.subject_id: row for row in course_rows
    }
    for subject_id in teachers:
        slots.setdefault(subject_id, None)

    visible = (
        None
        if _office(session, user)
        else scope.visible_course_subject_ids(session, user, room.id)
    )
    if visible is not None:
        employee_id = _employee_of(session, user)
        own_subjects = {
            row.subject_id
            for timeline in teachers.values()
            for row in timeline
            if row.effective_to is None and row.teacher_id == employee_id
        }
        slots = {
            subject_id: course_subject
            for subject_id, course_subject in slots.items()
            if (course_subject is not None and course_subject.id in visible)
            or subject_id in own_subjects
        }

    if not slots:
        average = completion.for_section_average(session, room.id)
        return SectionCourseRead(
            section_id=room.id,
            label=room_label(session, room.id),
            academic_year=year.name if year is not None else None,
            completion_percent=average[0] if average is not None else None,
            completion_subjects=average[1] if average is not None else 0,
            subjects_count=len(section_subject_ids),
            subjects=[],
        )

    subjects = {
        subject.id: subject
        for subject in session.exec(
            select(Subject).where(Subject.id.in_(list(slots)))
        ).all()
    }

    chapter_statement = select(Chapter).where(
        Chapter.class_id == room.class_id,
        Chapter.subject_id.in_(list(slots)),
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

    manage = scope.can_manage_course(session, user)
    can_assign = scope.can_assign_teacher(session, user)
    course_ids = [row.id for row in slots.values() if row is not None]
    plans = _plan_counts(session, course_ids)
    completed = _completed_counts(session, room, year, list(slots))
    plan_summary = _lesson_plan_summary(session, course_ids, today.year, today.month)

    result: list[SubjectCourseRead] = []
    for subject_id, course_subject in slots.items():
        subject = subjects.get(subject_id)
        if subject is None:
            continue
        timeline = teachers.get(subject_id, [])
        rows = [
            _chapter_row(
                session,
                chapter,
                progress.get(chapter.id),
                names,
                today,
                can_tick=_may_tick(session, user, room, subject_id),
                can_edit=manage,
            )
            for chapter in chapters
            if chapter.subject_id == subject_id
        ]
        done = sum(1 for row in rows if row.status == CHAPTER_COMPLETED)
        total = len(rows)
        status = course_subject.status if course_subject is not None else COURSE_ACTIVE
        result.append(
            SubjectCourseRead(
                classroom_subject_id=(
                    course_subject.id if course_subject is not None else None
                ),
                subject_id=subject_id,
                subject=subject.name,
                status=status,
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
                lesson_plan=(
                    plan_summary.get(course_subject.id)
                    if course_subject is not None
                    else None
                ),
                can_manage=manage,
                can_assign_teacher=can_assign,
                can_archive=bool(
                    manage and course_subject is not None and status == COURSE_ACTIVE
                ),
                can_restore=bool(
                    manage and course_subject is not None and status == COURSE_ARCHIVED
                ),
                can_delete=bool(
                    manage
                    and course_subject is not None
                    and not plans.get(course_subject.id)
                    and not completed.get(subject_id)
                ),
            )
        )

    result.sort(key=lambda item: (item.status == COURSE_ARCHIVED, item.subject))
    average = completion.for_section_average(session, room.id)
    return SectionCourseRead(
        section_id=room.id,
        label=room_label(session, room.id),
        academic_year=year.name if year is not None else None,
        completion_percent=average[0] if average is not None else None,
        completion_subjects=average[1] if average is not None else 0,
        subjects_count=len(section_subject_ids),
        subjects=result,
    )


def _course_row_or_404(
    session: Session, classroom_subject_id: UUID
) -> ClassroomSubject:
    row = session.exec(
        select(ClassroomSubject).where(ClassroomSubject.id == classroom_subject_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Section subject not found")
    return row


def _row_read(row: ClassroomSubject, subject: Subject) -> CourseSubjectRowRead:
    return CourseSubjectRowRead(
        classroom_subject_id=row.id,
        subject_id=subject.id,
        subject=subject.name,
        status=row.status,
    )


def _require_manage(session: Session, user) -> None:
    if not scope.can_manage_course(session, user):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the office can add, archive or remove a section subject, "
                "or plan its chapters."
            ),
        )


def available_subjects(session: Session, section_id: UUID, user=None) -> list[Subject]:
    """The school's active subjects that this section does **not** have this session.

    Archived rows count as "already added": they are restored from the row's own action,
    not re-added from the dropdown (which would collide with the unique key).
    """
    _require_manage(session, user)
    room = _room_or_404(session, section_id)
    year = completion.current_academic_year(session)

    statement = select(ClassroomSubject.subject_id).where(
        ClassroomSubject.classroom_id == room.id
    )
    if year is not None:
        statement = statement.where(ClassroomSubject.academic_year_id == year.id)
    used = set(session.exec(statement).all())

    return [
        subject
        for subject in academics_service.get_subjects(session)
        if subject.id not in used
    ]


def _subject_for_payload(session: Session, payload: AddSectionSubjectIn) -> Subject:
    """The master subject a section row will point at (and a custom one joins the list)."""
    if payload.subject_id is not None:
        subject = session.exec(
            select(Subject).where(Subject.id == payload.subject_id)
        ).first()
        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")
        if not subject.is_active:
            raise HTTPException(
                status_code=409,
                detail="That subject is retired in the school's list.",
            )
        return subject

    name = " ".join((payload.name or "").split())
    if not name:
        raise HTTPException(status_code=422, detail="Type a subject name.")

    # "English 1" typed in one section is the same subject in the next: reuse the master
    # row (re-activating it if it had been retired) instead of creating a duplicate.
    existing = next(
        (
            subject
            for subject in academics_service.get_subjects(
                session, include_inactive=True
            )
            if subject.name.strip().lower() == name.lower()
        ),
        None,
    )
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing

    return academics_service.create_subject(session, SubjectCreate(name=name))


def add_subject(
    session: Session,
    section_id: UUID,
    payload: AddSectionSubjectIn,
    user=None,
) -> CourseSubjectRowRead:
    """Put a subject on a section's Course tab - with no teacher yet."""
    _require_manage(session, user)
    room = _room_or_404(session, section_id)
    year = completion.current_academic_year(session)
    if year is None:
        raise HTTPException(
            status_code=409,
            detail="Open the current academic year before adding a subject.",
        )

    subject = _subject_for_payload(session, payload)
    existing = session.exec(
        select(ClassroomSubject).where(
            ClassroomSubject.classroom_id == room.id,
            ClassroomSubject.subject_id == subject.id,
            ClassroomSubject.academic_year_id == year.id,
        )
    ).first()
    if existing is not None:
        if existing.status == COURSE_ARCHIVED:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{subject.name}' is archived in this section - restore it instead "
                    "of adding it again."
                ),
            )
        raise HTTPException(
            status_code=409,
            detail=f"'{subject.name}' is already in this section.",
        )

    row = ClassroomSubject(
        classroom_id=room.id,
        subject_id=subject.id,
        academic_year_id=year.id,
        status=COURSE_ACTIVE,
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _row_read(row, subject)


def archive_subject(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    """Retire a subject from the section without deleting its plans, chapters or history."""
    _require_manage(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    subject = session.exec(select(Subject).where(Subject.id == row.subject_id)).first()
    if subject is None:  # pragma: no cover - the foreign key guarantees it
        raise HTTPException(status_code=404, detail="Subject not found")

    if row.status != COURSE_ARCHIVED:
        row.status = COURSE_ARCHIVED
        row.archived_at = utcnow()
        row.archived_by_user_id = getattr(user, "id", None)
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    return _row_read(row, subject)


def restore_subject(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    """Bring an archived subject back.

    A retired master subject has to be re-activated in the school list first, or every
    new section would inherit a subject the school no longer offers.
    """
    _require_manage(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    subject = session.exec(select(Subject).where(Subject.id == row.subject_id)).first()
    if subject is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Subject not found")
    if not subject.is_active:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{subject.name}' is retired in the school's list - re-activate it "
                "before restoring it to this section."
            ),
        )

    if row.status != COURSE_ACTIVE:
        row.status = COURSE_ACTIVE
        row.archived_at = None
        row.archived_by_user_id = None
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    return _row_read(row, subject)


def _delete_block_reason(
    session: Session, row: ClassroomSubject, room: Classroom
) -> str | None:
    """Why this section subject may not be hard-deleted, or None when it may."""
    plans = session.exec(
        select(func.count())
        .select_from(LessonPlan)
        .where(LessonPlan.classroom_subject_id == row.id)
    ).one()
    if plans:
        return "This subject has lesson plans; archive it instead so the history stays."

    completed = session.exec(
        select(func.count())
        .select_from(ChapterProgress)
        .join(Chapter, Chapter.id == ChapterProgress.chapter_id)
        .where(
            ChapterProgress.classroom_id == room.id,
            ChapterProgress.status == CHAPTER_COMPLETED,
            Chapter.class_id == room.class_id,
            Chapter.subject_id == row.subject_id,
            Chapter.academic_year_id == row.academic_year_id,
        )
    ).one()
    if completed:
        return (
            "Chapters are completed in this section; archive it instead so the "
            "progress stays."
        )
    return None


def delete_subject(session: Session, classroom_subject_id: UUID, user=None) -> None:
    """Remove a section subject that has no lesson plan and no completed chapter.

    A subject with a plan (any status) or a completed chapter is refused - the school is
    offered Archive instead, which keeps every row. A genuinely empty subject takes its
    unstarted progress and assignment history with it.
    """
    _require_manage(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    room = _room_or_404(session, row.classroom_id)

    reason = _delete_block_reason(session, row, room)
    if reason is not None:
        raise HTTPException(status_code=409, detail=reason)

    chapter_ids = list(
        session.exec(
            select(Chapter.id).where(
                Chapter.class_id == room.class_id,
                Chapter.subject_id == row.subject_id,
                Chapter.academic_year_id == row.academic_year_id,
            )
        ).all()
    )
    if chapter_ids:
        for progress in session.exec(
            select(ChapterProgress).where(
                ChapterProgress.classroom_id == room.id,
                ChapterProgress.chapter_id.in_(chapter_ids),
            )
        ).all():
            session.delete(progress)

    for assignment in session.exec(
        select(SubjectTeacher).where(
            SubjectTeacher.classroom_id == room.id,
            SubjectTeacher.subject_id == row.subject_id,
            or_(
                SubjectTeacher.classroom_subject_id == row.id,
                SubjectTeacher.classroom_subject_id.is_(None),
            ),
        )
    ).all():
        session.delete(assignment)

    session.delete(row)
    session.commit()


def _require_assign(session: Session, user) -> None:
    if not scope.can_assign_teacher(session, user):
        raise HTTPException(
            status_code=403,
            detail="Only the office can assign or change a subject teacher.",
        )


def _active_teacher(session: Session, teacher_id: UUID) -> Employee | None:
    """An employee who can teach today: not left, not deactivated, login active."""
    return session.exec(
        select(Employee)
        .join(User, User.id == Employee.user_id)
        .where(
            Employee.id == teacher_id,
            Employee.left_on.is_(None),
            Employee.deactivated_at.is_(None),
            User.is_active == True,  # noqa: E712
        )
    ).first()


def _has_teaching_role(session: Session, employee: Employee) -> bool:
    return (
        session.exec(
            select(Role.id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == employee.user_id,
                Role.codename.in_(list(TEACHING_ROLES)),
            )
        ).first()
        is not None
    )


def _open_assignments(session: Session, row: ClassroomSubject) -> list[SubjectTeacher]:
    """The open rows for this section subject, whatever shape wrote them."""
    return list(
        session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.classroom_id == row.classroom_id,
                SubjectTeacher.subject_id == row.subject_id,
                SubjectTeacher.effective_to.is_(None),
            )
        ).all()
    )


def _workload_warning(session: Session, employee_id: UUID) -> str | None:
    """A sentence when the school's own rule says this teacher is already overloaded."""
    rule = session.exec(select(StaffWorkloadRule)).first()
    if rule is None or not rule.weekly_periods:
        return None
    periods = int(
        session.exec(
            select(func.count())
            .select_from(TimetablePeriod)
            .where(TimetablePeriod.teacher_id == employee_id)
        ).one()
    )
    share = round(100.0 * periods / rule.weekly_periods)
    if share < rule.overload_percent:
        return None
    return (
        f"This teacher already has {periods} periods a week ({share}% of the "
        f"school's full load). The assignment is saved; review the timetable."
    )


def _assign_row(
    session: Session,
    row: ClassroomSubject,
    teacher: Employee,
    effective: date,
    user,
) -> None:
    """Close the open assignment and open the new one - the history is never rewritten."""
    open_rows = _open_assignments(session, row)
    if any(existing.effective_from > effective for existing in open_rows):
        raise HTTPException(
            status_code=422,
            detail="The effective date is before the current assignment's start.",
        )
    if (
        open_rows
        and all(existing.teacher_id == teacher.id for existing in open_rows)
        and effective >= max(existing.effective_from for existing in open_rows)
    ):
        # Assigning the person who already holds it is a no-op, not a new history row.
        return

    previous = {existing.teacher_id for existing in open_rows}
    names = employee_names(session, list(previous | {teacher.id}))
    subject = session.exec(select(Subject).where(Subject.id == row.subject_id)).first()
    subject_name = subject.name if subject is not None else "Subject"
    previous_names = ", ".join(
        sorted(names.get(item, "A teacher") for item in previous)
    )

    same_day = [
        existing for existing in open_rows if existing.effective_from == effective
    ]
    if same_day:
        # A same-day correction replaces the person on that day; there is no history to
        # split, and the unique (classroom, subject, effective_from) key allows one row.
        same_day[0].teacher_id = teacher.id
        same_day[0].classroom_subject_id = row.id
        same_day[0].academic_year_id = row.academic_year_id
        same_day[0].effective_to = None
        session.add(same_day[0])
    else:
        for existing in open_rows:
            existing.effective_to = effective - timedelta(days=1)
            session.add(existing)
        session.add(
            SubjectTeacher(
                classroom_id=row.classroom_id,
                subject_id=row.subject_id,
                classroom_subject_id=row.id,
                teacher_id=teacher.id,
                academic_year_id=row.academic_year_id,
                effective_from=effective,
                effective_to=None,
            )
        )

    new_name = names.get(teacher.id, "A teacher")
    summary = (
        f"{subject_name.title()} · {room_label(session, row.classroom_id)}: "
        f"{previous_names or 'nobody'} -> {new_name} from {effective.isoformat()}"
    )
    session.add(
        StaffAuditLog(
            employee_id=teacher.id,
            section="course",
            action="changed" if previous else "assigned",
            row_id=row.id,
            summary=summary,
            changed_by_user_id=getattr(user, "id", None),
        )
    )
    session.commit()


def assign_teacher(
    session: Session,
    classroom_subject_id: UUID,
    payload: CourseTeacherAssignIn,
    user=None,
) -> TeacherAssignResult:
    """Assign/change one section subject's teacher, returning the workload warning."""
    _require_assign(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    teacher = _active_teacher(session, payload.teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Active teacher not found")
    if not _has_teaching_role(session, teacher):
        raise HTTPException(
            status_code=409, detail="That employee does not hold a teaching role."
        )

    effective = payload.effective_from or date.today()
    _assign_row(session, row, teacher, effective, user)
    name = employee_names(session, [teacher.id]).get(teacher.id, "A teacher")
    return TeacherAssignResult(
        classroom_subject_id=row.id,
        teacher_id=teacher.id,
        teacher=name,
        effective_from=effective,
        warning=_workload_warning(session, teacher.id),
    )


def teacher_history(
    session: Session, classroom_subject_id: UUID
) -> list[CourseTeacherRead]:
    """Everyone who held this section subject, oldest first, with their own chapters."""
    row = _course_row_or_404(session, classroom_subject_id)
    timeline = list(
        session.exec(
            select(SubjectTeacher)
            .where(
                SubjectTeacher.classroom_id == row.classroom_id,
                SubjectTeacher.subject_id == row.subject_id,
                or_(
                    SubjectTeacher.classroom_subject_id == row.id,
                    SubjectTeacher.classroom_subject_id.is_(None),
                ),
            )
            .order_by(SubjectTeacher.effective_from)
        ).all()
    )
    room = _room_or_404(session, row.classroom_id)
    completed_rows = session.exec(
        select(ChapterProgress.completed_by_employee_id, func.count(ChapterProgress.id))
        .join(Chapter, Chapter.id == ChapterProgress.chapter_id)
        .where(
            ChapterProgress.classroom_id == room.id,
            ChapterProgress.status == CHAPTER_COMPLETED,
            Chapter.class_id == room.class_id,
            Chapter.subject_id == row.subject_id,
            Chapter.academic_year_id == row.academic_year_id,
        )
        .group_by(ChapterProgress.completed_by_employee_id)
    ).all()
    completed = {
        employee_id: int(count)
        for employee_id, count in completed_rows
        if employee_id is not None
    }
    names = employee_names(session, [item.teacher_id for item in timeline])
    return [
        CourseTeacherRead(
            employee_id=item.teacher_id,
            name=names.get(item.teacher_id, "A teacher"),
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            current=item.effective_to is None,
            completed=completed.get(item.teacher_id, 0),
        )
        for item in timeline
    ]


def _clear_teacher_row(session: Session, row: ClassroomSubject) -> None:
    today = date.today()
    for existing in _open_assignments(session, row):
        if existing.effective_from > today:
            session.delete(existing)
        else:
            existing.effective_to = today
            session.add(existing)
    session.commit()


def clear_teacher(session: Session, classroom_subject_id: UUID, user=None) -> None:
    """Close the current assignment (the legacy "clear" action); history stays."""
    _require_assign(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    _clear_teacher_row(session, row)


def assign_teacher_via_legacy(
    session: Session,
    *,
    section_id: UUID,
    subject_id: UUID,
    teacher_id: UUID | None,
) -> None:
    """The old `PUT /classroom/sections/{id}/subjects/{subject_id}/teacher` path.

    It now writes the same history rows as the Course endpoint, so the two cannot
    disagree: find (or open) the section subject for this session, then assign/clear.
    """
    room = _room_or_404(session, section_id)
    year = completion.current_academic_year(session)
    if year is None:
        raise HTTPException(
            status_code=409,
            detail="Open the current academic year before assigning a teacher.",
        )

    subject = session.exec(select(Subject).where(Subject.id == subject_id)).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    row = session.exec(
        select(ClassroomSubject).where(
            ClassroomSubject.classroom_id == room.id,
            ClassroomSubject.subject_id == subject_id,
            ClassroomSubject.academic_year_id == year.id,
        )
    ).first()
    if row is None:
        row = ClassroomSubject(
            classroom_id=room.id,
            subject_id=subject_id,
            academic_year_id=year.id,
            status=COURSE_ACTIVE,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

    if teacher_id is None:
        _clear_teacher_row(session, row)
        return

    teacher = _active_teacher(session, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Active teacher not found")
    if not _has_teaching_role(session, teacher):
        raise HTTPException(
            status_code=409, detail="That employee does not hold a teaching role."
        )
    _assign_row(session, row, teacher, date.today(), None)


def _chapter_or_404(session: Session, chapter_id: UUID) -> Chapter:
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


def _chapters_for(
    session: Session, class_id: UUID, subject_id: UUID, year_id: UUID
) -> list[Chapter]:
    return list(
        session.exec(
            select(Chapter)
            .where(
                Chapter.class_id == class_id,
                Chapter.subject_id == subject_id,
                Chapter.academic_year_id == year_id,
            )
            .order_by(Chapter.sequence)
        ).all()
    )


def _chapter_view(
    session: Session, chapter: Chapter, room: Classroom, user
) -> ChapterRowRead:
    """One chapter as this section and this caller see it."""
    progress = session.exec(
        select(ChapterProgress).where(
            ChapterProgress.chapter_id == chapter.id,
            ChapterProgress.classroom_id == room.id,
        )
    ).first()
    names = employee_names(
        session,
        [progress.completed_by_employee_id]
        if progress is not None and progress.completed_by_employee_id
        else [],
    )
    return _chapter_row(
        session,
        chapter,
        progress,
        names,
        date.today(),
        can_tick=_may_tick(session, user, room, chapter.subject_id),
        can_edit=scope.can_manage_course(session, user),
    )


def list_chapters(
    session: Session, classroom_subject_id: UUID, user=None
) -> list[ChapterRowRead]:
    """The chapter plan of one section subject, with this section's progress.

    The rows belong to the class, so 9-B sees the same chapters as 9-A; the status,
    completed date and completed-by are the section's own. A teacher may read the list
    only for a subject they hold now.
    """
    row = _course_row_or_404(session, classroom_subject_id)
    room = _room_or_404(session, row.classroom_id)
    if not (
        _office(session, user)
        or scope.is_own_course_teacher(session, user, classroom_subject_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="You can read only the chapters of the subject you teach.",
        )

    chapters = _chapters_for(
        session, room.class_id, row.subject_id, row.academic_year_id
    )
    return [_chapter_view(session, chapter, room, user) for chapter in chapters]


def add_chapter(
    session: Session,
    classroom_subject_id: UUID,
    payload: ChapterCreate,
    user=None,
) -> ChapterRowRead:
    """Add a chapter to the class's plan (the office only).

    `sequence` omitted appends; an occupied explicit sequence is refused (`409`) instead
    of silently renumbering the book. A chapter is class-level, so it appears in every
    section of that class as soon as it is created.
    """
    _require_manage(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    room = _room_or_404(session, row.classroom_id)

    existing = _chapters_for(
        session, room.class_id, row.subject_id, row.academic_year_id
    )
    if payload.sequence is not None:
        if any(chapter.sequence == payload.sequence for chapter in existing):
            raise HTTPException(
                status_code=409,
                detail=f"Chapter {payload.sequence} already exists in this plan.",
            )
        sequence = payload.sequence
    else:
        sequence = max((chapter.sequence for chapter in existing), default=0) + 1

    chapter = Chapter(
        class_id=room.class_id,
        subject_id=row.subject_id,
        academic_year_id=row.academic_year_id,
        sequence=sequence,
        name=payload.name,
        planned_date=payload.planned_date,
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return _chapter_view(session, chapter, room, user)


def _move_chapter(session: Session, chapter: Chapter, target: int) -> None:
    """Move to 1-based `target` and renumber the whole list, collision-free.

    Unique `(class, subject, session, sequence)` means we cannot simply swap two rows:
    the first update would collide. Every row goes to a negative number, flushes, then
    comes back at its final positive number - one transaction, no duplicate positions.
    """
    rows = _chapters_for(
        session, chapter.class_id, chapter.subject_id, chapter.academic_year_id
    )
    ordered = [row for row in rows if row.id != chapter.id]
    position = max(0, min(target - 1, len(ordered)))
    ordered.insert(position, chapter)

    for index, row in enumerate(ordered, start=1):
        row.sequence = -index
        session.add(row)
    session.flush()
    for index, row in enumerate(ordered, start=1):
        row.sequence = index
        session.add(row)
    session.flush()


def update_chapter(
    session: Session,
    chapter_id: UUID,
    payload: ChapterUpdate,
    user=None,
) -> ChapterRowRead:
    """Rename, re-date or move one chapter (the office only)."""
    _require_manage(session, user)
    chapter = _chapter_or_404(session, chapter_id)
    fields = payload.model_fields_set

    if "name" in fields and payload.name is not None:
        chapter.name = payload.name
    if "planned_date" in fields:
        chapter.planned_date = payload.planned_date
    if (
        "sequence" in fields
        and payload.sequence is not None
        and payload.sequence != chapter.sequence
    ):
        _move_chapter(session, chapter, payload.sequence)

    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return _chapter_row(
        session,
        chapter,
        None,
        {},
        date.today(),
        can_tick=False,
        can_edit=True,
    )


def delete_chapter(session: Session, chapter_id: UUID, user=None) -> None:
    """Delete a chapter that no section has finished and no exam paper covers.

    A completed chapter is history and part of a percentage; the office must undo the
    tick first. An exam paper's syllabus also blocks it - the paper's Phase 7 read would
    otherwise point at a chapter that no longer exists.
    """
    _require_manage(session, user)
    chapter = _chapter_or_404(session, chapter_id)

    completed = session.exec(
        select(ChapterProgress.id).where(
            ChapterProgress.chapter_id == chapter.id,
            ChapterProgress.status == CHAPTER_COMPLETED,
        )
    ).first()
    if completed is not None:
        raise HTTPException(
            status_code=409,
            detail="A class-section has completed this chapter; undo the tick first.",
        )

    used = session.exec(
        select(ExamPaperChapter.id).where(ExamPaperChapter.chapter_id == chapter.id)
    ).first()
    if used is not None:
        raise HTTPException(
            status_code=409,
            detail="An exam paper uses this chapter; remove it from the paper first.",
        )

    for progress in session.exec(
        select(ChapterProgress).where(ChapterProgress.chapter_id == chapter.id)
    ).all():
        session.delete(progress)
    session.delete(chapter)
    session.commit()


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
