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
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    CHAPTER_PENDING,
    CHAPTER_STATUSES,
    Chapter,
    Classroom,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import room_label
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
from app.domains.auth.models import Role, UserRole
from app.domains.auth.service import AuthorizationService
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.labels import TEACHING_ROLES
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.people.teachers.profile.repository import employee_names
from app.domains.people.teachers.workload.models import StaffWorkloadRule

from . import completion, scope
from . import subjects as subject_rows
from .schemas import (
    AddSectionSubjectIn,
    ChapterCopyIn,
    ChapterCopyResult,
    ChapterCreate,
    ChapterRowRead,
    ChapterSourceRead,
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


def _may_tick(session: Session, user, classroom_subject_id: UUID) -> bool:
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
            SubjectTeacher.classroom_subject_id == classroom_subject_id,
            SubjectTeacher.teacher_id == employee_id,
            SubjectTeacher.effective_to.is_(None),
        )
    ).first()
    return holding is not None


def _tickable_subjects(
    session: Session, user, classroom_subject_ids: list[UUID]
) -> set[UUID]:
    """The subjects among `classroom_subject_ids` this person may tick - in one pass.

    The same rule as `_may_tick`, answered for a whole section with at most two queries,
    so the Course tab does not ask once per subject.
    """
    if user is None:
        return set()
    if scope.can_manage_course(session, user) or AuthorizationService.has_permission(
        user, "classes.update", session=session
    ):
        return set(classroom_subject_ids)
    employee_id = _employee_of(session, user)
    if employee_id is None or not classroom_subject_ids:
        return set()
    return set(
        session.exec(
            select(SubjectTeacher.classroom_subject_id).where(
                SubjectTeacher.classroom_subject_id.in_(classroom_subject_ids),
                SubjectTeacher.teacher_id == employee_id,
                SubjectTeacher.effective_to.is_(None),
            )
        ).all()
    )


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
    chapters: list[Chapter],
    names: dict[UUID, str],
) -> list[CourseTeacherRead]:
    """Each person who held the subject, with what they personally finished."""
    completed_by: dict[UUID, int] = {}
    for row in chapters:
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
    names: dict[UUID, str],
    today: date,
    *,
    can_tick: bool,
    can_edit: bool = False,
) -> ChapterRowRead:
    """One chapter: the plan, this section's status, and the ahead/behind verdict."""
    status = chapter.status or CHAPTER_PENDING
    completed_on = chapter.completed_on
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
            names.get(chapter.completed_by_employee_id)
            if chapter.completed_by_employee_id
            else None
        ),
        completed_by_employee_id=chapter.completed_by_employee_id,
        progress_id=None,
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
    session: Session, classroom_subject_ids: list[UUID]
) -> dict[UUID, int]:
    """{classroom_subject_id: completed chapters} - one grouped query."""
    if not classroom_subject_ids:
        return {}
    rows = session.exec(
        select(Chapter.classroom_subject_id, func.count(Chapter.id))
        .where(
            Chapter.classroom_subject_id.in_(classroom_subject_ids),
            Chapter.status == CHAPTER_COMPLETED,
        )
        .group_by(Chapter.classroom_subject_id)
    ).all()
    return {course_id: int(count) for course_id, count in rows}


