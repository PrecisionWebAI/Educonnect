"""`GET /teachers/performance` - attendance, workload and course completion.

The URL is the one the screen has called since Phase 1, so it stays: a rename would
break the client for no product reason. It is spelled out in full and mounted with no
prefix (`teachers/api.py`).

The score is **not** stored anywhere. It is derived from three tables on every read,
because a stored aggregate is a number that was true on the day somebody last ran a
job - and the first question a principal asks is "does this include last week?".

Nothing in this module reads a review or a rating: those were the appraisal season's
own vocabulary and they no longer exist in the database.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlmodel import Session, func, select

from app.domains.academic.classroom.academics.models import (
    CHAPTER_COMPLETED,
    Chapter,
    ChapterProgress,
    Classroom,
    SubjectTeacher,
)
from app.domains.academic.classroom.course import completion
from app.domains.admin.users.models import User
from app.domains.people.teachers import labels as staff_labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers.schemas import (
    PerformanceComponent,
    StaffPerformance,
)
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.workload import repository as workload_repository

#: How the overall score is put together. Named here, not scattered through the
#: code, so a school's "what counts as performance" question has one place to look.
#: Attendance weighs most because every school keeps that register for its own
#: reasons; the other two are shares of a plan the school itself wrote.
WEIGHTS = {"attendance": 0.4, "workload": 0.3, "course": 0.3}

#: Inside the course component: coverage against timeliness. Coverage carries more
#: because a chapter nobody reached cannot be "late" in any useful sense.
COURSE_COVERAGE = 0.6
COURSE_TIMELINESS = 0.4

#: The session months: 1 April -> 31 March.
SESSION_START_MONTH = 4
SESSION_END_MONTH = 3


@dataclass(frozen=True)
class _Session:
    """The window every percentage on this screen is measured over."""

    name: str
    start: date
    end: date
    #: The `academic_year` row, when the school has one - `None` means the window
    #: came from the calendar and no chapter row can be narrowed to it.
    year_id: UUID | None = None


def session_window(session: Session) -> _Session:
    """The session the numbers describe - the school's own, else the calendar's.

    The score used to be measured over "the last 90 days" while the screen called it
    this session. A school year is 1 April to 31 March; when the office has opened
    the row (`academic_year.is_current`) its dates are used **as written**, so a
    school that shifted its year is not quietly overruled by the calendar.
    """
    year = completion.current_year(session)
    if year is not None:
        return _Session(
            name=year.name, start=year.start_date, end=year.end_date, year_id=year.id
        )

    today = date.today()
    start_year = today.year if today.month >= SESSION_START_MONTH else today.year - 1
    return _Session(
        name=f"{start_year}-{str(start_year + 1)[-2:]}",
        start=date(start_year, SESSION_START_MONTH, 1),
        end=date(start_year + 1, SESSION_END_MONTH, 31),
    )


@dataclass
class _Register:
    """One person's days over the session: present, half, and marked at all."""

    present: int
    half_day: int
    marked: int

    @property
    def percent(self) -> int:
        return staff_labels.attendance_percent(
            present=self.present, half_day=self.half_day, marked=self.marked
        )


@dataclass
class _Course:
    """One teacher's chapter plan: reached, on time, and how far it slipped."""

    done: int
    total: int
    on_time: int
    #: Done chapters that had a planned date - the only ones timeliness can judge.
    planned: int
    #: Sum of `completed_on - planned_date` over those chapters; negative is early.
    slippage: int

    @property
    def coverage(self) -> int:
        return round(self.done / self.total * 100) if self.total else 0

    @property
    def timeliness(self) -> int | None:
        if not self.planned:
            return None
        return round(self.on_time / self.planned * 100)

    @property
    def average_days(self) -> int | None:
        if not self.planned:
            return None
        return round(self.slippage / self.planned)

    @property
    def value(self) -> int:
        """Coverage alone when no chapter was planned with a date."""
        if self.timeliness is None:
            return self.coverage
        return round(self.coverage * COURSE_COVERAGE + self.timeliness * COURSE_TIMELINESS)

    @property
    def display(self) -> str:
        parts = [f"{self.done} of {self.total} chapter(s) ({self.coverage}%)"]
        if self.timeliness is not None:
            parts.append(f"{self.timeliness}% on time")
        average = self.average_days
        if average is not None:
            if average > 0:
                parts.append(f"{average} day(s) late on average")
            elif average < 0:
                parts.append(f"{abs(average)} day(s) early on average")
            else:
                parts.append("on the planned date on average")
        return " · ".join(parts)


