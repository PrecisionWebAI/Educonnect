"""`GET /teachers/performance` - the anonymous reviews, summarised.

Moved here in Phase 10: `teacherreview` is the *review* half of an appraisal, so the
read that summarises it belongs beside the season rather than in the directory's
service. Two things deliberately did not move:

* **the URL.** The screen has called `/teachers/performance` since Phase 1; a rename
  would break the client for no product reason, so the route spells the full path and
  is mounted with no prefix (`api.py`);
* **the right.** It stays `teachers.read`: reading ratings is reading the directory.
  `appraisals.review` is the right to *give* one, and it was never what this needed.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from app.core.db import get_session
from app.domains.academic.classroom.academics.models import SyllabusProgress
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission
from app.domains.people.teachers import labels as people_labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers.models import TeacherReview
from app.domains.people.teachers.schemas import (
    PerformanceComponent,
    StaffPerformance,
)
from app.domains.people.teachers.staff_attendance.models import StaffAttendanceRecord

router = APIRouter()


def trend(ratings: list[int]) -> str:
    """Which way the ratings moved: the recent half against the older half.

    A teacher with one rating has no movement to report, and "flat" is the honest
    answer for that - not a made-up direction.
    """
    if len(ratings) < 2:
        return "flat"
    midpoint = len(ratings) // 2
    older = sum(ratings[:midpoint]) / midpoint
    recent = sum(ratings[midpoint:]) / (len(ratings) - midpoint)
    if recent > older:
        return "up"
    if recent < older:
        return "down"
    return "flat"


#: How the overall score is put together. Named here, not scattered in the code,
#: so a school's "what counts as performance" question has one place to look.
#: The weights are renormalised over the components that actually have data.
WEIGHTS = {"attendance": 0.3, "reviews": 0.4, "syllabus": 0.3}

#: The window the register is read over: the last quarter.
ATTENDANCE_DAYS = 90


def _attendance(
    session: Session, employee_ids: list[UUID]
) -> dict[UUID, tuple[int, int]]:
    """{employee_id: (attended, marked)} over `ATTENDANCE_DAYS`, half days as half."""
    start = date.today() - timedelta(days=ATTENDANCE_DAYS)
    rows = session.exec(
        select(
            StaffAttendanceRecord.employee_id,
            StaffAttendanceRecord.status,
            func.count(),
        )
        .where(
            StaffAttendanceRecord.employee_id.in_(employee_ids),
            StaffAttendanceRecord.date >= start,
        )
        .group_by(StaffAttendanceRecord.employee_id, StaffAttendanceRecord.status)
    ).all()
    totals: dict[UUID, list[float]] = {}
    for employee_id, status, count in rows:
        bucket = totals.setdefault(employee_id, [0.0, 0.0])  # attended, marked
        bucket[1] += count
        if status == people_labels.PRESENT:
            bucket[0] += count
        elif status == people_labels.HALF_DAY:
            bucket[0] += count / 2
    return {key: (int(value[0]), int(value[1])) for key, value in totals.items()}


def _syllabus(session: Session, teacher_ids: list[UUID]) -> dict[UUID, int]:
    """{employee_id: chapters done as a percentage} - only where a plan exists."""
    if not teacher_ids:
        return {}
    rows = session.exec(
        select(
            SyllabusProgress.teacher_id,
            func.sum(SyllabusProgress.chapters_done),
            func.sum(SyllabusProgress.chapters_total),
        )
        .where(SyllabusProgress.teacher_id.in_(teacher_ids))
        .group_by(SyllabusProgress.teacher_id)
    ).all()
    covered: dict[UUID, int] = {}
    for teacher_id, done, total in rows:
        if teacher_id is not None and total:
            covered[teacher_id] = round(int(done or 0) / int(total) * 100)
    return covered


def performance(session: Session) -> list[StaffPerformance]:
    """Every person on the roll, scored from whatever the school actually recorded.

    The row is built for **both tabs** (0.9): a staff member has no syllabus, so that
    component is `None` and says "no data" instead of 0%. A teacher with no review,
    no marked register and no plan is a row of "no data" and a `score` of `None` -
    the honest answer before anything is known, and the reason `score` is optional
    rather than defaulting to zero.
    """
    teachers = teachers_repository.roll_employees(session, "teacher")
    staff = teachers_repository.roll_employees(session, "staff")
    everyone = {employee.id: employee for employee in [*teachers, *staff]}
    if not everyone:
        return []

    ids = list(everyone)
    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(User.id.in_([row.user_id for row in everyone.values()]))
        ).all()
    }

    reviews = session.exec(
        select(TeacherReview.teacher_id, TeacherReview.rating).order_by(
            TeacherReview.teacher_id,  # type: ignore[arg-type]
            TeacherReview.created_at,  # type: ignore[arg-type]
        )
    ).all()
    ratings: dict[UUID, list[int]] = {}
    for teacher_id, rating in reviews:
        ratings.setdefault(teacher_id, []).append(rating)

    attendance = _attendance(session, ids)
    syllabus = _syllabus(session, [employee.id for employee in teachers])
    teacher_ids = {employee.id for employee in teachers}

    rows: list[StaffPerformance] = []
    for employee in everyone.values():
        values = ratings.get(employee.id, [])
        rating = round(sum(values) / len(values), 1) if values else 0.0
        is_teacher = employee.id in teacher_ids
        components = _components(
            attendance=attendance.get(employee.id),
            ratings=values,
            rating=rating,
            syllabus=syllabus.get(employee.id) if is_teacher else None,
            is_teacher=is_teacher,
        )
        rows.append(
            StaffPerformance(
                id=employee.id,
                staff=names.get(employee.user_id, ""),
                kind="teacher" if is_teacher else "staff",
                rating=rating,
                reviews=len(values),
                trend=trend(values),
                score=_score(components),
                components=components,
            )
        )
    return sorted(rows, key=lambda row: row.staff)


def _components(
    *,
    attendance: tuple[int, int] | None,
    ratings: list[int],
    rating: float,
    syllabus: int | None,
    is_teacher: bool,
) -> list[PerformanceComponent]:
    """The four ingredients, each `None` when the school has nothing to judge by.

    `syllabus` is only ever built for a teacher: a staff member's job has no
    syllabus, so the component is **absent** rather than 0% - the same rule the
    periods tile follows on the workload screen.
    """
    items: list[PerformanceComponent] = []

    if attendance and attendance[1]:
        attended, marked = attendance
        percent = people_labels.attendance_percent(
            present=attended, half_day=0, marked=marked
        )
        items.append(
            PerformanceComponent(
                key="attendance",
                label="Attendance",
                value=float(percent),
                weight=WEIGHTS["attendance"],
                display=f"{percent}% of {marked} marked day(s)",
            )
        )
    else:
        items.append(
            PerformanceComponent(
                key="attendance",
                label="Attendance",
                weight=WEIGHTS["attendance"],
            )
        )

    if ratings:
        percent = round(rating / 5 * 100)
        items.append(
            PerformanceComponent(
                key="reviews",
                label="Reviews",
                value=float(percent),
                weight=WEIGHTS["reviews"],
                display=f"{rating}/5 from {len(ratings)} review(s)",
            )
        )
    else:
        items.append(
            PerformanceComponent(
                key="reviews", label="Reviews", weight=WEIGHTS["reviews"]
            )
        )

    if is_teacher:
        if syllabus is None:
            items.append(
                PerformanceComponent(
                    key="syllabus",
                    label="Syllabus",
                    weight=WEIGHTS["syllabus"],
                )
            )
        else:
            items.append(
                PerformanceComponent(
                    key="syllabus",
                    label="Syllabus",
                    value=float(syllabus),
                    weight=WEIGHTS["syllabus"],
                    display=f"{syllabus}% of the plan",
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


@router.get("/teachers/performance", response_model=list[StaffPerformance])
def read_staff_performance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.read")),
):
    """Ratings from the anonymous reviews - viewing is a read, not a workload right."""
    return performance(session)
