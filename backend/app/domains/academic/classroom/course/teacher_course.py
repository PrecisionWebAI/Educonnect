"""The Teachers > Course tab: every teacher's subjects, weeks and completion.

The Classroom tab answers "what is this section doing"; this answers "what is this
**person** carrying". The two read the same rows (`subjectteacher`, `lessonplan`,
`chapterprogress`), so a number cannot differ between the screens.

`course.view_all` sees the whole teaching roll. A teacher sees only their own row and
their own detail; another teacher's id is a `404`, not a `403` that would confirm it
exists.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import scope
from app.domains.academic.classroom.course.models import (
    CHAPTER_PLAN_SUBMITTED,
    PLAN_SUBMITTED,
    ClassroomSubject,
    LessonPlan,
)
from app.domains.academic.classroom.timetable import history as timetable_history
from app.domains.academic.classroom.timetable import service as timetable_service
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as teacher_labels
from app.domains.people.teachers.labels import TEACHING_ROLES
from app.domains.people.teachers.profile.repository import employee_names
from app.domains.people.teachers.substitution.models import SubstitutionAssignment
from app.domains.people.teachers.workload import repository as workload_repository

from . import completion, teaching_days
from .schemas import (
    ClassCoverageRow,
    CourseSummaryRead,
    CourseTeacherRow,
    TeacherAssignmentRow,
    TeacherChapterRow,
    TeacherCourseDetail,
    TeacherTimetablePeriod,
    TeacherTimetableRead,
    TeacherWeekRow,
)


def _teaching_users():
    return (
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(list(TEACHING_ROLES)))
    )


def _course_for(
    session: Session, classroom_subject_id: UUID | None
) -> ClassroomSubject | None:
    if classroom_subject_id is None:
        return None
    return session.get(ClassroomSubject, classroom_subject_id)


def _labels(session: Session) -> dict[UUID, str]:
    """{room id: "Class 9-A"} - one query, no per-row lookup."""
    rooms = {
        room.id: f"{classroom.classname}-{section.section_name}"
        for room, classroom, section in session.exec(
            select(Classroom, ClassName, Section)
            .join(ClassName, ClassName.class_id == Classroom.class_id)
            .join(Section, Section.section_id == Classroom.section_id)
        ).all()
    }
    return rooms


def _pending_by_course(session: Session, course_ids: set[UUID]) -> dict[UUID, int]:
    """{section subject id: approvals waiting on a reviewer}, three grouped reads.

    One number covers every kind of request the teacher has made: a submitted lesson-plan
    week, a submitted chapter list, and each chapter whose completion is proposed.
    """
    pending: dict[UUID, int] = {}
    if not course_ids:
        return pending

    for course_id, count in session.exec(
        select(LessonPlan.classroom_subject_id, func.count(LessonPlan.id))
        .where(
            LessonPlan.classroom_subject_id.in_(course_ids),
            LessonPlan.status == PLAN_SUBMITTED,
        )
        .group_by(LessonPlan.classroom_subject_id)
    ).all():
        pending[course_id] = pending.get(course_id, 0) + int(count)

    for course_id in session.exec(
        select(ClassroomSubject.id).where(
            ClassroomSubject.id.in_(course_ids),
            ClassroomSubject.chapter_plan_status == CHAPTER_PLAN_SUBMITTED,
        )
    ).all():
        pending[course_id] = pending.get(course_id, 0) + 1

    for course_id, count in session.exec(
        select(Chapter.classroom_subject_id, func.count(Chapter.id))
        .where(
            Chapter.classroom_subject_id.in_(course_ids),
            Chapter.proposed_status.is_not(None),  # type: ignore[union-attr]
        )
        .group_by(Chapter.classroom_subject_id)
    ).all():
        pending[course_id] = pending.get(course_id, 0) + int(count)
    return pending


def _room_names(
    session: Session, room_ids: set[UUID]
) -> dict[UUID, tuple[int, str, str]]:
    """{room id: (class level, class name, section name)} for just these rooms."""
    if not room_ids:
        return {}
    return {
        room.id: (classname.level, classname.classname, section.section_name)
        for room, classname, section in session.exec(
            select(Classroom, ClassName, Section)
            .join(ClassName, ClassName.class_id == Classroom.class_id)
            .join(Section, Section.section_id == Classroom.section_id)
            .where(Classroom.id.in_(room_ids))
        ).all()
    }


def _class_coverage(
    room_names: dict[UUID, tuple[int, str, str]], room_ids: set[UUID]
) -> list[ClassCoverageRow]:
    """One row per class with its sections together, lowest class first.

    Ordered by the class `level`, not the name: as text "Class 10" sorts before "Class 2".
    """
    grouped: dict[tuple[int, str], set[str]] = {}
    for room_id in room_ids:
        names = room_names.get(room_id)
        if names is None:
            continue
        level, class_name, section_name = names
        grouped.setdefault((level, class_name), set()).add(section_name)
    return [
        ClassCoverageRow(class_name=class_name, sections=sorted(sections), level=level)
        for (level, class_name), sections in sorted(grouped.items())
    ]


def _periods_per_week(
    session: Session, teacher_ids: list[UUID]
) -> dict[UUID, int]:
    """{employee id: timetable slots a week}, from the current year's timetable.

    One slot is one row of `timetableperiod` naming the teacher, so a teacher who takes
    Maths in 9-A on Monday 9:00 has one period there, whatever the subject. Rows with no
    year are the timetable's legacy rows and count as the current year, as the timetable
    screens do.
    """
    if not teacher_ids:
        return {}
    statement = _in_current_year(
        session,
        select(TimetablePeriod.teacher_id, func.count(TimetablePeriod.id))
        .where(TimetablePeriod.teacher_id.in_(teacher_ids))
        .group_by(TimetablePeriod.teacher_id),  # type: ignore[arg-type]
    )
    return {
        teacher_id: int(count) for teacher_id, count in session.exec(statement).all()
    }


def _in_current_year(session: Session, statement):
    """Keep to the current year's timetable (plus legacy rows with no year)."""
    year = completion.current_academic_year(session)
    if year is None:
        return statement
    return statement.where(
        or_(
            TimetablePeriod.academic_year_id == year.id,
            TimetablePeriod.academic_year_id.is_(None),  # type: ignore[union-attr]
        )
    )


