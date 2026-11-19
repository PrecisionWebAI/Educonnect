"""The Teachers > Course tab: every teacher's subjects, weeks and completion.

The Classroom tab answers "what is this section doing"; this answers "what is this
**person** carrying". The two read the same rows (`subjectteacher`, `lessonplan`,
`chapterprogress`), so a number cannot differ between the screens.

`course.view_all` sees the whole teaching roll. A teacher sees only their own row and
their own detail; another teacher's id is a `404`, not a `403` that would confirm it
exists.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ChapterProgress,
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import scope
from app.domains.academic.classroom.course.models import (
    PLAN_SUBMITTED,
    ClassroomSubject,
    LessonPlan,
)
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.labels import TEACHING_ROLES
from app.domains.people.teachers.profile.repository import employee_names

from . import completion, teaching_days
from .schemas import (
    CourseSummaryRead,
    CourseTeacherRow,
    TeacherAssignmentRow,
    TeacherChapterRow,
    TeacherCourseDetail,
    TeacherWeekRow,
)


def _teaching_users():
    return (
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(list(TEACHING_ROLES)))
    )


def _course_for(
    session: Session, classroom_id: UUID, subject_id: UUID
) -> ClassroomSubject | None:
    return session.exec(
        select(ClassroomSubject)
        .where(
            ClassroomSubject.classroom_id == classroom_id,
            ClassroomSubject.subject_id == subject_id,
        )
        .order_by(ClassroomSubject.created_at.desc())
    ).first()


def _labels(session: Session) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """(room labels, subject names) - one query each, no per-row lookup."""
    rooms = {
        room.id: f"{classroom.classname}-{section.section_name}"
        for room, classroom, section in session.exec(
            select(Classroom, ClassName, Section)
            .join(ClassName, ClassName.class_id == Classroom.class_id)
            .join(Section, Section.section_id == Classroom.section_id)
        ).all()
    }
    subjects = {
        subject.id: subject.name for subject in session.exec(select(Subject)).all()
    }
    return rooms, subjects


def _chapter_stats(
    session: Session,
) -> tuple[
    dict[tuple[UUID, UUID], int],
    dict[tuple[UUID, UUID, UUID], int],
    set[tuple[UUID, UUID, UUID]],
]:
    """(totals, done, behind) maps for every section subject."""
    totals = completion._chapter_totals(session)
    done = completion._done_totals(session)

    today = date.today()
    rooms_by_class: dict[UUID, set[UUID]] = {}
    for room_id, class_id in session.exec(
        select(Classroom.id, Classroom.class_id)
    ).all():
        rooms_by_class.setdefault(class_id, set()).add(room_id)

    behind: set[tuple[UUID, UUID, UUID]] = set()
    rows = session.exec(
        select(
            Chapter.class_id,
            Chapter.subject_id,
            ChapterProgress.classroom_id,
            ChapterProgress.status,
        )
        .join(
            ChapterProgress,
            ChapterProgress.chapter_id == Chapter.id,
            isouter=True,
        )
        .where(
            Chapter.planned_date.is_not(None),  # type: ignore[union-attr]
            Chapter.planned_date < today,
        )
    ).all()
    chapters: dict[tuple[UUID, UUID], dict[UUID | None, str | None]] = {}
    for class_id, subject_id, room_id, status in rows:
        chapters.setdefault((class_id, subject_id), {})[room_id] = status

    for (class_id, subject_id), by_room in chapters.items():
        for room_id in rooms_by_class.get(class_id, set()):
            # No row for this section is "not ticked", exactly like an explicit
            # pending row - both mean the planned date has passed unfinished.
            if by_room.get(room_id) != CHAPTER_COMPLETED:
                behind.add((room_id, class_id, subject_id))
    return totals, done, behind


def teacher_list(
    session: Session,
    user,
    *,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[CourseTeacherRow]:
    """The teaching roll with the counts the Course tab's first table shows."""
    if not scope.can_read_course(session, user):
        raise HTTPException(status_code=403, detail="You cannot read the course roll.")

    statement = (
        select(Employee, User)
        .join(User, User.id == Employee.user_id)
        .where(Employee.user_id.in_(_teaching_users()))
    )
    if not scope.can_view_all_courses(session, user):
        own = scope.employee_of(session, user)
        if own is None:
            return []
        statement = statement.where(Employee.id == own.id)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(User.full_name).like(like),
                func.lower(Employee.employee_code).like(like),
                func.lower(Employee.department).like(like),
            )
        )
    employees = list(
        session.exec(
            statement.order_by(User.full_name)
            .offset(max(0, skip))
            .limit(max(1, min(limit, 200)))
        ).all()
    )
    if not employees:
        return []

    employee_ids = [employee.id for employee, _user in employees]
    assignments = list(
        session.exec(
            select(SubjectTeacher)
            .where(
                SubjectTeacher.teacher_id.in_(employee_ids),
                SubjectTeacher.effective_to.is_(None),
            )
            .order_by(SubjectTeacher.effective_from)
        ).all()
    )
    by_teacher: dict[UUID, list[SubjectTeacher]] = {}
    for assignment in assignments:
        by_teacher.setdefault(assignment.teacher_id, []).append(assignment)

    totals, done, behind = _chapter_stats(session)
    course_cache: dict[tuple[UUID, UUID], ClassroomSubject | None] = {}
    course_ids: set[UUID] = set()
    for assignment in assignments:
        key = (assignment.classroom_id, assignment.subject_id)
        course = course_cache.get(key)
        if key not in course_cache:
            course = _course_for(session, *key)
            course_cache[key] = course
        if course is not None:
            course_ids.add(course.id)

    pending: dict[UUID, int] = {}
    if course_ids:
        for course_id, count in session.exec(
            select(LessonPlan.classroom_subject_id, func.count(LessonPlan.id))
            .where(
                LessonPlan.classroom_subject_id.in_(course_ids),
                LessonPlan.status == PLAN_SUBMITTED,
            )
            .group_by(LessonPlan.classroom_subject_id)
        ).all():
            pending[course_id] = int(count)

    result: list[CourseTeacherRow] = []
    for employee, user_row in employees:
        own_assignments = by_teacher.get(employee.id, [])
        subject_ids = {row.subject_id for row in own_assignments}
        section_ids = {row.classroom_id for row in own_assignments}
        percents: list[float] = []
        behind_subjects = 0
        course_ids_here: set[UUID] = set()
        for row in own_assignments:
            course = course_cache.get((row.classroom_id, row.subject_id))
            if course is not None:
                course_ids_here.add(course.id)
            room = session.get(Classroom, row.classroom_id)
            if room is None:
                continue
            total = totals.get((room.class_id, row.subject_id), 0)
            if total:
                completed = done.get(
                    (row.classroom_id, room.class_id, row.subject_id), 0
                )
                percents.append(100.0 * completed / total)
            if (row.classroom_id, room.class_id, row.subject_id) in behind:
                behind_subjects += 1

        result.append(
            CourseTeacherRow(
                employee_id=employee.id,
                name=user_row.full_name,
                employee_code=employee.employee_code,
                department=employee.department,
                subjects_count=len(subject_ids),
                sections_count=len(section_ids),
                pending_approvals=sum(pending.get(cid, 0) for cid in course_ids_here),
                behind_subjects=behind_subjects,
                completion_percent=(
                    round(sum(percents) / len(percents), 1) if percents else None
                ),
            )
        )
    return result


