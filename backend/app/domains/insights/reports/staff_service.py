"""The three staff aggregates (Phase 9), computed from the tables that already exist.

Set-shaped on purpose: one query for the register's window, one for the timetable's
load, two for the season. A per-person loop would be a report that takes a minute on
a real school.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels as staff_labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers import scope as teachers_scope
from app.domains.people.teachers.appraisal.models import (
    Appraisal,
    AppraisalCycle,
    AppraisalGoal,
)
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord
from app.domains.people.teachers.workload.models import StaffWorkloadRule

from .staff_schemas import (
    StaffAppraisalSummary,
    StaffAttendanceSummary,
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


def _current_cycle(session: Session) -> AppraisalCycle | None:
    """The season being worked in: the open one, else the newest window."""
    cycles = session.exec(
        select(AppraisalCycle).order_by(
            AppraisalCycle.start_date.desc()  # type: ignore[attr-defined]
        )
    ).all()
    for cycle in cycles:
        if cycle.status == staff_labels.CYCLE_OPEN:
            return cycle
    return cycles[0] if cycles else None


def appraisal_summary(
    session: Session, employee_ids: list[UUID]
) -> StaffAppraisalSummary:
    """Where the current season has got to, and how its ratings average out."""
    cycle = _current_cycle(session)
    if cycle is None:
        return StaffAppraisalSummary()

    rows: list[Appraisal] = []
    if employee_ids:
        rows = list(
            session.exec(
                select(Appraisal).where(
                    Appraisal.cycle_id == cycle.id,
                    Appraisal.employee_id.in_(employee_ids),
                )
            ).all()
        )
    ratings = [row.reviewer_rating for row in rows if row.reviewer_rating is not None]

    judged: list[AppraisalGoal] = []
    if rows:
        goals = session.exec(
            select(AppraisalGoal).where(
                AppraisalGoal.appraisal_id.in_([row.id for row in rows])
            )
        ).all()
        judged = [goal for goal in goals if goal.achieved is not None]

    finished = (staff_labels.APPRAISAL_REVIEWED, staff_labels.APPRAISAL_FINALIZED)
    return StaffAppraisalSummary(
        cycle=cycle.name,
        cycle_status=cycle.status,
        total=len(rows),
        submitted=len(
            [
                row
                for row in rows
                if row.status
                in (
                    staff_labels.APPRAISAL_SUBMITTED,
                    *finished,
                )
            ]
        ),
        reviewed=len([row for row in rows if row.status in finished]),
        finalized=len(
            [row for row in rows if row.status == staff_labels.APPRAISAL_FINALIZED]
        ),
        average_reviewer_rating=(
            round(sum(ratings) / len(ratings), 1) if ratings else None
        ),
        goals_judged=len(judged),
        goals_achieved=len([goal for goal in judged if goal.achieved]),
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
        appraisals=appraisal_summary(session, employee_ids),
        scope=scope,
        people=len(employee_ids),
    )