def section_course(
    session: Session,
    section_id: UUID,
    user=None,
    include_archived: bool = False,
) -> SectionCourseRead:
    """Everything the Course tab shows for one class-section, in one read.

    The rows are the section's own `classroomsubject` rows - a subject can exist before a
    teacher does. A teacher sees only the subjects they hold now; the office sees all.
    The number of queries is fixed: it does not grow with subjects, chapters or teachers.
    """
    room = _room_or_404(session, section_id)
    year = completion.current_academic_year(session)
    course_rows = _course_rows(session, room, year, include_archived)

    visible = (
        None
        if _office(session, user)
        else scope.visible_course_subject_ids(session, user, room.id)
    )
    if visible is not None:
        course_rows = [row for row in course_rows if row.id in visible]

    if not course_rows:
        average = completion.for_section_average(session, room.id)
        return SectionCourseRead(
            section_id=room.id,
            label=room_label(session, room.id),
            academic_year=year.name if year is not None else None,
            completion_percent=average[0] if average is not None else None,
            completion_subjects=average[1] if average is not None else 0,
            subjects_count=0,
            subjects=[],
        )

    course_ids = [row.id for row in course_rows]

    # The teacher history of the visible subjects - open and closed rows - in one query.
    by_course: dict[UUID, list[SubjectTeacher]] = {}
    for assignment in session.exec(
        select(SubjectTeacher)
        .where(SubjectTeacher.classroom_subject_id.in_(course_ids))
        .order_by(SubjectTeacher.effective_from)
    ).all():
        by_course.setdefault(assignment.classroom_subject_id, []).append(assignment)

    chapters_by_course: dict[UUID, list[Chapter]] = {}
    for chapter in session.exec(
        select(Chapter)
        .where(Chapter.classroom_subject_id.in_(course_ids))
        .order_by(Chapter.classroom_subject_id, Chapter.sequence)
    ).all():
        chapters_by_course.setdefault(chapter.classroom_subject_id, []).append(chapter)

    employee_ids: set[UUID] = {
        chapter.completed_by_employee_id
        for group in chapters_by_course.values()
        for chapter in group
        if chapter.completed_by_employee_id is not None
    }
    employee_ids |= {
        assignment.teacher_id for group in by_course.values() for assignment in group
    }
    names = employee_names(session, list(employee_ids))
    today = date.today()

    manage = scope.can_manage_course(session, user)
    can_assign = scope.can_assign_teacher(session, user)
    tickable = _tickable_subjects(session, user, course_ids)
    plans = _plan_counts(session, course_ids)
    completed = _completed_counts(session, course_ids)
    plan_summary = _lesson_plan_summary(session, course_ids, today.year, today.month)

    result: list[SubjectCourseRead] = []
    for course_subject in course_rows:
        timeline = by_course.get(course_subject.id, [])
        chapters = chapters_by_course.get(course_subject.id, [])
        can_tick = course_subject.id in tickable
        rows = [
            _chapter_row(
                session,
                chapter,
                names,
                today,
                can_tick=can_tick,
                can_edit=manage,
            )
            for chapter in chapters
        ]
        done = sum(1 for row in rows if row.status == CHAPTER_COMPLETED)
        total = len(rows)
        status = course_subject.status
        result.append(
            SubjectCourseRead(
                classroom_subject_id=course_subject.id,
                name=course_subject.name,
                code=course_subject.code,
                status=status,
                current_teacher=_current_teacher(timeline, names),
                current_teacher_id=_current_teacher_id(timeline),
                teachers=_teacher_shares(timeline, chapters, names),
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
                lesson_plan=plan_summary.get(course_subject.id),
                can_manage=manage,
                can_assign_teacher=can_assign,
                can_archive=bool(manage and status == COURSE_ACTIVE),
                can_restore=bool(manage and status == COURSE_ARCHIVED),
                can_delete=bool(
                    manage
                    and not plans.get(course_subject.id)
                    and not completed.get(course_subject.id)
                ),
            )
        )

    result.sort(key=lambda item: (item.status == COURSE_ARCHIVED, item.name))
    average = completion.for_section_average(session, room.id)
    return SectionCourseRead(
        section_id=room.id,
        label=room_label(session, room.id),
        academic_year=year.name if year is not None else None,
        completion_percent=average[0] if average is not None else None,
        completion_subjects=average[1] if average is not None else 0,
        subjects_count=len(course_rows),
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


def _row_read(row: ClassroomSubject) -> CourseSubjectRowRead:
    return CourseSubjectRowRead(
        classroom_subject_id=row.id,
        name=row.name,
        code=row.code,
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


def add_subject(
    session: Session,
    section_id: UUID,
    payload: AddSectionSubjectIn,
    user=None,
) -> CourseSubjectRowRead:
    """Put a section-owned subject on the Course tab - with no teacher yet."""
    row = subject_rows.create_subject(
        session,
        section_id=section_id,
        name=payload.name,
        code=payload.code,
        user=user,
    )
    return _row_read(row)


def rename_subject(
    session: Session,
    classroom_subject_id: UUID,
    payload,
    user=None,
) -> CourseSubjectRowRead:
    """Rename one section's subject; no other classroom is touched."""
    row = subject_rows.rename_subject(
        session,
        classroom_subject_id=classroom_subject_id,
        name=payload.name,
        code=payload.code if "code" in payload.model_fields_set else ...,
        user=user,
    )
    return _row_read(row)


def archive_subject(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    """Retire a subject from the section without deleting its plans, chapters or history."""
    row = subject_rows.archive_subject(
        session,
        classroom_subject_id=classroom_subject_id,
        user=user,
    )
    return _row_read(row)


def restore_subject(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    """Bring an archived subject back; an active duplicate is a `409`."""
    row = subject_rows.restore_subject(
        session,
        classroom_subject_id=classroom_subject_id,
        user=user,
    )
    return _row_read(row)


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
        .select_from(Chapter)
        .where(
            Chapter.classroom_subject_id == row.id,
            Chapter.status == CHAPTER_COMPLETED,
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

    for chapter in session.exec(
        select(Chapter).where(Chapter.classroom_subject_id == row.id)
    ).all():
        session.delete(chapter)

    assignment_statement = select(SubjectTeacher).where(
        SubjectTeacher.classroom_subject_id == row.id
    )
    for assignment in session.exec(assignment_statement).all():
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
    """The open history rows of this section subject."""
    return list(
        session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.classroom_subject_id == row.id,
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
    subject_name = row.name
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
            .where(SubjectTeacher.classroom_subject_id == row.id)
            .order_by(SubjectTeacher.effective_from)
        ).all()
    )
    completed_rows = session.exec(
        select(Chapter.completed_by_employee_id, func.count(Chapter.id))
        .where(
            Chapter.classroom_subject_id == row.id,
            Chapter.status == CHAPTER_COMPLETED,
        )
        .group_by(Chapter.completed_by_employee_id)
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


def _chapter_or_404(session: Session, chapter_id: UUID) -> Chapter:
    chapter = session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


def _chapters_for(session: Session, classroom_subject_id: UUID) -> list[Chapter]:
    return list(
        session.exec(
            select(Chapter)
            .where(Chapter.classroom_subject_id == classroom_subject_id)
            .order_by(Chapter.sequence)
        ).all()
    )


def _chapter_view(
    session: Session, chapter: Chapter, room: Classroom, user
) -> ChapterRowRead:
    """One chapter as this section and this caller see it."""
    names = employee_names(
        session,
        [chapter.completed_by_employee_id]
        if chapter.completed_by_employee_id
        else [],
    )
    return _chapter_row(
        session,
        chapter,
        names,
        date.today(),
        can_tick=_may_tick(session, user, chapter.classroom_subject_id),
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

    chapters = _chapters_for(session, row.id)
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

    existing = _chapters_for(session, row.id)
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
        classroom_subject_id=row.id,
        academic_year_id=row.academic_year_id,
        sequence=sequence,
        name=payload.name,
        planned_date=payload.planned_date,
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return _chapter_view(session, chapter, room, user)


def _same_class_year_sections(
    session: Session, target: ClassroomSubject
) -> list[ClassroomSubject]:
    """Other active subjects of the same class (any section) and academic year."""
    target_room = _room_or_404(session, target.classroom_id)
    return list(
        session.exec(
            select(ClassroomSubject)
            .join(Classroom, Classroom.id == ClassroomSubject.classroom_id)
            .where(
                ClassroomSubject.id != target.id,
                ClassroomSubject.school_id == target.school_id,
                ClassroomSubject.academic_year_id == target.academic_year_id,
                ClassroomSubject.status == COURSE_ACTIVE,
                Classroom.class_id == target_room.class_id,
            )
        ).all()
    )


def chapter_sources(
    session: Session, classroom_subject_id: UUID, user=None
) -> list[ChapterSourceRead]:
    """Other sections of this class and year that already have a chapter plan."""
    target = _course_row_or_404(session, classroom_subject_id)
    if not (
        _office(session, user)
        or scope.is_own_course_teacher(session, user, classroom_subject_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="You can read only the chapters of the subject you teach.",
        )
    candidates = _same_class_year_sections(session, target)
    if not candidates:
        return []
    counts = dict(
        session.exec(
            select(Chapter.classroom_subject_id, func.count(Chapter.id))
            .where(Chapter.classroom_subject_id.in_([row.id for row in candidates]))
            .group_by(Chapter.classroom_subject_id)
        ).all()
    )
    sources = [
        ChapterSourceRead(
            classroom_subject_id=row.id,
            section_id=row.classroom_id,
            label=f"{room_label(session, row.classroom_id)} · {row.name}",
            chapter_count=int(counts[row.id]),
        )
        for row in candidates
        if counts.get(row.id)
    ]
    return sorted(sources, key=lambda item: item.label)


def copy_chapters(
    session: Session,
    classroom_subject_id: UUID,
    payload: ChapterCopyIn,
    user=None,
) -> ChapterCopyResult:
    """Copy another section's chapter list into this section subject.

    Same school, same class, same academic year; never onto itself. Each copy is a fresh
    Pending chapter (name, planned date, order) - progress is not copied. An empty target
    keeps the source's numbering; a target with chapters gets the new ones appended after
    its last. A chapter whose name the target already has is skipped and reported, never
    duplicated. After the copy the two plans are independent.
    """
    _require_manage(session, user)
    target = _course_row_or_404(session, classroom_subject_id)
    source = _course_row_or_404(session, payload.source_classroom_subject_id)
    if source.id == target.id:
        raise HTTPException(status_code=409, detail="Choose another section.")
    if source.school_id != target.school_id:
        raise HTTPException(status_code=404, detail="Source subject not found.")
    if source.academic_year_id != target.academic_year_id:
        raise HTTPException(
            status_code=409, detail="Chapters can be copied only within one academic year."
        )
    if _room_or_404(session, source.classroom_id).class_id != _room_or_404(
        session, target.classroom_id
    ).class_id:
        raise HTTPException(
            status_code=409, detail="Chapters can be copied only between sections of one class."
        )

    existing = _chapters_for(session, target.id)
    taken = {chapter.name.strip().lower() for chapter in existing}
    next_sequence = max((chapter.sequence for chapter in existing), default=0)
    keep_numbers = not existing

    copied = 0
    skipped: list[str] = []
    for chapter in _chapters_for(session, source.id):
        key = chapter.name.strip().lower()
        if key in taken:
            skipped.append(chapter.name)
            continue
        taken.add(key)
        next_sequence = chapter.sequence if keep_numbers else next_sequence + 1
        session.add(
            Chapter(
                classroom_subject_id=target.id,
                academic_year_id=target.academic_year_id,
                sequence=next_sequence,
                name=chapter.name,
                planned_date=chapter.planned_date,
                status=CHAPTER_PENDING,
            )
        )
        copied += 1
    session.commit()

    room = _room_or_404(session, target.classroom_id)
    return ChapterCopyResult(
        copied=copied,
        skipped=skipped,
        chapters=[
            _chapter_view(session, chapter, room, user)
            for chapter in _chapters_for(session, target.id)
        ],
    )


def _move_chapter(session: Session, chapter: Chapter, target: int) -> None:
    """Move to 1-based `target` and renumber the whole list, collision-free.

    Unique `(class, subject, session, sequence)` means we cannot simply swap two rows:
    the first update would collide. Every row goes to a negative number, flushes, then
    comes back at its final positive number - one transaction, no duplicate positions.
    """
    rows = _chapters_for(session, chapter.classroom_subject_id)
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

    if chapter.status == CHAPTER_COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="This chapter is completed; undo the tick first.",
        )

    used = session.exec(
        select(ExamPaperChapter.id).where(ExamPaperChapter.chapter_id == chapter.id)
    ).first()
    if used is not None:
        raise HTTPException(
            status_code=409,
            detail="An exam paper uses this chapter; remove it from the paper first.",
        )

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
    row = _course_row_or_404(session, chapter.classroom_subject_id)
    if row.classroom_id != room.id:
        raise HTTPException(
            status_code=409,
            detail="That chapter belongs to another class-section.",
        )

    status = (payload.status or "").strip()
    if status not in CHAPTER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {', '.join(CHAPTER_STATUSES)}.",
        )

    if not _may_tick(session, user, chapter.classroom_subject_id):
        raise HTTPException(
            status_code=403,
            detail="Only the teacher of this subject, or the office, can tick it.",
        )

    employee_id = _employee_of(session, user)
    chapter.status = status
    if status == CHAPTER_COMPLETED:
        chapter.completed_on = date.today()
        chapter.completed_by_employee_id = employee_id
    else:
        chapter.completed_on = None
        chapter.completed_by_employee_id = None

    session.add(chapter)
    session.commit()
    session.refresh(chapter)

    return _chapter_row(
        session,
        chapter,
        employee_names(
            session,
            [chapter.completed_by_employee_id]
            if chapter.completed_by_employee_id
            else [],
        ),
        date.today(),
        can_tick=True,
    )