def _weeks(session: Session, course: ClassroomSubject | None) -> list[TeacherWeekRow]:
    if course is None:
        return []
    today = date.today()
    plans = {
        plan.week_no: plan
        for plan in session.exec(
            select(LessonPlan).where(
                LessonPlan.classroom_subject_id == course.id,
                LessonPlan.academic_year_id == course.academic_year_id,
                LessonPlan.year == today.year,
                LessonPlan.month == today.month,
            )
        ).all()
    }
    return [
        TeacherWeekRow(
            week_no=week.week_no,
            start_date=week.start_date,
            end_date=week.end_date,
            plan_id=plans[week.week_no].id if week.week_no in plans else None,
            status=plans[week.week_no].status if week.week_no in plans else None,
            version=plans[week.week_no].version if week.week_no in plans else 0,
            approved_version=(
                plans[week.week_no].approved_version if week.week_no in plans else None
            ),
            rejection_reason=(
                plans[week.week_no].rejection_reason if week.week_no in plans else None
            ),
        )
        for week in teaching_days.week_ranges(session, today.year, today.month)
    ]


def _chapters(
    session: Session, room: Classroom, subject_id: UUID, course: ClassroomSubject | None
) -> list[TeacherChapterRow]:
    if course is None:
        return []
    rows = list(
        session.exec(
            select(Chapter)
            .where(
                Chapter.class_id == room.class_id,
                Chapter.subject_id == subject_id,
                Chapter.academic_year_id == course.academic_year_id,
            )
            .order_by(Chapter.sequence)
        ).all()
    )
    progress = {
        row.chapter_id: row
        for row in session.exec(
            select(ChapterProgress).where(
                ChapterProgress.classroom_id == room.id,
                ChapterProgress.chapter_id.in_([chapter.id for chapter in rows]),
            )
        ).all()
    }
    names = employee_names(
        session,
        [
            row.completed_by_employee_id
            for row in progress.values()
            if row.completed_by_employee_id is not None
        ],
    )
    return [
        TeacherChapterRow(
            chapter_id=chapter.id,
            sequence=chapter.sequence,
            name=chapter.name,
            planned_date=chapter.planned_date,
            status=(
                progress[chapter.id].status if chapter.id in progress else "Pending"
            ),
            completed_on=(
                progress[chapter.id].completed_on if chapter.id in progress else None
            ),
            completed_by=(
                names.get(progress[chapter.id].completed_by_employee_id)
                if chapter.id in progress
                and progress[chapter.id].completed_by_employee_id is not None
                else None
            ),
        )
        for chapter in rows
    ]