def teacher_timetable(
    session: Session, employee_id: UUID, user
) -> TeacherTimetableRead:
    """One teacher's whole week - every class-section and subject they are put in.

    The same scope as the detail: the office reads anybody's, a teacher only their own,
    and another person's id is a `404`. The count in the list and this grid read the same
    rows, so the number on the badge is the number of cells here.
    """
    if not scope.may_read_teacher_course(session, user, employee_id):
        raise HTTPException(status_code=404, detail="Teacher not found")
    if session.get(Employee, employee_id) is None:
        raise HTTPException(status_code=404, detail="Teacher not found")

    rows = session.exec(
        _in_current_year(
            session,
            select(TimetablePeriod, ClassName, Section, ClassroomSubject)
            .join(Classroom, Classroom.id == TimetablePeriod.classroom_id)
            .join(ClassName, ClassName.class_id == Classroom.class_id)
            .join(Section, Section.section_id == Classroom.section_id)
            .join(
                ClassroomSubject,
                ClassroomSubject.id == TimetablePeriod.classroom_subject_id,
            )
            .where(TimetablePeriod.teacher_id == employee_id),
        ).order_by(TimetablePeriod.start_time)
    ).all()
    return TeacherTimetableRead(
        bell=timetable_service.bell_schedule(session),
        periods=[
            TeacherTimetablePeriod(
                day_of_week=str(period.day_of_week),
                start_time=period.start_time,
                end_time=period.end_time,
                section_id=period.classroom_id,
                class_name=classname.classname,
                section_name=section.section_name,
                subject=course.name,
                room=period.room,
            )
            for period, classname, section, course in rows
        ],
    )


def _chapters_per_month(
    session: Session, teacher_ids: list[UUID]
) -> tuple[dict[UUID, int], int]:
    """({teacher id: chapters completed}, whole months counted) up to the end of last month.

    The window is the session's first day to the last day of the previous month, and the
    divisor is the number of whole months in it - so a teacher four months in is judged on
    four months, and the month still running is left out until it closes. A chapter belongs
    to the teacher who completed it (`completed_by_employee_id`), so a mid-year change of
    teacher splits the chapters between the two people. With no academic year, or in the
    session's first month, there is no whole month yet: no count and no average.
    """
    year = completion.current_academic_year(session)
    if year is None or not teacher_ids:
        return {}, 0
    # After the session closes the last month is its own last month, not "this month".
    reference = min(date.today(), year.end_date + timedelta(days=1))
    this_month = reference.replace(day=1)
    months = (this_month.year - year.start_date.year) * 12 + (
        this_month.month - year.start_date.month
    )
    if months <= 0:
        return {}, 0
    counts: dict[UUID, int] = {}
    for teacher_id, count in session.exec(
        select(Chapter.completed_by_employee_id, func.count(Chapter.id))
        .where(
            Chapter.completed_by_employee_id.in_(teacher_ids),
            Chapter.status == CHAPTER_COMPLETED,
            Chapter.completed_on >= year.start_date,
            Chapter.completed_on < this_month,
        )
        .group_by(Chapter.completed_by_employee_id)  # type: ignore[arg-type]
    ).all():
        counts[teacher_id] = int(count)
    return counts, months