def _attendance(
    session: Session, employee_ids: list[UUID], start: date, end: date
) -> dict[UUID, _Register]:
    """{employee_id: their days} over the session, half days counted as half.

    The window stops at **today**: a session that runs to 31 March must not report a
    teacher as absent for the days nobody has lived yet.
    """
    if not employee_ids:
        return {}
    last = min(end, date.today())
    rows = session.exec(
        select(
            StaffAttendanceRecord.employee_id,
            StaffAttendanceRecord.status,
            func.count(),
        )
        .where(
            StaffAttendanceRecord.employee_id.in_(employee_ids),
            StaffAttendanceRecord.date >= start,
            StaffAttendanceRecord.date <= last,
        )
        .group_by(StaffAttendanceRecord.employee_id, StaffAttendanceRecord.status)
    ).all()

    tallies: dict[UUID, list[int]] = {}
    for employee_id, status, count in rows:
        bucket = tallies.setdefault(employee_id, [0, 0, 0])  # present, half, marked
        bucket[2] += int(count)
        if status == staff_labels.PRESENT:
            bucket[0] += int(count)
        elif status == staff_labels.HALF_DAY:
            bucket[1] += int(count)
    return {
        employee_id: _Register(present=v[0], half_day=v[1], marked=v[2])
        for employee_id, v in tallies.items()
    }


def _course(
    session: Session, teacher_ids: list[UUID], year_id: UUID | None
) -> dict[UUID, _Course]:
    """{employee_id: their chapter plan} across the subjects that person holds now.

    The plan is read **per class-section**, because `chapter` hangs off the class and
    `chapterprogress` off the section: 9-A and 9-B share one plan and can be at
    different chapters. A teacher who holds two sections of one subject is measured
    against both - that is the work they actually carry.

    Only chapters of the current session count, and only the holdings that are still
    open (`effective_to IS NULL`): a subject handed over last term is not this
    teacher's plan any more.
    """
    if not teacher_ids:
        return {}

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
    if not holdings:
        return {}

    rooms = dict(session.exec(select(Classroom.id, Classroom.class_id)).all())

    statement = select(
        Chapter.id, Chapter.class_id, Chapter.subject_id, Chapter.planned_date
    )
    if year_id is not None:
        statement = statement.where(Chapter.academic_year_id == year_id)

    plan: dict[tuple[UUID, UUID], list[tuple[UUID, date | None]]] = {}
    for chapter_id, class_id, subject_id, planned_date in session.exec(statement).all():
        plan.setdefault((class_id, subject_id), []).append((chapter_id, planned_date))

    progress = {
        (chapter_id, classroom_id): completed_on
        for chapter_id, classroom_id, completed_on in session.exec(
            select(
                ChapterProgress.chapter_id,
                ChapterProgress.classroom_id,
                ChapterProgress.completed_on,
            ).where(ChapterProgress.status == CHAPTER_COMPLETED)
        ).all()
    }

    tallies: dict[UUID, list[int]] = {}
    for teacher_id, classroom_id, subject_id in holdings:
        class_id = rooms.get(classroom_id)
        if class_id is None:
            continue
        chapters = plan.get((class_id, subject_id))
        if not chapters:
            continue
        # done, total, on_time, planned, slippage
        bucket = tallies.setdefault(teacher_id, [0, 0, 0, 0, 0])
        for chapter_id, planned_date in chapters:
            bucket[1] += 1
            completed_on = progress.get((chapter_id, classroom_id))
            if completed_on is None:
                continue
            bucket[0] += 1
            if planned_date is None:
                continue
            bucket[3] += 1
            if completed_on <= planned_date:
                bucket[2] += 1
            bucket[4] += (completed_on - planned_date).days

    return {
        teacher_id: _Course(
            done=v[0], total=v[1], on_time=v[2], planned=v[3], slippage=v[4]
        )
        for teacher_id, v in tallies.items()
    }


