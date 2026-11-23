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

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    CHAPTER_IN_PROGRESS,
    CHAPTER_PENDING,
    CHAPTER_SKIPPED,
    CHAPTER_STATUSES,
    Chapter,
    Classroom,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import room_label
from app.domains.academic.classroom.course.models import (
    CHAPTER_PLAN_APPROVED,
    CHAPTER_PLAN_DRAFT,
    CHAPTER_PLAN_SUBMITTED,
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
    ChapterCreate,
    ChapterRowRead,
    ChapterTickIn,
    ChapterUpdate,
    CourseSubjectRowRead,
    CourseTeacherAssignIn,
    CourseTeacherRead,
    LessonPlanSummaryRead,
    PlanRejectIn,
    ProgressSaveIn,
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
    closed = status in (CHAPTER_COMPLETED, CHAPTER_SKIPPED)

    ahead: bool | None = None
    if finished and chapter.planned_date is not None and completed_on is not None:
        ahead = completed_on <= chapter.planned_date
    behind = (
        not closed and chapter.planned_date is not None and chapter.planned_date < today
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
        ahead=ahead,
        behind=behind,
        can_tick=can_tick,
        can_edit=can_edit,
        proposed_status=chapter.proposed_status,
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
    approver = scope.can_approve_course(session, user)
    plans = _plan_counts(session, course_ids)
    completed = _completed_counts(session, course_ids)
    plan_summary = _lesson_plan_summary(session, course_ids, today.year, today.month)

    result: list[SubjectCourseRead] = []
    for course_subject in course_rows:
        timeline = by_course.get(course_subject.id, [])
        chapters = chapters_by_course.get(course_subject.id, [])
        holds = course_subject.id in tickable
        plan_state = course_subject.chapter_plan_status
        reapproval = _reapproval_pending(course_subject)
        can_edit_plan = holds and _plan_open_to_edit(course_subject)
        can_save = holds and (plan_state == CHAPTER_PLAN_APPROVED or reapproval)
        rows = [
            _chapter_row(
                session,
                chapter,
                names,
                today,
                can_tick=can_save,
                can_edit=can_edit_plan,
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
                # The chapter the class is on: the first one still open; when every chapter
                # is closed, the last one (the line under the subject name never vanishes).
                next_chapter=next(
                    (
                        f"Ch {row.sequence} · {row.name}"
                        for row in rows
                        if row.status not in (CHAPTER_COMPLETED, CHAPTER_SKIPPED)
                    ),
                    f"Ch {rows[-1].sequence} · {rows[-1].name}" if rows else None,
                ),
                skipped=sum(1 for row in rows if row.status == CHAPTER_SKIPPED),
                pending_approval=sum(1 for row in rows if row.proposed_status),
                chapter_plan_status=plan_state,
                chapter_plan_reapproval=reapproval,
                # The number the table shows while edits wait: what was last approved.
                approved_total=(
                    course_subject.chapter_plan_approved_count if reapproval else None
                ),
                chapter_plan_reject_reason=course_subject.chapter_plan_reject_reason,
                can_edit_plan=can_edit_plan,
                can_submit_plan=bool(
                    plan_state == CHAPTER_PLAN_DRAFT and holds and total > 0
                ),
                can_save_progress=can_save,
                can_approve=approver,
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
    owner = _course_row_or_404(session, chapter.classroom_subject_id)
    plan_state = owner.chapter_plan_status
    holds = _may_tick(session, user, chapter.classroom_subject_id)
    names = employee_names(
        session,
        [chapter.completed_by_employee_id] if chapter.completed_by_employee_id else [],
    )
    return _chapter_row(
        session,
        chapter,
        names,
        date.today(),
        can_tick=holds
        and (plan_state == CHAPTER_PLAN_APPROVED or _reapproval_pending(owner)),
        can_edit=holds and _plan_open_to_edit(owner),
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
    """Add a chapter to this subject's list.

    `sequence` omitted appends (the screen numbers it 1, 2, 3...); an occupied explicit
    sequence is refused (`409`) instead of silently renumbering the book. Allowed while
    the list is a Draft (the teacher of the subject or the office) and, once approved,
    for the office only.
    """
    row = _course_row_or_404(session, classroom_subject_id)
    _require_plan_edit(session, user, row)
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
    _reopen_for_approval(row)
    session.add(row)
    session.commit()
    session.refresh(chapter)
    return _chapter_view(session, chapter, room, user)


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
    """Rename, re-date or move one chapter (see `_require_plan_edit` for who)."""
    chapter = _chapter_or_404(session, chapter_id)
    _require_plan_edit(
        session, user, _course_row_or_404(session, chapter.classroom_subject_id)
    )
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

    owner_row = _course_row_or_404(session, chapter.classroom_subject_id)
    _reopen_for_approval(owner_row)
    session.add(owner_row)
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
    chapter = _chapter_or_404(session, chapter_id)
    row = _course_row_or_404(session, chapter.classroom_subject_id)
    _require_plan_edit(session, user, row)

    if (
        chapter.status in (CHAPTER_COMPLETED, CHAPTER_SKIPPED)
        or chapter.proposed_status
    ):
        raise HTTPException(
            status_code=409,
            detail="This chapter already has progress; undo it first.",
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
    session.flush()
    # A gap left by a delete is closed, so the numbers (1, 2, 3...) stay honest.
    remaining = _chapters_for(session, row.id)
    for index, other in enumerate(remaining, start=1):
        other.sequence = -index
        session.add(other)
    session.flush()
    for index, other in enumerate(remaining, start=1):
        other.sequence = index
        session.add(other)
    _reopen_for_approval(row)
    session.add(row)
    session.commit()


# ------------------------------------------------------------- chapter list lifecycle


def _reapproval_pending(row: ClassroomSubject) -> bool:
    """Changes made to an approved list that the principal has not approved yet.

    The list was approved once (`chapter_plan_decided_at`) and is `Submitted` again.
    The earlier approval stays in use for teaching meanwhile; the edits wait.
    """
    return (
        row.chapter_plan_status == CHAPTER_PLAN_SUBMITTED
        and row.chapter_plan_decided_at is not None
    )


def _plan_open_to_edit(row: ClassroomSubject) -> bool:
    """May the list be changed right now (by whoever holds the subject, or the office)?"""
    return row.chapter_plan_status in (
        CHAPTER_PLAN_DRAFT,
        CHAPTER_PLAN_APPROVED,
    ) or _reapproval_pending(row)


def _reopen_for_approval(row: ClassroomSubject) -> None:
    """Any change to an approved list sends it back to the principal."""
    if row.chapter_plan_status == CHAPTER_PLAN_APPROVED:
        row.chapter_plan_status = CHAPTER_PLAN_SUBMITTED
        row.chapter_plan_submitted_at = datetime.utcnow()
        row.chapter_plan_reject_reason = None


def _require_plan_edit(session: Session, user, row: ClassroomSubject) -> None:
    """Who may change the chapter list right now.

    The teacher who holds the subject, or the office. A first submission is locked while
    it waits for the principal. Once a list has been approved it can still be changed -
    but every change sends it back for approval (`_reopen_for_approval`).
    """
    if row.status != COURSE_ACTIVE:
        raise HTTPException(status_code=409, detail="This subject is archived.")
    if not _plan_open_to_edit(row):
        raise HTTPException(
            status_code=409,
            detail="The chapter list is waiting for approval and cannot be changed.",
        )
    if not _may_tick(session, user, row.id):
        raise HTTPException(
            status_code=403,
            detail="Only the teacher of this subject, or the office, can plan chapters.",
        )


def _require_approver(session: Session, user) -> None:
    if not scope.can_approve_course(session, user):
        raise HTTPException(
            status_code=403,
            detail="Only the principal's office can approve chapters.",
        )


def _save_plan_row(session: Session, row: ClassroomSubject) -> CourseSubjectRowRead:
    session.add(row)
    session.commit()
    session.refresh(row)
    return _row_read(row)


def submit_chapter_plan(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    """The teacher sends the finished list to the principal's office."""
    row = _course_row_or_404(session, classroom_subject_id)
    if row.chapter_plan_status != CHAPTER_PLAN_DRAFT:
        raise HTTPException(status_code=409, detail="The list is already submitted.")
    _require_plan_edit(session, user, row)
    if not _chapters_for(session, row.id):
        raise HTTPException(status_code=409, detail="Add at least one chapter first.")
    row.chapter_plan_status = CHAPTER_PLAN_SUBMITTED
    row.chapter_plan_submitted_at = datetime.utcnow()
    row.chapter_plan_reject_reason = None
    return _save_plan_row(session, row)


def approve_chapter_plan(
    session: Session, classroom_subject_id: UUID, user=None
) -> CourseSubjectRowRead:
    _require_approver(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    if row.chapter_plan_status != CHAPTER_PLAN_SUBMITTED:
        raise HTTPException(status_code=409, detail="Nothing is waiting for approval.")
    row.chapter_plan_status = CHAPTER_PLAN_APPROVED
    row.chapter_plan_decided_at = datetime.utcnow()
    row.chapter_plan_reject_reason = None
    row.chapter_plan_approved_count = len(_chapters_for(session, row.id))
    return _save_plan_row(session, row)


def reject_chapter_plan(
    session: Session, classroom_subject_id: UUID, payload: PlanRejectIn, user=None
) -> CourseSubjectRowRead:
    """Send the list back to the teacher with the reason."""
    _require_approver(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    if row.chapter_plan_status != CHAPTER_PLAN_SUBMITTED:
        raise HTTPException(status_code=409, detail="Nothing is waiting for approval.")
    row.chapter_plan_status = CHAPTER_PLAN_DRAFT
    row.chapter_plan_decided_at = datetime.utcnow()
    row.chapter_plan_reject_reason = payload.reason
    return _save_plan_row(session, row)


# ------------------------------------------------------------------ approved progress

_SAVEABLE = (CHAPTER_PENDING, CHAPTER_COMPLETED, CHAPTER_SKIPPED)


def _clear_proposal(chapter: Chapter) -> None:
    chapter.proposed_status = None
    chapter.proposed_by_employee_id = None
    chapter.proposed_at = None
    chapter.proposed_auto = False


def _apply_proposals(chapters: list[Chapter], today: date) -> None:
    """The principal's approval: what the teacher saved becomes the real status."""
    for chapter in chapters:
        if not chapter.proposed_status:
            continue
        chapter.status = chapter.proposed_status
        chapter.auto_skipped = bool(
            chapter.proposed_auto and chapter.status == CHAPTER_SKIPPED
        )
        if chapter.status == CHAPTER_COMPLETED:
            chapter.completed_on = today
            chapter.completed_by_employee_id = chapter.proposed_by_employee_id
        else:
            chapter.completed_on = None
            chapter.completed_by_employee_id = None
        _clear_proposal(chapter)


def _chapter_rows_for(
    session: Session, row: ClassroomSubject, user
) -> list[ChapterRowRead]:
    room = _room_or_404(session, row.classroom_id)
    return [
        _chapter_view(session, chapter, room, user)
        for chapter in _chapters_for(session, row.id)
    ]


def _settled(chapter: Chapter) -> str:
    """The approved status, with the old 'In progress' read as Pending."""
    if chapter.status == CHAPTER_IN_PROGRESS:
        return CHAPTER_PENDING
    return chapter.status


def save_progress(
    session: Session, classroom_subject_id: UUID, payload: ProgressSaveIn, user=None
) -> list[ChapterRowRead]:
    """The teacher saves Completed / Skipped for one or many chapters.

    Chapters go in order: finishing chapter 4 while 2 and 3 are still pending marks 2
    and 3 **Skipped** (they can still be completed later). Nothing moves a count until the
    principal (or a senior) approves - every save waits, including an approver's own.
    Taking a Completed chapter back to Pending is a change too, and the chapters that were
    skipped only because of it go back to Pending when nothing finished comes after them.
    """
    row = _course_row_or_404(session, classroom_subject_id)
    if row.status != COURSE_ACTIVE:
        raise HTTPException(status_code=409, detail="This subject is archived.")
    if row.chapter_plan_status != CHAPTER_PLAN_APPROVED and not _reapproval_pending(
        row
    ):
        raise HTTPException(
            status_code=409,
            detail="The chapter list must be approved before progress is saved.",
        )
    if not _may_tick(session, user, row.id):
        raise HTTPException(
            status_code=403,
            detail="Only the teacher of this subject, or the office, can save progress.",
        )

    chapters = _chapters_for(session, row.id)
    known = {chapter.id for chapter in chapters}
    asked: dict[UUID, str] = {}
    for item in payload.items:
        status = (item.status or "").strip()
        if item.chapter_id not in known:
            raise HTTPException(status_code=404, detail="Chapter not found")
        if status not in _SAVEABLE:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {', '.join(_SAVEABLE)}.",
            )
        asked[item.chapter_id] = status

    # What each chapter would be after this save. Everything a teacher (or the principal)
    # saves is a *proposal*: nothing moves a count until an approver approves it.
    target: dict[UUID, str] = {}
    auto: dict[UUID, bool] = {}
    for chapter in chapters:
        settled = _settled(chapter)
        if chapter.id in asked:
            target[chapter.id] = asked[chapter.id]
            auto[chapter.id] = False
        elif chapter.proposed_status:
            target[chapter.id] = chapter.proposed_status
            auto[chapter.id] = chapter.proposed_auto
        else:
            target[chapter.id] = settled
            auto[chapter.id] = chapter.auto_skipped

    last_done = max(
        (c.sequence for c in chapters if target[c.id] == CHAPTER_COMPLETED), default=0
    )
    for chapter in chapters:
        current = target[chapter.id]
        if current == CHAPTER_PENDING and chapter.sequence < last_done:
            # A chapter left behind while a later one is finished is skipped.
            target[chapter.id] = CHAPTER_SKIPPED
            auto[chapter.id] = True
        elif (
            current == CHAPTER_SKIPPED
            and auto[chapter.id]
            and chapter.id not in asked
            and chapter.sequence > last_done
        ):
            # It was skipped only because of a chapter that is no longer finished.
            target[chapter.id] = CHAPTER_PENDING
            auto[chapter.id] = False

    employee_id = _employee_of(session, user)
    now = datetime.utcnow()
    for chapter in chapters:
        want = target[chapter.id]
        if want == _settled(chapter) and auto[chapter.id] == chapter.auto_skipped:
            _clear_proposal(chapter)
        elif (
            chapter.proposed_status != want or chapter.proposed_auto != auto[chapter.id]
        ):
            chapter.proposed_status = want
            chapter.proposed_auto = auto[chapter.id]
            chapter.proposed_by_employee_id = employee_id
            chapter.proposed_at = now
        session.add(chapter)

    session.commit()
    return _chapter_rows_for(session, row, user)


def approve_progress(
    session: Session, classroom_subject_id: UUID, user=None
) -> list[ChapterRowRead]:
    _require_approver(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    chapters = _chapters_for(session, row.id)
    if not any(chapter.proposed_status for chapter in chapters):
        raise HTTPException(status_code=409, detail="Nothing is waiting for approval.")
    _apply_proposals(chapters, date.today())
    for chapter in chapters:
        session.add(chapter)
    session.commit()
    return _chapter_rows_for(session, row, user)


def reject_progress(
    session: Session, classroom_subject_id: UUID, user=None
) -> list[ChapterRowRead]:
    """Send the saved change back: the chapters go back to what they were."""
    _require_approver(session, user)
    row = _course_row_or_404(session, classroom_subject_id)
    chapters = _chapters_for(session, row.id)
    if not any(chapter.proposed_status for chapter in chapters):
        raise HTTPException(status_code=409, detail="Nothing is waiting for approval.")
    for chapter in chapters:
        _clear_proposal(chapter)
        session.add(chapter)
    session.commit()
    return _chapter_rows_for(session, row, user)


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
