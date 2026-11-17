"""The three staff aggregates (Phase 9), computed from the tables that already exist.

Set-shaped on purpose: one query for the register's window, one for the timetable's
load, and the performance tile reuses the one per-person calculation the Performance
tab draws its rows from. A second copy of "what a score is" is how a tile and the
table under it start disagreeing.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as staff_labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers import scope as teachers_scope
from app.domains.people.teachers.performance import service as performance_service
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.workload.models import StaffWorkloadRule

from .staff_schemas import (
    StaffAttendanceSummary,
    StaffPerformanceSummary,
    StaffSummaryReport,
    StaffWorkloadSummary,
)

#: How far back the attendance aggregate looks by default: a month is what a
#: principal means by "this month", and the window travels in the payload.
DEFAULT_DAYS = 30


def _visible(session: Session, user: User | None) -> list[Employee] | None:
    """The people this caller may count, or ``None`` for the whole roll."""
    ids = teachers_scope.visible_employee_ids(session, user)
    if ids is None:
        return None
    return [
        employee
        for employee in teachers_repository.teaching_employees(session)
        if employee.id in ids
    ]


def attendance_summary(
    session: Session, employee_ids: list[UUID], days: int
) -> StaffAttendanceSummary:
    """Present / half-day / absent over a window, as a share of the days marked."""
    window_end = date.today()
    window_start = window_end - timedelta(days=max(days, 1) - 1)

    counts = dict.fromkeys(staff_labels.ATTENDANCE_STATUSES, 0)
    if employee_ids:
        rows = session.exec(
            select(StaffAttendanceRecord).where(
                StaffAttendanceRecord.employee_id.in_(employee_ids),
                StaffAttendanceRecord.date >= window_start,
                StaffAttendanceRecord.date <= window_end,
            )
        ).all()
        for row in rows:
            if row.status in counts:
                counts[row.status] += 1
    marked = sum(counts.values())

    return StaffAttendanceSummary(
        window_start=window_start,
        window_end=window_end,
        days=days,
        present=counts[staff_labels.PRESENT],
        half_day=counts[staff_labels.HALF_DAY],
        absent=counts[staff_labels.ABSENT],
        marked=marked,
        percent=staff_labels.attendance_percent(
            present=counts[staff_labels.PRESENT],
            half_day=counts[staff_labels.HALF_DAY],
            marked=marked,
        ),
    )


def workload_summary(
    session: Session, employee_ids: list[UUID]
) -> StaffWorkloadSummary:
    """Periods per teacher, bucketed against the school's rule (or its heaviest load)."""
    loads = teachers_repository.period_counts(session, employee_ids)
    per_teacher = [loads.get(employee_id, 0) for employee_id in employee_ids]
    rule = session.exec(select(StaffWorkloadRule)).first()

    if rule is not None and rule.weekly_periods:
        capacity = rule.weekly_periods
        source = "rule"
        under_mark = capacity * rule.underload_percent / 100
        over_mark = capacity * rule.overload_percent / 100
    else:
        # No rule written: the heaviest timetable in the school is the only
        # denominator the data supports, and the payload says so.
        capacity = max(per_teacher, default=0)
        source = "timetable"
        under_mark = capacity * 0.6
        over_mark = float(capacity)

    under = normal = over = 0
    for load in per_teacher:
        if capacity and load > over_mark:
            over += 1
        elif capacity and load < under_mark:
            under += 1
        else:
            normal += 1

    total = sum(per_teacher)
    return StaffWorkloadSummary(
        teachers=len(per_teacher),
        periods=total,
        average=round(total / len(per_teacher), 1) if per_teacher else 0.0,
        maximum=max(per_teacher, default=0),
        under=under,
        normal=normal,
        over=over,
        capacity_source=source,
        capacity=capacity,
    )


def performance_summary(
    session: Session, employee_ids: list[UUID]
) -> StaffPerformanceSummary:
    """The roll's scores, averaged - from the one per-person calculation.

    Reused rather than re-derived: the Performance tab ranks people by these exact
    numbers, so a tile that computed its own average would eventually disagree with
    the rows under it. `employee_ids` is already the caller's scope (`_visible`).
    """
    window = performance_service.session_window(session)
    wanted = set(employee_ids)
    rows = [row for row in performance_service.performance(session) if row.id in wanted]

    scores = [row.score for row in rows if row.score is not None]
    components: dict[str, list[float]] = {}
    for row in rows:
        for item in row.components:
            if item.value is not None:
                components.setdefault(item.key, []).append(item.value)

    def average_of(key: str) -> int | None:
        values = components.get(key)
        if not values:
            return None
        return round(sum(values) / len(values))

    return StaffPerformanceSummary(
        session=window.name,
        session_start=window.start,
        session_end=window.end,
        people=len(rows),
        scored=len(scores),
        average=round(sum(scores) / len(scores), 1) if scores else None,
        maximum=max(scores) if scores else None,
        minimum=min(scores) if scores else None,
        attendance=average_of("attendance"),
        workload=average_of("workload"),
        course=average_of("course"),
    )


def staff_summary(
    session: Session, user: User | None = None, days: int = DEFAULT_DAYS
) -> StaffSummaryReport:
    """All three, at the caller's scope - the payload says which scope that was."""
    people = _visible(session, user)
    if people is None:
        employee_ids = [
            employee.id for employee in teachers_repository.teaching_employees(session)
        ]
        scope = "school"
    else:
        employee_ids = [employee.id for employee in people]
        scope = "scoped"

    return StaffSummaryReport(
        attendance=attendance_summary(session, employee_ids, days),
        workload=workload_summary(session, employee_ids),
        performance=performance_summary(session, employee_ids),
        scope=scope,
        people=len(employee_ids),
    )