def _workload(
    session: Session, teacher_ids: list[UUID]
) -> tuple[dict[UUID, int], int, str]:
    """(periods a week per teacher, the school's capacity, where it came from)."""
    capacity, source, _week_slots = workload_repository.capacity(session)
    return teachers_repository.period_counts(session, teacher_ids), capacity, source


def _components(
    *,
    attendance: _Register | None,
    workload: tuple[int, int, str] | None,
    course: _Course | None,
) -> list[PerformanceComponent]:
    """The three ingredients, each `None` when the school has nothing to judge by.

    `workload` and `course` are only ever passed for a teacher: a staff member's job
    has no timetable periods and no chapter plan, so the component is **absent**
    rather than 0% - the same rule the periods tile follows on the workload screen.
    """
    items: list[PerformanceComponent] = []

    if attendance is not None and attendance.marked:
        items.append(
            PerformanceComponent(
                key="attendance",
                label="Attendance",
                value=float(attendance.percent),
                weight=WEIGHTS["attendance"],
                display=f"{attendance.percent}% of {attendance.marked} marked day(s)",
            )
        )
    else:
        items.append(
            PerformanceComponent(
                key="attendance", label="Attendance", weight=WEIGHTS["attendance"]
            )
        )

    if workload is not None:
        periods, capacity, source = workload
        if capacity:
            utilisation = staff_labels.utilisation(periods, capacity)
            measured = "the school's rule" if source == "rule" else "the timetable"
            items.append(
                PerformanceComponent(
                    key="workload",
                    label="Workload",
                    value=float(utilisation),
                    weight=WEIGHTS["workload"],
                    display=f"{periods} of {capacity} period(s) a week ({measured})",
                )
            )
        else:
            items.append(
                PerformanceComponent(
                    key="workload", label="Workload", weight=WEIGHTS["workload"]
                )
            )

        if course is None:
            # A teacher with no plan for the subjects they hold: "no data", not 0%.
            items.append(
                PerformanceComponent(
                    key="course", label="Course", weight=WEIGHTS["course"]
                )
            )
        else:
            items.append(
                PerformanceComponent(
                    key="course",
                    label="Course",
                    value=float(course.value),
                    weight=WEIGHTS["course"],
                    display=course.display,
                )
            )

    return items


def _score(components: list[PerformanceComponent]) -> int | None:
    """Weighted average over the components that have data, or `None` if none do."""
    available = [item for item in components if item.value is not None]
    total = sum(item.weight for item in available)
    if not total:
        return None
    return round(sum((item.value or 0) * item.weight for item in available) / total)


def performance(session: Session) -> list[StaffPerformance]:
    """Every person on the roll, scored from whatever the school actually recorded.

    The row is built for **both tabs** (0.9): a staff member has no timetable and no
    plan, so those two components are absent and the score is their attendance
    alone. Somebody with an unmarked register is a row of "no data" and a `score` of
    `None` - the honest answer before anything is known, and the reason `score` is
    optional rather than defaulting to zero.
    """
    teachers = teachers_repository.roll_employees(session, "teacher")
    staff = teachers_repository.roll_employees(session, "staff")
    everyone = {employee.id: employee for employee in [*teachers, *staff]}
    if not everyone:
        return []

    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(User.id.in_([row.user_id for row in everyone.values()]))
        ).all()
    }

    window = session_window(session)
    attendance = _attendance(session, list(everyone), window.start, window.end)
    teacher_ids = [employee.id for employee in teachers]
    periods, capacity, capacity_source = _workload(session, teacher_ids)
    course = _course(session, teacher_ids, window.year_id)
    teaching = set(teacher_ids)

    rows: list[StaffPerformance] = []
    for employee in everyone.values():
        is_teacher = employee.id in teaching
        components = _components(
            attendance=attendance.get(employee.id),
            workload=(
                (periods.get(employee.id, 0), capacity, capacity_source)
                if is_teacher
                else None
            ),
            course=course.get(employee.id) if is_teacher else None,
        )
        rows.append(
            StaffPerformance(
                id=employee.id,
                staff=names.get(employee.user_id, ""),
                kind="teacher" if is_teacher else "staff",
                session=window.name,
                session_start=window.start,
                session_end=window.end,
                score=_score(components),
                components=components,
            )
        )
    return sorted(rows, key=lambda row: row.staff)