def _lesson_slots_per_day(session: Session) -> int:
    """Teaching periods in one school day, from the school's own bell schedule.

    The regular lessons only: a break is not a period, and the extra classes (E1, E2...)
    are an add-on a school may or may not run, so they are not part of a full day.
    """
    return sum(
        1
        for slot in timetable_service.bell_schedule(session)
        if not slot.is_break and not slot.extra
    )


def _week_capacity(session: Session) -> int:
    """Every teaching period of a full school week: lessons a day x the days it runs.

    Eight periods over Monday to Saturday is 48. The days are the ones the school is not
    regularly closed (its weekly offs), so a five-day school gets 5 x its periods. This is
    the whole of what a teacher could be given, so a teacher placed in 1 of 48 carries 2%.
    """
    from app.domains.admin.settings import calendar as school_calendar

    working_days = 7 - len(school_calendar.weekly_off_days(session))
    return _lesson_slots_per_day(session) * max(working_days, 0)


def _yearly(
    session: Session, teacher_ids: list[UUID]
) -> dict[UUID, timetable_history.YearLoad]:
    """Classes taken, covers done and free classes, from the session's first day to today.

    Only **open school days** count - weekly offs and holidays are out of the classes, the
    covers and the free slots alike (a cover can only happen on a day school is open). The
    window is the current academic year up to today; with no year set there is no "since the
    session began", so nothing is counted rather than guessed.

    The timetable's own history gives each day's scheduled classes, so a mid-year change of
    teacher splits the count between the two people. An approved cover moves a class from
    the absent teacher (who did not take it) to the substitute (who did). A day's lesson
    slots are the regular (not extra, not break) periods of the school's bell schedule.
    """
    year = completion.current_academic_year(session)
    if year is None or not teacher_ids:
        return {}
    start = year.start_date
    end = min(date.today(), year.end_date)
    if end < start:
        return {}
    covers = session.exec(
        select(
            SubstitutionAssignment.on_date,
            SubstitutionAssignment.substitute_employee_id,
            SubstitutionAssignment.absent_employee_id,
        ).where(
            SubstitutionAssignment.status == teacher_labels.APPROVED,
            SubstitutionAssignment.on_date >= start,
            SubstitutionAssignment.on_date <= end,
            or_(
                SubstitutionAssignment.substitute_employee_id.in_(teacher_ids),
                SubstitutionAssignment.absent_employee_id.in_(teacher_ids),
            ),
        )
    ).all()
    return timetable_history.year_load(
        session,
        teacher_ids,
        start,
        end,
        slots_per_day=_lesson_slots_per_day(session),
        covers=covers,
    )


def _unique_subjects(names) -> list[str]:
    """Distinct subject names, trimmed, lowercase and A-Z.

    "Maths", "maths " and "MATHS" are one subject, written "maths": the names are typed by
    hand per class-section, so the same subject arrives in many spellings.
    """
    return sorted({name for raw in names if (name := (raw or "").strip().lower())})