def teacher_detail(session: Session, employee_id: UUID, user) -> TeacherCourseDetail:
    """One teacher's current and past subjects, with this month's weeks and progress."""
    if not scope.may_read_teacher_course(session, user, employee_id):
        raise HTTPException(status_code=404, detail="Teacher not found")

    row = session.exec(
        select(Employee, User)
        .join(User, User.id == Employee.user_id)
        .where(Employee.id == employee_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    employee, user_row = row

    assignments = list(
        session.exec(
            select(SubjectTeacher)
            .where(SubjectTeacher.teacher_id == employee_id)
            .order_by(SubjectTeacher.effective_from)
        ).all()
    )
    rooms, subjects = _labels(session)
    totals, done, _behind = _chapter_stats(session)
    course_cache: dict[tuple[UUID, UUID], ClassroomSubject | None] = {}
    result: list[TeacherAssignmentRow] = []

    for assignment in assignments:
        key = (assignment.classroom_id, assignment.subject_id)
        if key not in course_cache:
            course_cache[key] = _course_for(session, *key)
        course = course_cache[key]
        room = session.get(Classroom, assignment.classroom_id)
        total = totals.get((room.class_id, assignment.subject_id), 0) if room else 0
        completed = (
            done.get((assignment.classroom_id, room.class_id, assignment.subject_id), 0)
            if room
            else 0
        )
        current = assignment.effective_to is None
        result.append(
            TeacherAssignmentRow(
                classroom_subject_id=course.id if course is not None else None,
                section_id=assignment.classroom_id,
                label=rooms.get(assignment.classroom_id, "Class-section"),
                subject_id=assignment.subject_id,
                subject=subjects.get(assignment.subject_id, "Subject"),
                current=current,
                effective_from=assignment.effective_from,
                effective_to=assignment.effective_to,
                done=completed,
                total=total,
                percent=round(100.0 * completed / total, 1) if total else None,
                weeks=_weeks(session, course) if current else [],
                chapters=(
                    _chapters(session, room, assignment.subject_id, course)
                    if current and room is not None
                    else []
                ),
            )
        )

    result.sort(key=lambda item: (not item.current, item.label, item.subject))
    return TeacherCourseDetail(
        employee_id=employee.id,
        name=user_row.full_name,
        employee_code=employee.employee_code,
        department=employee.department,
        assignments=result,
    )


def my_course(session: Session, user) -> TeacherCourseDetail:
    employee = scope.employee_of(session, user)
    if employee is None:
        raise HTTPException(status_code=404, detail="No employee record for this login")
    return teacher_detail(session, employee.id, user)


def summary(session: Session, user) -> CourseSummaryRead:
    """The Course badge: subjects, submitted weeks and D7 completion, scoped."""
    if not scope.can_read_course(session, user):
        raise HTTPException(
            status_code=403, detail="You cannot read the course summary."
        )
    year = completion.current_year(session)
    if year is None:
        return CourseSummaryRead()

    courses = list(
        session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.academic_year_id == year.id,
                ClassroomSubject.status == "Active",
            )
        ).all()
    )
    unrestricted = any(
        (
            scope.can_manage_course(session, user),
            scope.can_view_all_courses(session, user),
            scope.can_approve_course(session, user),
        )
    )
    if not unrestricted:
        by_room: dict[UUID, list[ClassroomSubject]] = {}
        for course in courses:
            by_room.setdefault(course.classroom_id, []).append(course)
        allowed: set[UUID] = set()
        for room_id, room_courses in by_room.items():
            visible = scope.visible_course_subject_ids(session, user, room_id)
            if visible is None:
                allowed |= {course.id for course in room_courses}
            else:
                allowed |= {
                    course.id for course in room_courses if course.id in visible
                }
        courses = [course for course in courses if course.id in allowed]

    if not courses:
        return CourseSummaryRead()

    course_ids = [course.id for course in courses]
    pending = 0
    if course_ids:
        pending = int(
            session.exec(
                select(func.count())
                .select_from(LessonPlan)
                .where(
                    LessonPlan.classroom_subject_id.in_(course_ids),
                    LessonPlan.status == PLAN_SUBMITTED,
                )
            ).one()
        )

    totals, done, _behind = _chapter_stats(session)
    rooms = dict(
        session.exec(
            select(Classroom.id, Classroom.class_id).where(
                Classroom.id.in_({course.classroom_id for course in courses})
            )
        ).all()
    )
    percents: list[float] = []
    for course in courses:
        class_id = rooms.get(course.classroom_id)
        total = totals.get((class_id, course.subject_id), 0) if class_id else 0
        if total:
            completed = done.get((course.classroom_id, class_id, course.subject_id), 0)
            percents.append(100.0 * completed / total)
    return CourseSummaryRead(
        subject_count=len(courses),
        pending_approvals=pending,
        completion_percent=(
            round(sum(percents) / len(percents), 1) if percents else None
        ),
    )


def section_summary(session: Session, section_id: UUID, user) -> CourseSummaryRead:
    """The Classroom card's Course line for one section."""
    if not scope.may_read_section_course(session, user, section_id):
        raise HTTPException(status_code=404, detail="Class-section not found")
    year = completion.current_year(session)
    if year is None:
        return CourseSummaryRead()

    courses = list(
        session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.classroom_id == section_id,
                ClassroomSubject.academic_year_id == year.id,
                ClassroomSubject.status == "Active",
            )
        ).all()
    )
    course_ids = [course.id for course in courses]
    pending = 0
    if course_ids:
        pending = int(
            session.exec(
                select(func.count())
                .select_from(LessonPlan)
                .where(
                    LessonPlan.classroom_subject_id.in_(course_ids),
                    LessonPlan.status == PLAN_SUBMITTED,
                )
            ).one()
        )
    average = completion.for_section_average(session, section_id)
    return CourseSummaryRead(
        subject_count=len(courses),
        pending_approvals=pending,
        completion_percent=average[0] if average is not None else None,
    )