def _chapter_stats(
    session: Session,
) -> tuple[dict[UUID, int], dict[UUID, int], set[UUID]]:
    """(totals, done, behind) maps keyed by classroom-subject id."""
    totals = completion._chapter_totals(session)
    done = completion._done_totals(session)
    today = date.today()
    behind: set[UUID] = set()
    rows = session.exec(
        select(Chapter.classroom_subject_id, Chapter.status).where(
            Chapter.planned_date.is_not(None),  # type: ignore[union-attr]
            Chapter.planned_date < today,
        )
    ).all()
    for course_id, status in rows:
        if status != CHAPTER_COMPLETED:
            behind.add(course_id)
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

    course_cache: dict[UUID, ClassroomSubject | None] = {}
    course_ids: set[UUID] = set()
    for assignment in assignments:
        key = assignment.classroom_subject_id
        if key not in course_cache:
            course_cache[key] = _course_for(session, key)
        course = course_cache[key]
        if course is not None:
            course_ids.add(course.id)

    pending = _pending_by_course(session, course_ids)
    periods = _periods_per_week(session, employee_ids)
    loads = _yearly(session, employee_ids)
    chapters_done, chapter_months = _chapters_per_month(session, employee_ids)
    # The Load column is periods held out of every period the school's week has; the
    # Light / Steady / Overloaded lines are the Workload tab's own.
    week_capacity = _week_capacity(session)
    workload_rule = workload_repository.rule(session)
    overload_percent = workload_rule.overload_percent if workload_rule else 100
    underload_percent = workload_rule.underload_percent if workload_rule else 60
    # The class-sections each teacher runs as class teacher: a job, not a subject, so it
    # is read from the room itself and may include a section they teach nothing in.
    own_rooms = workload_repository.class_teacher_rooms(session, employee_ids)
    room_names = _room_names(
        session,
        {course.classroom_id for course in course_cache.values() if course is not None}
        | {room for rooms in own_rooms.values() for room in rooms},
    )

    result: list[CourseTeacherRow] = []
    for employee, user_row in employees:
        own_assignments = by_teacher.get(employee.id, [])
        section_ids = {
            course_cache[row.classroom_subject_id].classroom_id
            for row in own_assignments
            if course_cache.get(row.classroom_subject_id) is not None
        }
        course_ids_here: set[UUID] = {
            course_cache[row.classroom_subject_id].id
            for row in own_assignments
            if course_cache.get(row.classroom_subject_id) is not None
        }

        result.append(
            CourseTeacherRow(
                employee_id=employee.id,
                name=user_row.full_name,
                employee_code=employee.employee_code,
                department=employee.department,
                subjects_count=len(course_ids_here),
                sections_count=len(section_ids),
                pending_approvals=sum(pending.get(cid, 0) for cid in course_ids_here),
                classes=_class_coverage(room_names, section_ids),
                class_teacher_of=_class_coverage(
                    room_names, own_rooms.get(employee.id, set())
                ),
                subjects=_unique_subjects(
                    course_cache[cid].name
                    for cid in course_ids_here
                    if course_cache.get(cid) is not None
                ),
                periods_per_week=periods.get(employee.id, 0),
                classes_yearly=loads[employee.id].classes if employee.id in loads else 0,
                free_yearly=loads[employee.id].free if employee.id in loads else 0,
                capacity_yearly=loads[employee.id].capacity if employee.id in loads else 0,
                chapters_completed=chapters_done.get(employee.id, 0),
                months_counted=chapter_months,
                chapters_per_month=(
                    round(chapters_done.get(employee.id, 0) / chapter_months, 1)
                    if chapter_months
                    else 0.0
                ),
                substitutions_yearly=(
                    loads[employee.id].substitutions if employee.id in loads else 0
                ),
                load_percent=(
                    round(periods.get(employee.id, 0) * 100 / week_capacity)
                    if week_capacity > 0
                    else 0
                ),
                load_band=teacher_labels.workload_band(
                    periods.get(employee.id, 0),
                    week_capacity,
                    overload_percent=overload_percent,
                    underload_percent=underload_percent,
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
    session: Session, course: ClassroomSubject | None
) -> list[TeacherChapterRow]:
    if course is None:
        return []
    rows = list(
        session.exec(
            select(Chapter)
            .where(Chapter.classroom_subject_id == course.id)
            .order_by(Chapter.sequence)
        ).all()
    )
    names = employee_names(
        session,
        [
            chapter.completed_by_employee_id
            for chapter in rows
            if chapter.completed_by_employee_id is not None
        ],
    )
    return [
        TeacherChapterRow(
            chapter_id=chapter.id,
            sequence=chapter.sequence,
            name=chapter.name,
            planned_date=chapter.planned_date,
            status=chapter.status or "Pending",
            completed_on=chapter.completed_on,
            completed_by=(
                names.get(chapter.completed_by_employee_id)
                if chapter.completed_by_employee_id is not None
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
    rooms = _labels(session)
    totals, done, _behind = _chapter_stats(session)
    course_cache: dict[UUID, ClassroomSubject | None] = {}
    result: list[TeacherAssignmentRow] = []

    for assignment in assignments:
        key = assignment.classroom_subject_id
        if key not in course_cache:
            course_cache[key] = _course_for(session, key)
        course = course_cache[key]
        if course is None:
            continue  # a history row whose section subject no longer exists
        total = totals.get(assignment.classroom_subject_id, 0)
        completed = done.get(assignment.classroom_subject_id, 0)
        current = assignment.effective_to is None
        result.append(
            TeacherAssignmentRow(
                classroom_subject_id=assignment.classroom_subject_id,
                section_id=course.classroom_id,
                label=rooms.get(course.classroom_id, "Class-section"),
                subject=course.name,
                current=current,
                effective_from=assignment.effective_from,
                effective_to=assignment.effective_to,
                done=completed,
                total=total,
                percent=round(100.0 * completed / total, 1) if total else None,
                weeks=_weeks(session, course) if current else [],
                chapters=_chapters(session, course) if current else [],
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
    year = completion.current_academic_year(session)
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
    pending = sum(_pending_by_course(session, set(course_ids)).values())

    totals, done, _behind = _chapter_stats(session)
    percents: list[float] = []
    for course in courses:
        total = totals.get(course.id, 0)
        if total:
            percents.append(100.0 * done.get(course.id, 0) / total)
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
    year = completion.current_academic_year(session)
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
